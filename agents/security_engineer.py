"""
Security Engineer Agent Configuration

The Security Engineer can read code files, save security review reports,
and interact with GitHub via MCP for storing reviews.
"""

import os
from pathlib import Path
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.file import FileTools
from agno.tools.mcp import MCPTools
from instructions.security_engineer_instructions import SECURITY_ENGINEER_INSTRUCTIONS


# Shared output directory - all agents can read/write here (fallback for local operations)
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "security_reviews").mkdir(exist_ok=True)

# GitHub MCP for storing security reviews in the target repository
github_mcp = MCPTools(
    command="npx -y @modelcontextprotocol/server-github",
    env={"GITHUB_PERSONAL_ACCESS_TOKEN": os.environ.get("GITHUB_TOKEN", "")},
    timeout_seconds=60,  # Increased timeout for npx package download
)

security_engineer_agent = Agent(
    name="Security Engineer Agent",
    role="Reviews code for security vulnerabilities, ensures secure coding practices, and provides security guidance on implementations.",
    model=Claude(id="claude-sonnet-4-5"),
    add_history_to_context=False,  # Disabled to prevent tool retry loops from history confusion
    markdown=True,
    instructions=SECURITY_ENGINEER_INSTRUCTIONS,
    tools=[
        FileTools(
            base_dir=OUTPUT_DIR,
            enable_read_file=True,
            enable_save_file=True,
            enable_list_files=True,
        ),
        github_mcp,
    ]
)
