"""
Software Engineer Agent Configuration

The Software Engineer can read technical documents, save implementation code files,
and interact with GitHub and Supabase.

Tools are injected per-user at runtime via the pre-hook (tool_injector).
Default tool instances here serve as fallbacks for local/dev usage.
"""

from agno.agent import Agent
from db import db
from agno.models.anthropic import Claude
from instructions.software_engineer_instructions import SOFTWARE_ENGINEER_INSTRUCTIONS
from services.tool_injector import inject_user_tools

software_engineer_agent = Agent(
    name="Software Engineer Agent",
    role="Implements code, fixes bugs, writes tests, and creates code documentation. Handles version control and follows coding best practices.",
    model=Claude(id="claude-sonnet-4-5-20250929", max_tokens=16384),
    db=db,
    add_history_to_context=True,
    num_history_messages=20,
    markdown=True,
    instructions=SOFTWARE_ENGINEER_INSTRUCTIONS,
    tools=[],  # Tools injected via pre_hooks
    pre_hooks=[inject_user_tools],  # Inject per-user GitHub, Vercel, Google Docs tools
    tool_call_limit=100,
    debug_mode=False,
)
