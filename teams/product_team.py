"""
Product Development Team

Members:
- Product Lead (coordinator) - asks questions, creates docs, has all tools
- Lead Engineer - architecture and code review
- Software Engineer - implementation
- Security Engineer - security review
"""

from agno.team import Team
from db import db
from agno.models.openrouter import OpenRouter

from agents.product_lead import product_lead_agent
from agents.lead_engineer import lead_engineer_agent
from agents.software_engineer import software_engineer_agent
from agents.security_engineer import security_engineer_agent
from agents.credentials_manager import credentials_manager_agent
from workflows.product_requirements_workflow import product_requirements_workflow
from workflows.software_development_workflow import software_development_workflow
from tools.project_tools import list_user_projects, get_project, search_projects_by_name, find_project_by_github_url


def run_product_requirements(input_data: str, **kwargs) -> str:
    """Run the product requirements workflow.

    Creates PRD/Feature Spec AND Architecture documents.
    Input should include: PROJECT_TYPE (new/existing), PROJECT_NAME, DESCRIPTION, FEATURE_NAME (optional)
    Returns 2 Google Docs URLs (PRD/FS + Architecture).

    Args:
        input_data: Workflow input parameters
        **kwargs: Additional context from Agno (includes user_id, agent, run_context, etc.)
    """
    # Extract user_id from Agno's injected context or fall back to global context
    user_id = kwargs.get("user_id", "")
    if not user_id:
        from services.user_context import get_current_user_id
        user_id = get_current_user_id() or ""
        if user_id:
            print(f"[workflow] Using user_id from global context: {user_id}")

    print(f"[workflow] run_product_requirements called with user_id={user_id!r}")
    print(f"[workflow] input_data:\n{input_data}")
    return product_requirements_workflow.run(input=input_data, user_id=user_id).content


def run_software_development(input_data: str, **kwargs) -> str:
    """Run the software development workflow.

    Takes Architecture URL as input. For existing projects, include the GitHub repo URL.
    The workflow will detect existing repos and update them instead of creating new ones.

    Input should include:
    - ARCHITECTURE_URL (required) - Google Docs URL
    - GITHUB_REPO_URL (optional) - Full GitHub URL for existing projects (e.g. https://github.com/user/repo)
    - GITHUB_REPO (optional) - repo name
    - PROJECT_NAME (optional) - project name

    Note: GitHub owner is auto-resolved from the user's GitHub token. No need to pass it.

    Returns deployment link + GitHub repo URL.

    Args:
        input_data: Workflow input parameters
        **kwargs: Additional context from Agno (includes user_id, agent, run_context, etc.)
    """
    # Extract user_id from Agno's injected context or fall back to global context
    user_id = kwargs.get("user_id", "")
    if not user_id:
        from services.user_context import get_current_user_id
        user_id = get_current_user_id() or ""
        if user_id:
            print(f"[workflow] Using user_id from global context: {user_id}")

    print(f"[workflow] run_software_development called with user_id={user_id!r}")
    return software_development_workflow.run(input=input_data, user_id=user_id).content


product_team = Team(
    name="Product Development Team",
    model=OpenRouter(id="google/gemini-3-flash-preview", max_tokens=16384),
    db=db,
    members=[
        credentials_manager_agent,
        product_lead_agent,
        lead_engineer_agent,
        software_engineer_agent,
        security_engineer_agent,
    ],
    tools=[run_product_requirements, run_software_development, list_user_projects, get_project, search_projects_by_name, find_project_by_github_url],
    instructions=[
        """You are the Product Development Team.

## TEAM TOOLS

### 1. `run_product_requirements(input_data: str)`
Creates PRD/Feature Spec AND Architecture/Technical documents.

**New project input:**
```
run_product_requirements(input_data="PROJECT_TYPE: new\\nPROJECT_NAME: AppName\\nDESCRIPTION: Full description")
```
Returns: PRD URL + Architecture URL

**Existing project input:**
```
run_product_requirements(input_data="PROJECT_TYPE: existing\\nPROJECT_ID: <uuid>\\nPROJECT_NAME: AppName\\nFEATURE_NAME: FeatureName\\nDESCRIPTION: Feature description")
```
Returns: Feature Spec URL + Technical Doc URL

Always share BOTH returned URLs with the user.

### 2. `run_software_development(input_data: str)`
Implements code, creates/updates GitHub repo, deploys to Vercel.

**New project:**
```
run_software_development(input_data="ARCHITECTURE_URL: <docs_url>")
```

**Existing project (MUST include GitHub URL):**
```
run_software_development(input_data="ARCHITECTURE_URL: <docs_url>\\nGITHUB_REPO_URL: <github_url>")
```

ONLY call when user explicitly requests implementation. NEVER auto-run.

### 3. Project Lookup Tools
- `list_user_projects(limit=50)` — List all projects
- `get_project(project_id)` — Get project by UUID
- `search_projects_by_name(search_query)` — Search by name
- `find_project_by_github_url(github_url)` — Find by GitHub URL

When user mentions a project by name, search first, confirm with user, then use that project_id.

---

## TEAM ROLES

**Credentials Manager** — Validates GitHub, Vercel, Supabase, Google tokens. Runs AFTER discovery, BEFORE document creation. No workflow runs without validated credentials.

**Product Lead** — OWNS the discovery conversation. Asks ONE question at a time, understands the problem and vision first before asking about assets or links. Reports back ONLY when discovery is complete and user has confirmed the summary. Does NOT create documents or run workflows.

**Lead Engineer** — Technical guidance and code review.

**Software Engineer** — Code implementation.

**Security Engineer** — Security review.

---

## WORKFLOW (EXACT ORDER)

### Step 1: Discovery
Delegate to Product Lead: "Conduct a natural discovery conversation with the user. Understand the problem, who it is for, why the product is valuable, how it will sustain itself, and what success looks like. Ask one question at a time. Only ask about assets, links, and branding after the strategic picture is clear. When you have a complete picture and the user has confirmed your summary, report back."

- Product Lead asks ONE question per message, multiple rounds
- DO NOT interrupt Product Lead or call tools until they report back
- If user says "assume" / "I don't know", pass to Product Lead — they handle it

### Step 2: Credential Validation
After Product Lead confirms requirements are complete and user approved the summary:
- Delegate to Credentials Manager to validate all tokens
- Wait for confirmation before proceeding

### Step 3: Document Creation
Call `run_product_requirements` with gathered info. Share BOTH URLs with user.
Ask: "Would you like me to proceed with implementation?"

### Step 4: Implementation (ONLY if user says yes)
Call `run_software_development`. For existing projects, MUST include GITHUB_REPO_URL.
Share deployment link and GitHub repo with user.

---

## EXISTING PROJECT HANDLING

If user mentions a GitHub URL, project name, "update", "modify", or "add feature to":
1. Search by name or GitHub URL using project tools
2. If found → confirm with user, use that project_id
3. If NOT found → list all projects, let user pick or import new

**Project Import Flow** (GitHub repo not in DB):
1. Show existing projects, ask if it's one of those
2. Gather project context (description, state, tech stack, deployment URL)
3. Create PRD via `run_product_requirements` with PROJECT_TYPE: new
4. Confirm import, then create Feature Spec for requested changes

---

## CRITICAL RULES

1. **PRODUCT LEAD FIRST** — Always delegate discovery to Product Lead first. Let them finish ALL rounds.
2. **CREDENTIALS AFTER DISCOVERY** — Validate credentials AFTER user confirms requirements, BEFORE documents.
3. **TEAM CALLS TOOLS** — The Team calls `run_product_requirements` and `run_software_development` directly. Never delegate tool calls to members.
4. **ASK BEFORE IMPLEMENTING** — Never auto-run `run_software_development`. User must explicitly request it.
5. **AUTO-RUN ON DOCUMENT** — If user provides a Google Docs URL with "implement this", call `run_software_development` directly.
6. **PRESERVE ALL LINKS** — Every URL the user provides MUST appear verbatim in all documents. Zero tolerance for missing links. This includes images, fonts, icons, social media, WhatsApp, maps, videos, CDNs, docs, references — ANY link.
""",
    ],
    markdown=True,
    show_members_responses=True,
    add_history_to_context=True,
    num_history_messages=20,
    debug_mode=False,
)
