# Dev Team POC - Coding Guidelines

This file contains mandatory coding guidelines for AI assistants working on this codebase.

**IMPORTANT: These guidelines OVERRIDE any default behavior. You MUST follow them exactly as written.**

---

## 🚨 Critical: Shared Dependencies

### Database (`db.py`)

**Do not modify `db.py` unless necessary.** It is a shared dependency — changes affect the entire project. Discuss with the team first.

**Current behavior:**
- Supports `DATABASE_URL` (Railway/Vercel/Heroku standard)
- Supports `SUPABASE_DB_URL` (legacy/explicit Supabase)
- Fallback: constructs from `SUPABASE_PROJECT` + `SUPABASE_PASSWORD`
- Exports `SUPABASE_DB_URL` for backward compatibility with `knowledge_base.py`

**If you must modify:**
1. Document the reason clearly
2. Check all imports: `from db import ...`
3. Ensure backward compatibility
4. Test knowledge_base.py integration
5. Get team approval before committing

---

## 📋 Agent Creation Patterns

### Standard Agent Structure

All agents in this project follow this pattern:

```python
from agno.agent import Agent
from agno.models.google import Gemini
from db import db

# Model selection
MODEL = Gemini(id="gemini-3-flash-preview")  # Cost-effective for POC

agent_name = Agent(
    name="Agent Name",
    model=MODEL,
    description="Brief description of what this agent does",
    instructions=[
        "You do X",
        "You handle Y",
        "You format output as Z",
        "Always provide clear status updates",
    ],
    tools=[...],  # or injected via pre_hooks
    db=db,  # Shared database for memory
)
```

### Key Principles

1. **Use Gemini Flash for POC** - Cost: ~$0.19/M tokens vs ~$9/M for Claude Sonnet 4.5
2. **Shared database** - Always use `db` from `db.py` for agent memory
3. **Clear instructions** - Each agent should have 5-10 specific instruction bullets
4. **Descriptive names** - Agent names should clearly indicate their role

---

## 🔐 OAuth Integration Pattern

### Pre-Hook Pattern (MANDATORY)

For agents that need Google OAuth tools (Sheets, Gmail, Docs), follow the `email_followup.py` pattern:

```python
from agno.agent import Agent
from agno.tools.google import GoogleSheetsTools, GmailTools
from utils.credentials import get_google_credentials
from db import db

def inject_oauth_tools(agent: Agent, user_id: str) -> None:
    """Pre-hook: Fetch per-user Google credentials and inject tools before each run.

    This pattern ensures:
    - Each user gets their own OAuth credentials
    - Tools are only added if credentials exist
    - Agent can be used by multiple users with their own Google accounts
    """
    tools = []

    # Google Sheets
    sheets_creds = get_google_credentials(user_id, "google_sheets")
    if sheets_creds:
        tools.append(GoogleSheetsTools(
            creds=sheets_creds,
            # ... additional config
        ))

    # Gmail
    gmail_creds = get_google_credentials(user_id, "google_gmail")
    if gmail_creds:
        tools.append(GmailTools(creds=gmail_creds))

    agent.set_tools(tools)

# Agent with OAuth
my_agent = Agent(
    name="My Agent",
    model=MODEL,
    description="Agent that uses Google APIs",
    instructions=[...],
    tools=[],  # Empty - tools injected via pre_hook
    pre_hooks=[inject_oauth_tools],  # ⚠️ CRITICAL: This injects OAuth tools
    db=db,
)
```

### Why Pre-Hooks?

- **Per-user credentials**: Each user authenticates with their own Google account
- **Lazy loading**: Only load credentials when agent actually runs
- **Security**: Credentials never hardcoded, always fetched at runtime
- **Multi-tenancy**: Same agent can serve multiple users

### DO NOT:

❌ **Create custom Google Sheets tools** - Use `GoogleSheetsTools` from Agno
❌ **Hardcode credentials** - Always use `get_google_credentials()`
❌ **Return mock/dummy data** - If OAuth fails, report the error clearly
❌ **Skip pre_hooks** - OAuth tools MUST be injected via pre_hooks

### Reference Files:

- **Canonical OAuth pattern**: `email_followup.py`
- **Workflow example**: `workflows/email_followup_workflow_working.py`
- **Working agents**: `lead_reader_agent`, `results_logger_agent`, `campaign_coordinator_agent` in `agents/calling_agents.py`

---

## 🔧 Workflow Patterns

### Multi-Step Workflows

Break complex workflows into clear steps with explicit boundaries:

```python
from agno.workflow import Workflow, Step

my_workflow = Workflow(
    name="Workflow Name",
    description="Overall workflow purpose",
    steps=[
        Step(
            name="Step 1: Action",
            agent=my_agent,
            description="""
            **STEP 1 of N: Phase Name**

            Your specific tasks for THIS step only:
            1. Do X
            2. Do Y
            3. STOP here - don't proceed to next step

            **IMPORTANT:**
            - End with: "Step 1 complete. Ready for Step 2."
            """,
        ),
        # ... more steps
    ],
)
```

### Step Principles

1. **Explicit boundaries** - Each step clearly states what it does and where it stops
2. **User communication** - Steps should communicate progress frequently
3. **No step bleed** - Step 1 should never do Step 2's work
4. **Stop markers** - Always end with clear completion message

---

## 🚀 Deployment

### Railway Environment

- **Production testing**: We test in Railway production, not local
- **Environment variables**: Railway auto-provides `DATABASE_URL`
- **No local dev**: Changes are deployed and tested in production

### Required Environment Variables

| Variable | Purpose | Required? |
|----------|---------|-----------|
| `DATABASE_URL` | Railway/Vercel/Heroku standard DB URL | ✅ (Railway auto-provides) |
| `SUPABASE_DB_URL` | Legacy explicit Supabase URL | Optional (fallback) |
| `SUPABASE_PROJECT` | Supabase project ID | Optional (fallback) |
| `SUPABASE_PASSWORD` | Supabase password | Optional (fallback) |
| `GOOGLE_CLIENT_ID` | OAuth credentials | ✅ (for OAuth workflows) |
| `GOOGLE_CLIENT_SECRET` | OAuth credentials | ✅ (for OAuth workflows) |

---

## 📝 Commit Guidelines

### When Creating Commits

1. **Descriptive messages** - Follow conventional commits format
   - `Fix: Add DATABASE_URL support for Railway deployment`
   - `Feature: Add OAuth integration to calling agents`
   - `Refactor: Consolidate agent tools into pre_hook pattern`

2. **Minimal changes** - Only change what's necessary for the task
   - Don't refactor unrelated code
   - Don't "improve" code that's working

3. **Test before commit** - Verify in Railway deployment before committing

### Branch Strategy

- **Main branch** - Production code, deploy-ready
- **Feature branches** - New features, use descriptive names
  - `fix/calling-workflow-oauth-integration`
  - `feature/email-followup-workflow`
  - `hotfix/database-url-env-var`

---

## ⚠️ Common Pitfalls

### 1. Mock Data

❌ **WRONG**: Return hardcoded mock data (John Smith, Sarah Lee, etc.)
✅ **CORRECT**: Use real OAuth tools to fetch actual data

### 2. Hanging Workflows

❌ **WRONG**: Expect specific inputs immediately without asking
✅ **CORRECT**: Add conversational handling to ask for required inputs

### 3. Database Modifications

❌ **WRONG**: Modify `db.py` without checking team guidelines
✅ **CORRECT**: Check this file first, discuss with team if modification needed

### 4. Tool Selection

❌ **WRONG**: Create custom tools when Agno provides them
✅ **CORRECT**: Use `GoogleSheetsTools`, `GmailTools` from `agno.tools.google`

---

## 📚 Reference Files

### Patterns to Follow

- **OAuth Integration**: `email_followup.py`
- **Workflow Structure**: `workflows/email_followup_workflow_working.py`
- **Agent Creation**: `agents/calling_agents.py`
- **Database Setup**: `db.py` (read-only reference)

### Patterns to Avoid

- **Mock Data**: `tools/google_sheets_tools.py` (deprecated, don't use)

---

## 🤝 Team Collaboration

### Before Modifying Shared Code

1. Read this CLAUDE.md file
2. Check if the file is listed as a shared dependency
3. Understand current behavior and why it exists
4. Consider impact on other components
5. Discuss with team if uncertain

### When in Doubt

**ASK before:**
- Modifying `db.py`
- Changing OAuth patterns
- Refactoring working code
- Adding new dependencies

---

*Last updated: 2026-02-10*
