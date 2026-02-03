"""
Software Engineer Agent Configuration

The Software Engineer can read technical documents, save implementation code files,
and interact with GitHub and Supabase.
"""

import os
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.mcp import MCPTools
from instructions.software_engineer_instructions import SOFTWARE_ENGINEER_INSTRUCTIONS
from tools.github_tools import GitHubTools


# GitHub Tools (direct API - more reliable than MCP)
github_tools = GitHubTools()

supabase_mcp = MCPTools(
    command=f"npx -y @supabase/mcp-server-supabase@latest --access-token={os.environ.get('SUPABASE_ACCESS_TOKEN', '')}",
    timeout_seconds=60,
)

# vercel_mcp = MCPTools(
#     command=f"npx -y mcp-remote https://mcp.vercel.com --header \"Authorization: Bearer {os.environ.get('VERCEL_TOKEN', '')}\"",
#     timeout_seconds=60,
# )

software_engineer_agent = Agent(
    name="Software Engineer Agent",
    role="Implements code, fixes bugs, writes tests, and creates code documentation. Handles version control and follows coding best practices.",
    model=Claude(id="claude-sonnet-4-20250514"),
    add_history_to_context=True,
    num_history_messages=15,  # Keep last 15 messages in context
    markdown=True,
    instructions=SOFTWARE_ENGINEER_INSTRUCTIONS,
    tools=[
        github_tools,
        supabase_mcp,
    ],
    tool_call_limit=100,  # Higher limit for code implementation
    debug_mode=False,
)
