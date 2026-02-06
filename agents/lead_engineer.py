"""
Lead Engineer Agent Configuration

The Lead Engineer can read PRDs, save architecture documents, code reviews,
and interact with GitHub and Supabase.
"""

import os
import sys
from pathlib import Path
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openrouter import OpenRouter
from agno.tools.mcp import MCPTools
from agno.tools.workflow import WorkflowTools
from instructions.lead_engineer_instructions import LEAD_ENGINEER_INSTRUCTIONS
from tools.github_tools import GitHubTools
from tools.google_docs_tools import GoogleDocsTools
from workflows.software_development_workflow import software_development_workflow


# GitHub Tools (direct API - more reliable than MCP)
github_tools = GitHubTools()

supabase_mcp = MCPTools(
    command=f"npx -y @supabase/mcp-server-supabase@latest --access-token={os.environ.get('SUPABASE_ACCESS_TOKEN', '')}",
    timeout_seconds=60,
)

lead_engineer_agent = Agent(
    name="Lead Engineer Agent",
    role="Designs technical architecture, creates technical specifications, provides code review guidance, and offers technical leadership on implementation approaches.",
    model=OpenRouter(id="google/gemini-3-flash-preview", max_tokens=16384),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    num_history_messages=20,
    markdown=True,
    instructions=LEAD_ENGINEER_INSTRUCTIONS,
    tools=[
        GoogleDocsTools(),
        github_tools,
        supabase_mcp,
    ],
    tool_call_limit=100,  # Higher limit for complex implementation tasks
    debug_mode=True,
)
