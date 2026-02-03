"""
Security Engineer Agent Configuration

The Security Engineer can read code files, save security review reports,
and interact with GitHub via MCP for storing reviews.
"""

import os
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.mcp import MCPTools
from instructions.security_engineer_instructions import SECURITY_ENGINEER_INSTRUCTIONS


# GitHub MCP
github_mcp = MCPTools(
    command=f"npx -y @modelcontextprotocol/server-github",
    env={"GITHUB_PERSONAL_ACCESS_TOKEN": os.environ.get("GITHUB_TOKEN", "")},
    timeout_seconds=60,
)

security_engineer_agent = Agent(
    name="Security Engineer Agent",
    role="Reviews code for security vulnerabilities, ensures secure coding practices, and provides security guidance on implementations.",
    model=Claude(id="claude-sonnet-4-20250514"),
    add_history_to_context=True,
    num_history_messages=10,  # Keep last 10 messages in context
    markdown=True,
    instructions=SECURITY_ENGINEER_INSTRUCTIONS,
    tools=[
        github_mcp,
    ],
    tool_call_limit=50,  # Prevent infinite loops
    debug_mode=False,
)
