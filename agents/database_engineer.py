"""
Database Engineer Agent Configuration

The Database Engineer manages database schema design, validation, and Supabase operations.

Tools are injected per-user at runtime via the pre-hook (tool_injector).
"""

from pathlib import Path
from agno.agent import Agent
from agno.skills import Skills, LocalSkills
from db import db
from agno.models.openrouter import OpenRouter
from instructions.database_engineer_instructions import DATABASE_ENGINEER_INSTRUCTIONS
from services.tool_injector import make_tool_hook

# Get skills directory relative to this file
skills_dir = Path(__file__).parent.parent / "skills"

database_engineer_agent = Agent(
    name="Database Engineer Agent",
    role="Designs and manages database schemas, validates data models, handles Supabase operations, and ensures database security and performance.",
    model=OpenRouter(id="google/gemini-3-flash-preview", max_tokens=16384),
    db=db,
    add_history_to_context=True,
    num_history_messages=20,
    markdown=True,
    instructions=DATABASE_ENGINEER_INSTRUCTIONS,
    skills=Skills(loaders=[LocalSkills(str(skills_dir))]),  # Load all skills (database-schema-design)
    tools=[],  # Tools injected via pre_hooks
    pre_hooks=[make_tool_hook("supabase_mcp", "github")],  # Inject per-user Supabase and GitHub tools
    tool_call_limit=100,
    debug_mode=False,
    reasoning=False,  # Explicitly disable reasoning to avoid Gemini API errors
)
