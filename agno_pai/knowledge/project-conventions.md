# Project Conventions — dev-team-poc

These are the mandatory conventions for all agents in this project.
Always follow these when generating new agents, teams, or workflows.

---

## Models

| Role | Model | Import |
|------|-------|--------|
| Default agent | `Gemini(id="gemini-3-flash-preview")` | `from agno.models.google import Gemini` |
| Team leader / coordinator | `Claude(id="claude-sonnet-4-5-20250929")` | `from agno.models.anthropic import Claude` |
| Compression | `Gemini(id="gemini-3-flash-preview")` | same as above |

**Never use any other model IDs unless explicitly requested.**

---

## Standard Agent Flags

Every agent MUST include these flags:

```python
agent = Agent(
    db=db,                            # REQUIRED — shared Postgres DB
    add_history_to_context=True,      # REQUIRED
    num_history_messages=10,          # REQUIRED — prevents unbounded growth
    add_datetime_to_context=True,     # REQUIRED
    add_name_to_context=True,         # REQUIRED
    markdown=True,                    # REQUIRED
    reasoning=False,                  # REQUIRED — keep False for speed
    update_memory_on_run=True,        # include if agent needs memory
)
```

---

## Database

```python
from db import db  # ALWAYS import from db.py — never create a new DB connection
```

**Never modify `db.py`.** It is a shared dependency.

---

## Tool Injection

OAuth and API-key tools MUST use pre-hooks. Never hardcode credentials.

```python
from services.tool_injector import make_tool_hook

agent = Agent(
    pre_hooks=[make_tool_hook("google_sheets", "google_gmail")],
    db=db,
)
```

Only list providers the agent actually uses.

---

## File Naming & Location

| What | Where | Naming |
|------|-------|--------|
| Single agent | root directory | `my_agent.py` |
| Agent used in a team | `agents/` | `agents/my_agent.py` |
| Team | `teams/` | `teams/my_team.py` |
| Workflow | `workflows/` | `workflows/my_workflow.py` |
| Custom tool | `tools/` | `tools/my_tool.py` |
| Agent instructions | `instructions/` | `instructions/my_agent_instructions.py` |

---

## Agent Instructions Style

Instructions are a **list of strings**, not a single string.
Each string is a line or section of the prompt.

```python
instructions=[
    "You are a [role] that [does what].",
    "",
    "## Section Name",
    "Rule 1.",
    "Rule 2.",
    "",
    "## Another Section",
    "More rules.",
],
```

---

## PR & Commit Rules

- Branch naming: `feature/<brief-desc>`, `fix/<brief-desc>`, `hotfix/<brief-desc>`
- Never push directly to main
- Add reviewers: **Muhammad-Anique** and **albgarrido**
- Squash merge: `gh pr merge <number> --squash --delete-branch`
- Never alter git history on pushed branches

---

## Existing Agents (as examples / references)

| File | What it does | Pattern |
|------|-------------|---------|
| `email_followup.py` | Sales follow-up via Gmail + Sheets | Agent with pre_hooks, CompressionManager |
| `content_creation.py` | Multi-phase content creation | Team (coordinate), Claude leader |
| `campaign_manager.py` | Campaign management | Agent |
| `agno_agent.py` | General purpose agent | Agent |
| `agents/` | Specialized team member agents | Various |
| `teams/` | Multi-agent teams | Team |
| `workflows/` | Multi-step workflows | Workflow |

When generating a new agent, check these files as reference for patterns.
