"""
Software Engineer Agent Configuration

The Software Engineer can read technical documents, save implementation code files,
and interact with GitHub, Supabase, and Vercel via MCP.
"""

import os
from pathlib import Path
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.file import FileTools
from agno.tools.mcp import MCPTools
from instructions.software_engineer_instructions import SOFTWARE_ENGINEER_INSTRUCTIONS


OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "implementations").mkdir(exist_ok=True)

github_mcp = MCPTools(
    command="npx -y @modelcontextprotocol/server-github",
    env={"GITHUB_PERSONAL_ACCESS_TOKEN": os.environ.get("GITHUB_TOKEN", "")},
    timeout_seconds=60,  # Increased timeout for npx package download
)

supabase_mcp = MCPTools(
    command=f"npx -y @supabase/mcp-server-supabase@latest --access-token={os.environ.get('SUPABASE_ACCESS_TOKEN', '')}",
    timeout_seconds=60,
)

vercel_mcp = MCPTools(
    command=f"npx -y mcp-remote https://mcp.vercel.com --header \"Authorization: Bearer {os.environ.get('VERCEL_TOKEN', '')}\"",
    timeout_seconds=60,
)

software_engineer_agent = Agent(
    name="Software Engineer Agent",
    role="Implements code, fixes bugs, writes tests, and creates code documentation. Handles version control and follows coding best practices.",
    model=Claude(id="claude-sonnet-4-5"),
    add_history_to_context=False,  # Disabled to prevent tool retry loops from history confusion
    markdown=True,
    instructions=SOFTWARE_ENGINEER_INSTRUCTIONS,
    tools=[
        FileTools(
            base_dir=OUTPUT_DIR,
            enable_read_file=True,
            enable_save_file=True,
            enable_list_files=True,
        ),
        github_mcp,
        supabase_mcp,
        vercel_mcp,
    ]
)
