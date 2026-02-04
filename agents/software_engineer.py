"""
Software Engineer Agent Configuration

The Software Engineer can read technical documents, save implementation code files,
and interact with GitHub and Supabase.
"""

import os
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openrouter import OpenRouter
from agno.tools.mcp import MCPTools
from instructions.software_engineer_instructions import SOFTWARE_ENGINEER_INSTRUCTIONS
from tools.github_tools import GitHubTools
from tools.vercel_deploy_tools import VercelDeployTools


# GitHub Toolkit (direct API - more reliable than MCP)
github_tools = GitHubTools()

supabase_mcp = MCPTools(
    command=f"npx -y @supabase/mcp-server-supabase@latest --access-token={os.environ.get('SUPABASE_ACCESS_TOKEN', '')}",
    timeout_seconds=60,
)

vercel_deploy_tools = VercelDeployTools()

software_engineer_agent = Agent(
    name="Software Engineer Agent",
    role="Implements code, fixes bugs, writes tests, and creates code documentation. Handles version control and follows coding best practices.",
    model=OpenRouter(id="google/gemini-3-flash-preview"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    num_history_messages=20,
    markdown=True,
    instructions=SOFTWARE_ENGINEER_INSTRUCTIONS,
    tools=[
        github_tools,
        supabase_mcp,
        vercel_deploy_tools,
    ],
    tool_call_limit=100,  # Higher limit for code implementation
    debug_mode=False,
)
