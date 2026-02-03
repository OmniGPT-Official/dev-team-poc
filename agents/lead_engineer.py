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
from agno.tools.workflow import WorkflowTools
from instructions.lead_engineer_instructions import LEAD_ENGINEER_INSTRUCTIONS
from tools.github_tools import GitHubTools
from tools.google_docs_tools import GoogleDocsTools
from workflows.software_development_workflow import software_development_workflow


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
    add_history_to_context=True,
    num_history_messages=20,  # Keep last 20 messages in context
    markdown=True,
    instructions=LEAD_ENGINEER_INSTRUCTIONS,
    tools=[
        FileTools(
            base_dir=OUTPUT_DIR,
            enable_read_file=True,
            enable_save_file=True,
            enable_list_files=True,
        ),
        GoogleDocsTools(),
        github_tools,
        supabase_mcp,
        WorkflowTools(
            workflow=software_development_workflow,
            enable_run_workflow=True,
            add_instructions=True,
        ),
    ],
    tool_call_limit=100,  # Higher limit for complex implementation tasks
    debug_mode=False,
)
