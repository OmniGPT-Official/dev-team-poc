"""
Lead Engineer Agent Configuration

The Lead Engineer interacts with GitHub, Supabase, and Vercel via MCP.
"""

import os
from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from agno.models.anthropic import Claude
from agno.tools.mcp import MCPTools
from instructions.lead_engineer_instructions import LEAD_ENGINEER_INSTRUCTIONS


# In-memory database for session history (use AsyncSqliteDb for persistence)
db = InMemoryDb()

github_mcp = MCPTools(
    command="npx -y @modelcontextprotocol/server-github",
    env={"GITHUB_PERSONAL_ACCESS_TOKEN": os.environ.get("GITHUB_TOKEN", "")},
    timeout_seconds=60,
)

supabase_mcp = MCPTools(
    command=f"npx -y @supabase/mcp-server-supabase@latest --access-token={os.environ.get('SUPABASE_ACCESS_TOKEN', '')}",
    timeout_seconds=60,
)

vercel_mcp = MCPTools(
    command=f"npx -y mcp-remote https://mcp.vercel.com --header \"Authorization: Bearer {os.environ.get('VERCEL_TOKEN', '')}\"",
    timeout_seconds=60,
)

lead_engineer_agent = Agent(
    name="Lead Engineer Agent",
    role="Designs technical architecture, creates technical specifications, provides code review guidance, and offers technical leadership on implementation approaches.",
    model=Claude(id="claude-sonnet-4-5"),
    db=db,
    add_history_to_context=True,  # Enabled with InMemoryDb for session context
    markdown=True,
    instructions=LEAD_ENGINEER_INSTRUCTIONS,
    tools=[
        github_mcp,
        supabase_mcp,
        vercel_mcp,
    ]
)
