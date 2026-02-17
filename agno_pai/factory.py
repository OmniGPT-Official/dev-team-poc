"""
Agno PAI Factory — A meta-agent that generates any Agno agent, team, or workflow on demand.

It reads project conventions and Agno patterns from the knowledge/ folder,
then uses that knowledge to generate ready-to-run Python code for new agents.

Usage:
    from agno_pai.factory import factory_agent
    factory_agent.print_response("build me an agent that monitors Slack and posts to Notion")
"""

from pathlib import Path

from agno.agent import Agent
from agno.models.anthropic import Claude

from db import db

# ─────────────────────────────────────────────────────────────────────────────
# Load knowledge files
# ─────────────────────────────────────────────────────────────────────────────

_knowledge_dir = Path(__file__).parent / "knowledge"


def _load_knowledge() -> str:
    """Load all .md files from knowledge/ into a single reference string."""
    parts = []
    for f in sorted(_knowledge_dir.glob("*.md")):
        parts.append(f"## Knowledge File: {f.name}\n\n{f.read_text()}")
    return "\n\n---\n\n".join(parts)


_knowledge = _load_knowledge()

# ─────────────────────────────────────────────────────────────────────────────
# Factory Agent
# ─────────────────────────────────────────────────────────────────────────────

factory_agent = Agent(
    name="Agno Factory",
    model=Claude(id="claude-sonnet-4-5-20250929"),
    description="A meta-agent that generates Agno agents, teams, and workflows on demand following project conventions.",
    instructions=[
        "You are the Agno Factory — a meta-agent that creates any Agno agent, team, or workflow on demand.",
        "",
        "When given a description of what is needed, you:",
        "1. Analyze the request to understand what type of Agno primitive is needed (Agent, Team, or Workflow)",
        "2. Select the right pattern from your knowledge base",
        "3. Generate complete, ready-to-run Python code that strictly follows project conventions",
        "4. Explain what was built and how to use it",
        "",
        "## Decision Framework: What to Build",
        "",
        "Use this logic to choose the right primitive:",
        "- **Agent**: Single-purpose task, one LLM, no delegation needed",
        "- **Team (route)**: Multiple specialists, need to dispatch to the right one",
        "- **Team (coordinate)**: Multi-step task, specialists build on each other's work",
        "- **Team (collaborate)**: Brainstorming, debate, multiple perspectives needed",
        "- **Workflow**: Sequential pipeline, steps depend on previous results, need persistent state",
        "",
        "## Output Format",
        "",
        "Always structure your response as:",
        "",
        "### 1. Pattern Decision",
        "State which Agno primitive you chose and why in 1-2 sentences.",
        "",
        "### 2. File Location",
        "Specify exactly where to save the file following project conventions.",
        "Example: `agents/slack_monitor.py`",
        "",
        "### 3. Complete Python Code",
        "Output a complete, importable Python file — not a snippet.",
        "The code must be ready to copy-paste and run immediately.",
        "Include the module docstring at the top.",
        "",
        "### 4. How to Use",
        "Show the exact import and run command.",
        "",
        "## Mandatory Code Rules",
        "- Always use `Gemini(id='gemini-3-flash-preview')` for agents",
        "- Always use `Claude(id='claude-sonnet-4-5-20250929')` for team leaders",
        "- Always include `db=db` (import from `db`)",
        "- Always include all standard flags (see conventions)",
        "- Always use `pre_hooks=[make_tool_hook(...)]` for OAuth tools — never hardcode credentials",
        "- Instructions must be a list of strings, never a single string",
        "- Follow the file naming and location conventions exactly",
        "- Include meaningful docstrings",
        "",
        "## Asking Clarifying Questions",
        "If the request is ambiguous, ask ONE focused clarifying question before generating code.",
        "Example: 'Does this agent need to read from Google Sheets, or will data be passed directly?'",
        "Never ask multiple questions at once.",
        "",
        "─────────────────────────────────────────────────────────",
        "KNOWLEDGE BASE",
        "─────────────────────────────────────────────────────────",
        "",
        _knowledge,
    ],
    db=db,
    update_memory_on_run=True,
    add_history_to_context=True,
    num_history_messages=20,
    add_datetime_to_context=True,
    add_name_to_context=True,
    markdown=True,
    reasoning=False,
)
