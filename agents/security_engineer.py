"""
Security Engineer Agent Configuration

The Security Engineer can read code files, save security review reports,
and interact with GitHub via MCP for storing reviews.
"""

import os
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openrouter import OpenRouter
from instructions.security_engineer_instructions import SECURITY_ENGINEER_INSTRUCTIONS
from tools.github_tools import GitHubTools


# GitHub Tools (direct API - faster and more reliable than MCP subprocess)
github_tools = GitHubTools()

security_engineer_agent = Agent(
    name="Security Engineer Agent",
    role="Reviews code for security vulnerabilities, ensures secure coding practices, and provides security guidance on implementations.",
    model=OpenRouter(id="google/gemini-3-flash-preview"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    num_history_messages=20,
    markdown=True,
    instructions=SECURITY_ENGINEER_INSTRUCTIONS,
    tools=[
        github_tools,
    ],
    tool_call_limit=50,  # Prevent infinite loops
    debug_mode=False,
)
