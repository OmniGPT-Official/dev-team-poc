"""
Lead Engineer Agent Configuration

The Lead Engineer can read PRDs, save architecture documents, code reviews,
and interact with GitHub and Supabase.

Tools are injected per-user at runtime via the pre-hook (tool_injector).
Default tool instances here serve as fallbacks for local/dev usage.
"""

from pathlib import Path
from agno.agent import Agent
from agno.skills import Skills, LocalSkills
from agno.compression.manager import CompressionManager
from db import db
from agno.models.openrouter import OpenRouter
from instructions.lead_engineer_instructions import LEAD_ENGINEER_INSTRUCTIONS
from services.tool_injector import make_tool_hook

# Get skills directory relative to this file
skills_dir = Path(__file__).parent.parent / "skills"

# Custom compression manager: only compress after 20 tool results accumulate in context
# (default is 3 — far too aggressive for an agent that reads docs and reviews code files)
_compression_manager = CompressionManager(compress_tool_results_limit=6)

lead_engineer_agent = Agent(
    name="Lead Engineer Agent",
    role="Designs technical architecture, creates technical specifications, provides code review guidance, and offers technical leadership on implementation approaches.",
    model=OpenRouter(id="google/gemini-3-flash-preview", max_tokens=16384),
    db=db,
    add_history_to_context=True,
    num_history_messages=5,               # Reduced from 20 — prevents context explosion over long sessions
    compress_tool_results=True,           # Enable tool result compression
    compression_manager=_compression_manager,  # Compress after 20 results (not the default 3)
    max_tool_calls_from_history=15,       # Cap historical tool calls loaded into context
    enable_session_summaries=True,        # Auto-generate session summaries to replace raw history
    add_session_summary_to_context=True,  # Inject summary instead of full raw history
    markdown=True,
    instructions=LEAD_ENGINEER_INSTRUCTIONS,
    skills=Skills(loaders=[LocalSkills(str(skills_dir))]),  # Load all skills (architecture-creation, code-review, database-schema-design)
    tools=[],  # Tools injected via pre_hooks
    pre_hooks=[make_tool_hook("google_docs", "github")],  # Inject per-user Google Docs and GitHub tools (updated from inject_user_tools)
    tool_call_limit=100,
    debug_mode=False,
    reasoning=False,  # Explicitly disable reasoning to avoid Gemini API errors
)
