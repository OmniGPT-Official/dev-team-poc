"""
Lead Engineer Agent Configuration

The Lead Engineer can read PRDs, save architecture documents, code reviews,
and interact with GitHub and Supabase.

Tools are injected per-user at runtime via the pre-hook (tool_injector).
Default tool instances here serve as fallbacks for local/dev usage.
"""

from agno.agent import Agent
from db import db
from agno.models.openrouter import OpenRouter
from instructions.lead_engineer_instructions import LEAD_ENGINEER_INSTRUCTIONS
from services.tool_injector import make_tool_hook

lead_engineer_agent = Agent(
    name="Lead Engineer Agent",
    role="Designs technical architecture, creates technical specifications, provides code review guidance, and offers technical leadership on implementation approaches.",
    model=OpenRouter(id="google/gemini-3-flash-preview", max_tokens=16384),
    db=db,
    add_history_to_context=True,
    num_history_messages=20,
    markdown=True,
    instructions=LEAD_ENGINEER_INSTRUCTIONS,
    tools=[],  # Tools injected via pre_hooks
    pre_hooks=[make_tool_hook("google_docs", "github")],  # Inject per-user Google Docs and GitHub tools (updated from inject_user_tools)
    tool_call_limit=100,
    debug_mode=False,
    reasoning=False,  # Explicitly disable reasoning to avoid Gemini API errors
)
