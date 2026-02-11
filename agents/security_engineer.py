"""
Security Engineer Agent Configuration

The Security Engineer can read code files, save security review reports,
and interact with GitHub via MCP for storing reviews.

Tools are injected per-user at runtime via the pre-hook (tool_injector).
"""

from agno.agent import Agent
from db import db
from agno.models.openrouter import OpenRouter
from instructions.security_engineer_instructions import SECURITY_ENGINEER_INSTRUCTIONS
from services.tool_injector import inject_user_tools

security_engineer_agent = Agent(
    name="Security Engineer Agent",
    role="Reviews code for security vulnerabilities, ensures secure coding practices, and provides security guidance on implementations.",
    model=OpenRouter(id="google/gemini-3-flash-preview", max_tokens=8192),
    db=db,
    add_history_to_context=True,
    num_history_messages=20,
    markdown=True,
    instructions=SECURITY_ENGINEER_INSTRUCTIONS,
    tools=[],  # Tools injected via pre_hooks
    pre_hooks=[inject_user_tools],  # Inject per-user GitHub tools
    tool_call_limit=50,  # Prevent infinite loops
    debug_mode=False,
)
