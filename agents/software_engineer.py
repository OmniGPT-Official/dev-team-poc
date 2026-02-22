"""
Software Engineer Agent Configuration

The Software Engineer can read technical documents, save implementation code files,
and interact with GitHub and Supabase.

Tools are injected per-user at runtime via the pre-hook (tool_injector).
Default tool instances here serve as fallbacks for local/dev usage.
"""

from pathlib import Path
from agno.agent import Agent
from agno.skills import Skills, LocalSkills
from agno.compression.manager import CompressionManager
from db import db
from agno.models.moonshot import MoonShot
from instructions.software_engineer_instructions import SOFTWARE_ENGINEER_INSTRUCTIONS
from services.tool_injector import inject_user_tools

# Skills directory is two levels up from this file (agents/ → project root → skills/)
_skills_dir = Path(__file__).parent.parent / "skills"

# Custom compression manager: compress after 6 tool results accumulate in context
# (default is 3 — slightly relaxed for a coding agent that reads multiple files per task)
_compression_manager = CompressionManager(compress_tool_results_limit=6)

software_engineer_agent = Agent(
    name="Software Engineer Agent",
    role="Implements code, fixes bugs, writes tests, and creates code documentation. Handles version control and follows coding best practices.",
    model=MoonShot(id="kimi-k2.5", max_tokens=16384, extra_body={"thinking": {"type": "disabled"}}),
    db=db,
    add_history_to_context=True,
    num_history_messages=5,               # Reduced from 20 — prevents context explosion over long sessions
    compress_tool_results=True,           # Enable tool result compression
    compression_manager=_compression_manager,  # Compress after 20 results (not the default 3)
    max_tool_calls_from_history=15,       # Cap historical tool calls loaded into context
    enable_session_summaries=True,        # Auto-generate session summaries to replace raw history
    add_session_summary_to_context=True,  # Inject summary instead of full raw history
    markdown=True,
    instructions=SOFTWARE_ENGINEER_INSTRUCTIONS,
    skills=Skills(loaders=[LocalSkills(str(_skills_dir))]),  # Loads task-execution + all available skills
    tools=[],  # Tools injected via pre_hooks
    pre_hooks=[inject_user_tools],  # Inject per-user GitHub, Vercel, Google Docs tools
    tool_call_limit=100,
    debug_mode=False,
)
