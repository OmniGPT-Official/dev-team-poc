"""
Security Engineer Agent Configuration

The Security Engineer interacts with GitHub via MCP for reading code and storing reviews.
"""

import os
from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from agno.models.anthropic import Claude
from agno.tools.mcp import MCPTools
from instructions.security_engineer_instructions import SECURITY_ENGINEER_INSTRUCTIONS


# In-memory database for session history (use AsyncSqliteDb for persistence)
db = InMemoryDb()

github_mcp = MCPTools(
    command="npx -y @modelcontextprotocol/server-github",
    env={"GITHUB_PERSONAL_ACCESS_TOKEN": os.environ.get("GITHUB_TOKEN", "")},
    timeout_seconds=60,
)

security_engineer_agent = Agent(
    name="Security Engineer Agent",
    role="Reviews code for security vulnerabilities, ensures secure coding practices, and provides security guidance on implementations.",
    model=Claude(id="claude-sonnet-4-5"),
    db=db,
    add_history_to_context=True,  # Enabled with InMemoryDb for session context
    markdown=True,
    instructions=SECURITY_ENGINEER_INSTRUCTIONS,
    tools=[
        github_mcp,
    ]
)
