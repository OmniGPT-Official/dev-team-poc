"""
Lead Engineer Agent Configuration

The Lead Engineer can read PRDs, save architecture documents, code reviews,
and interact with GitHub and Supabase.
"""

import os
from pathlib import Path
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.file import FileTools
from agno.tools.mcp import MCPTools
from instructions.lead_engineer_instructions import LEAD_ENGINEER_INSTRUCTIONS
from tools.github_tools import GitHubTools


OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "architecture").mkdir(exist_ok=True)

# GitHub Tools (direct API - more reliable than MCP)
github_tools = GitHubTools()

supabase_mcp = MCPTools(
    command=f"npx -y @supabase/mcp-server-supabase@latest --access-token={os.environ.get('SUPABASE_ACCESS_TOKEN', '')}",
    timeout_seconds=60,
)

lead_engineer_agent = Agent(
    name="Lead Engineer Agent",
    role="Designs technical architecture, creates technical specifications, provides code review guidance, and offers technical leadership on implementation approaches.",
    model=Claude(id="claude-sonnet-4-20250514"),
    add_history_to_context=False,  # Disabled to prevent tool retry loops from history confusion
    markdown=True,
    instructions=LEAD_ENGINEER_INSTRUCTIONS,
    tools=[
        FileTools(
            base_dir=OUTPUT_DIR,
            enable_read_file=True,
            enable_save_file=True,
            enable_list_files=True,
        ),
        github_tools,
        supabase_mcp,
    ]
)
