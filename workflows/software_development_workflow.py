"""
Software Development Workflow - Implementation with Review Cycle

This workflow handles implementation with code review and security review iterations.
The PRD and Architecture should already exist (created by Product Requirements Workflow).

Flow:
1. Read PRD+Architecture URLs -> Extract PRD and Architecture content from Google Docs
2. Create GitHub Repo -> Initialize repository
3. Implementation Cycle (Loop max 3 iterations):
   - Development: Software Engineer writes/revises code
   - Code Review: Lead Engineer reviews code
   - Security Review: Security Engineer reviews for vulnerabilities
   - Loop continues until both reviews approve OR max iterations reached
4. Deploy to Vercel -> Deploy and get preview link
5. Summary -> Return deployment link

Input: document_url (PRD URL) and architecture_url (Architecture Doc URL)
Output: Vercel deployment link + GitHub repo
"""

import os
import sys
import re
import asyncio
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agno.workflow import Step, Workflow, Loop
from agno.workflow.types import StepInput, StepOutput
from agno.utils.log import log_info, log_error


# ============================================================================
# SESSION STATE FOR TRACKING FILES AND REVIEWS
# ============================================================================

class ImplementationState:
    """Tracks file paths, review statuses, and project context across workflow."""
    def __init__(self):
        self.iteration = 0
        self.code_file_path = ""
        self.code_review_file_path = ""
        self.security_review_file_path = ""
        self.code_review_status = "pending"
        self.security_review_status = "pending"
        self.approved = False
        self.github_repo = ""
        self.github_owner = ""
        self.project_name = ""
        self.prd_content = ""
        self.architecture_content = ""

    def reset_reviews(self):
        """Reset review statuses for a new iteration."""
        self.code_review_status = "pending"
        self.security_review_status = "pending"


# Global state instance
_state = ImplementationState()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _run_async(coro):
    """Run async coroutine from sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def parse_input_urls(input_str: str) -> dict:
    """
    Parse input string to extract PRD URL and Architecture URL.

    Expected format:
    - PRD_URL: <url>
    - ARCHITECTURE_URL: <url>
    OR
    - DOCUMENT_URL: <prd_url> (for backward compatibility)
    - ARCHITECTURE_URL: <arch_url>
    """
    print(f"\n[DEBUG:parse_input] Parsing input (length {len(input_str)})")

    result = {
        "prd_url": None,
        "architecture_url": None,
        "github_repo": None,
        "github_owner": None,
        "project_name": None,
    }

    # Extract PRD URL
    prd_match = re.search(r'(?:PRD_URL|DOCUMENT_URL):\s*(https://[^\s]+)', input_str, re.I)
    if prd_match:
        result["prd_url"] = prd_match.group(1)
        print(f"[DEBUG:parse_input] ✓ Found PRD URL: {result['prd_url']}")

    # Extract Architecture URL
    arch_match = re.search(r'ARCHITECTURE_URL:\s*(https://[^\s]+)', input_str, re.I)
    if arch_match:
        result["architecture_url"] = arch_match.group(1)
        print(f"[DEBUG:parse_input] ✓ Found Architecture URL: {result['architecture_url']}")

    # Extract GitHub info (optional)
    repo_match = re.search(r'GITHUB_REPO:\s*([^\s]+)', input_str, re.I)
    if repo_match:
        result["github_repo"] = repo_match.group(1)

    owner_match = re.search(r'GITHUB_OWNER:\s*([^\s]+)', input_str, re.I)
    if owner_match:
        result["github_owner"] = owner_match.group(1)

    # Extract project name (optional)
    name_match = re.search(r'PROJECT_NAME:\s*([^\n]+)', input_str, re.I)
    if name_match:
        result["project_name"] = name_match.group(1).strip()

    return result


def _get_github_file_paths(product_name: str):
    """Generate consistent GitHub file paths for code and reviews."""
    safe_name = product_name.lower().replace(" ", "_").replace("/", "_")[:30]
    return {
        "code": f".dev-team/implementations/{safe_name}.py",
        "code_review": f".dev-team/code_reviews/{safe_name}_review.md",
        "security_review": f".dev-team/security_reviews/{safe_name}_security.md",
    }


# ============================================================================
# WORKFLOW STEP FUNCTIONS
# ============================================================================

def read_documents(step_input: StepInput) -> StepOutput:
    """
    Step 1: Read PRD and Architecture from Google Docs URLs

    Input: String with PRD_URL and ARCHITECTURE_URL
    Output: Combined PRD + Architecture content
    """
    global _state

    input_str = step_input.input if isinstance(step_input.input, str) else ""

    print("\n" + "="*80)
    print("[DEBUG:read_documents] === STEP 1: READ DOCUMENTS ===")
    print("="*80 + "\n")

    parsed = parse_input_urls(input_str)

    if not parsed["prd_url"]:
        error_msg = "ERROR: No PRD_URL provided"
        log_error(f"[STEP:read_documents] {error_msg}")
        return StepOutput(content=error_msg, success=False)

    if not parsed["architecture_url"]:
        error_msg = "ERROR: No ARCHITECTURE_URL provided"
        log_error(f"[STEP:read_documents] {error_msg}")
        return StepOutput(content=error_msg, success=False)

    log_info(f"[STEP:read_documents] Reading PRD from: {parsed['prd_url']}")
    log_info(f"[STEP:read_documents] Reading Architecture from: {parsed['architecture_url']}")

    from tools.google_docs_tools import GoogleDocsTools
    google_docs = GoogleDocsTools()

    try:
        # Read PRD
        prd_doc_id = re.search(r'/document/d/([a-zA-Z0-9-_]+)', parsed["prd_url"]).group(1)
        _state.prd_content = google_docs.read_document(prd_doc_id)
        print(f"[DEBUG:read_documents] ✓ PRD read: {len(_state.prd_content)} chars")

        # Read Architecture
        arch_doc_id = re.search(r'/document/d/([a-zA-Z0-9-_]+)', parsed["architecture_url"]).group(1)
        _state.architecture_content = google_docs.read_document(arch_doc_id)
        print(f"[DEBUG:read_documents] ✓ Architecture read: {len(_state.architecture_content)} chars")

        # Store project info
        _state.github_repo = parsed["github_repo"]
        _state.github_owner = parsed["github_owner"]
        _state.project_name = parsed["project_name"] or "project"

        combined_content = f"""=== PRD ===
{_state.prd_content}

=== ARCHITECTURE ===
{_state.architecture_content}

=== PROJECT INFO ===
GitHub Repo: {_state.github_repo}
GitHub Owner: {_state.github_owner}
Project Name: {_state.project_name}
"""

        log_info("[STEP:read_documents] Documents read successfully")
        return StepOutput(content=combined_content, success=True)

    except Exception as e:
        error_msg = f"ERROR: Failed to read documents: {str(e)}"
        log_error(f"[STEP:read_documents] {error_msg}")
        return StepOutput(content=error_msg, success=False)


def create_github_repo(step_input: StepInput) -> StepOutput:
    """
    Step 2: Create GitHub Repository

    Input: Combined PRD + Architecture content
    Output: GitHub repository info
    """
    global _state

    log_info("[STEP:create_repo] Creating GitHub repository")

    from agents.software_engineer import software_engineer_agent

    prompt = f"""Create a new GitHub repository for this project.

**Project Name:** {_state.project_name}
**GitHub Owner:** {_state.github_owner or "your-username"}
**Repository Name:** {_state.github_repo or _state.project_name.lower().replace(" ", "-")}

**Architecture Overview:**
{_state.architecture_content[:1000]}

## Instructions

1. **Check if repository exists** using get_repository
   - owner: "{_state.github_owner}"
   - repo: "{_state.github_repo}"

2. **If repo doesn't exist**, create it using create_repository
   - name: "{_state.github_repo}"
   - description: "{_state.project_name}"
   - private: false

3. **Create initial project structure**:
   - README.md with project description
   - .gitignore based on tech stack
   - .env.example with required environment variables
   - Basic folder structure

4. **Save files to GitHub** using create_or_update_file

Return confirmation with repository URL.
"""

    log_info("[AGENT:software_engineer] Creating repository")
    result = _run_async(software_engineer_agent.arun(prompt))
    output = result.content or ""

    # Extract repo URL
    repo_url_match = re.search(r'https://github\.com/[^\s]+', output)
    if repo_url_match:
        repo_url = repo_url_match.group(0)
        log_info(f"[STEP:create_repo] Repository created: {repo_url}")

    return StepOutput(content=output, success=True)


# ============================================================================
# IMPLEMENTATION CYCLE STEPS (Loop)
# ============================================================================

def development(step_input: StepInput) -> StepOutput:
    """Software Engineer implements code and saves to GitHub."""
    global _state

    _state.iteration += 1
    iteration = _state.iteration

    # Generate GitHub file paths
    paths = _get_github_file_paths(_state.project_name)
    _state.code_file_path = paths["code"]
    _state.code_review_file_path = paths["code_review"]
    _state.security_review_file_path = paths["security_review"]

    log_info(f"[DEVELOPMENT] Iteration {iteration}")

    from agents.software_engineer import software_engineer_agent

    if iteration == 1:
        # First iteration - implement from scratch
        prompt = f"""You are the Software Engineer. Implement the code based on the architecture.

**Project:** {_state.project_name}
**GitHub:** {_state.github_owner}/{_state.github_repo}

**PRD (Requirements):**
{_state.prd_content[:2000]}

**Architecture (Technical Design):**
{_state.architecture_content}

**Your Task:**
1. Write clean, production-ready code following the architecture
2. Include proper error handling and validation
3. Add docstrings and comments
4. Follow security best practices

**Save Code to GitHub:**
Call create_or_update_file ONCE:
- owner: "{_state.github_owner}"
- repo: "{_state.github_repo}"
- path: "{_state.code_file_path}"
- content: [your Python code]
- message: "feat: implement {_state.project_name}"
- branch: "main"

After saving, respond with a summary of what you implemented.
"""
    else:
        # Revision iteration - read feedback and update
        prompt = f"""You are the Software Engineer. Revise your code based on review feedback.

**Project:** {_state.project_name}
**GitHub:** {_state.github_owner}/{_state.github_repo}

**Steps:**
1. Read your current code: get_file_contents(owner="{_state.github_owner}", repo="{_state.github_repo}", path="{_state.code_file_path}")
2. Read code review: get_file_contents(owner="{_state.github_owner}", repo="{_state.github_repo}", path="{_state.code_review_file_path}")
3. Read security review: get_file_contents(owner="{_state.github_owner}", repo="{_state.github_repo}", path="{_state.security_review_file_path}")
4. Revise your code to address ALL feedback
5. Save revised code: create_or_update_file(owner="{_state.github_owner}", repo="{_state.github_repo}", path="{_state.code_file_path}", content=[revised code], message="fix: address review feedback", branch="main")

Call each tool EXACTLY ONCE. After saving, respond with changes made.
"""

    result = _run_async(software_engineer_agent.arun(prompt))
    _state.reset_reviews()

    log_info(f"[DEVELOPMENT] Code saved to: {_state.github_owner}/{_state.github_repo}/{_state.code_file_path}")
    return StepOutput(content=f"CODE:{_state.code_file_path}\n{result.content}", success=True)


def code_review(step_input: StepInput) -> StepOutput:
    """Lead Engineer reviews code and saves feedback to GitHub."""
    global _state

    log_info(f"[CODE_REVIEW] Iteration {_state.iteration}")

    from agents.lead_engineer import lead_engineer_agent

    prompt = f"""You are the Lead Engineer. Review the code implementation.

**Project:** {_state.project_name}
**GitHub:** {_state.github_owner}/{_state.github_repo}

**Steps:**
1. Read the code: get_file_contents(owner="{_state.github_owner}", repo="{_state.github_repo}", path="{_state.code_file_path}")

2. Review against these criteria:
   - Code Quality: Clean, readable, well-structured?
   - Architecture Alignment: Follows the technical spec?
   - Best Practices: Coding standards followed?
   - Error Handling: Comprehensive?
   - Maintainability: Easy to maintain?

3. Write review with this format:
   - **Review Status**: APPROVED or CHANGES_REQUESTED
   - **Quality Score**: 1-10
   - **Strengths**: What's done well
   - **Issues Found**: Problems (if any)
   - **Required Changes**: Specific changes needed (if CHANGES_REQUESTED)

4. Save review: create_or_update_file(owner="{_state.github_owner}", repo="{_state.github_repo}", path="{_state.code_review_file_path}", content=[your review], message="docs: code review iteration {_state.iteration}", branch="main")

Call each tool EXACTLY ONCE. After saving, confirm: "Review Status: [APPROVED/CHANGES_REQUESTED]"
"""

    result = _run_async(lead_engineer_agent.arun(prompt))
    content_lower = result.content.lower()

    _state.code_review_status = "approved" if "approved" in content_lower and "changes_requested" not in content_lower else "changes_requested"

    log_info(f"[CODE_REVIEW] Status: {_state.code_review_status}")
    return StepOutput(content=f"REVIEW:{_state.code_review_status}\n{result.content}", success=True)


def security_review(step_input: StepInput) -> StepOutput:
    """Security Engineer reviews code for vulnerabilities and saves feedback to GitHub."""
    global _state

    log_info(f"[SECURITY_REVIEW] Iteration {_state.iteration}")

    from agents.security_engineer import security_engineer_agent

    prompt = f"""You are the Security Engineer. Review the code for security vulnerabilities.

**Project:** {_state.project_name}
**GitHub:** {_state.github_owner}/{_state.github_repo}

**Steps:**
1. Read the code: get_file_contents(owner="{_state.github_owner}", repo="{_state.github_repo}", path="{_state.code_file_path}")

2. Check for security issues:
   - Injection vulnerabilities (SQL, XSS, command injection)
   - Authentication/Authorization flaws
   - Sensitive data exposure
   - Input validation issues
   - Insecure error handling
   - OWASP Top 10 vulnerabilities

3. Write review with this format:
   - **Security Status**: APPROVED or CHANGES_REQUIRED
   - **Vulnerabilities Found**: List with severity (Critical/High/Medium/Low)
   - **Required Fixes**: Specific security fixes
   - **Recommendations**: Additional improvements

4. Save review: create_or_update_file(owner="{_state.github_owner}", repo="{_state.github_repo}", path="{_state.security_review_file_path}", content=[your review], message="docs: security review iteration {_state.iteration}", branch="main")

Call each tool EXACTLY ONCE. After saving, confirm: "Security Status: [APPROVED/CHANGES_REQUIRED]"
"""

    result = _run_async(security_engineer_agent.arun(prompt))
    content_lower = result.content.lower()

    # Determine security status
    if "changes_required" in content_lower or "critical" in content_lower:
        _state.security_review_status = "changes_required"
    else:
        _state.security_review_status = "approved"

    log_info(f"[SECURITY_REVIEW] Status: {_state.security_review_status}")
    return StepOutput(content=f"SECURITY:{_state.security_review_status}\n{result.content}", success=True)


def reviews_passed(outputs: List[StepOutput]) -> bool:
    """Check if both reviews passed. Returns True to break loop."""
    global _state

    code_approved = _state.code_review_status == "approved"
    security_approved = _state.security_review_status == "approved"

    if code_approved and security_approved:
        _state.approved = True
        log_info("[LOOP] All reviews APPROVED - breaking loop")
        return True

    if _state.iteration >= 3:
        log_info("[LOOP] Max iterations (3) reached - breaking loop")
        return True

    log_info(f"[LOOP] Continuing - Code: {_state.code_review_status}, Security: {_state.security_review_status}")
    return False


# ============================================================================
# DEPLOYMENT AND SUMMARY
# ============================================================================

def deploy_to_vercel(step_input: StepInput) -> StepOutput:
    """Step 4: Deploy to Vercel"""
    global _state

    log_info("[STEP:deploy] Deploying to Vercel")

    from agents.software_engineer import software_engineer_agent

    prompt = f"""Deploy the project to Vercel.

**Project:** {_state.project_name}
**GitHub Repository:** {_state.github_owner}/{_state.github_repo}

**Instructions:**
1. Use Vercel MCP tools to deploy
2. Connect the GitHub repository
3. Configure environment variables from .env.example
4. Verify deployment
5. Return the preview URL

Use Vercel MCP tools.
"""

    log_info("[AGENT:software_engineer] Deploying")
    result = _run_async(software_engineer_agent.arun(prompt))

    log_info("[STEP:deploy] Deployment complete")
    return StepOutput(content=result.content, success=True)


def create_summary(step_input: StepInput) -> StepOutput:
    """Step 5: Create Final Summary"""
    global _state

    deployment_info = step_input.previous_step_content or ""

    log_info("[STEP:summary] Creating summary")

    # Extract URLs
    deploy_url_match = re.search(r'https://[^\s]+vercel\.app[^\s]*', deployment_info)
    deploy_url = deploy_url_match.group(0) if deploy_url_match else "Deployment in progress"

    repo_url = f"https://github.com/{_state.github_owner}/{_state.github_repo}" if _state.github_owner and _state.github_repo else "Repository created"

    status = "APPROVED" if _state.approved else "COMPLETED_WITH_NOTES"

    summary = f"""
## 🎉 Implementation Complete!

### Project: {_state.project_name}

**Status:** `{status}`
**Review Iterations:** {_state.iteration}
**Code Review:** {_state.code_review_status}
**Security Review:** {_state.security_review_status}

---

### 🚀 Deployment

**Live Preview:** {deploy_url}
**GitHub Repository:** {repo_url}

---

### 📁 Implementation Files (in GitHub)

**Code:** `{_state.code_file_path}`
**Code Review:** `{_state.code_review_file_path}`
**Security Review:** `{_state.security_review_file_path}`

---

### ✅ What Was Done

1. ✓ Read PRD and Architecture from Google Docs
2. ✓ Created GitHub repository with initial structure
3. ✓ Implementation cycle ({_state.iteration} iterations):
   - Development by Software Engineer
   - Code review by Lead Engineer
   - Security review by Security Engineer
4. ✓ Deployed to Vercel

---

### 🔗 Next Steps

1. Visit the preview link to test your product
2. Review the code and feedback in GitHub
3. Configure custom domain (optional)
4. Set up production environment variables
"""

    log_info("[STEP:summary] Summary complete")

    # Reset state for next run
    _state.__init__()

    return StepOutput(content=summary, success=True)


# ============================================================================
# WORKFLOW DEFINITION
# ============================================================================

software_development_workflow = Workflow(
    name="Software Development",
    stream=False,
    description="""Implementation workflow with code review and security review cycle.

    Input: PRD_URL and ARCHITECTURE_URL (from Product Requirements Workflow)

    Sequential Steps:
    1. Read PRD + Architecture from Google Docs
    2. Create GitHub Repository
    3. Implementation Cycle (Loop max 3 iterations):
       - Development: Software Engineer writes/revises code
       - Code Review: Lead Engineer reviews
       - Security Review: Security Engineer reviews
       - Loop until both approve OR max iterations
    4. Deploy to Vercel
    5. Return summary + deployment link

    All code and reviews are stored in GitHub repository under .dev-team/ directory.
    """,
    steps=[
        Step(name="read_documents", executor=read_documents),
        Step(name="create_repo", executor=create_github_repo),
        Loop(
            name="implementation_cycle",
            steps=[
                Step(name="development", executor=development),
                Step(name="code_review", executor=code_review),
                Step(name="security_review", executor=security_review),
            ],
            end_condition=reviews_passed,
            max_iterations=3,
        ),
        Step(name="deploy", executor=deploy_to_vercel),
        Step(name="summary", executor=create_summary),
    ]
)
