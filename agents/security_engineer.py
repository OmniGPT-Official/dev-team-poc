"""
Security Engineer Agent Configuration

The Security Engineer can read code files, save security review reports,
and interact with GitHub via MCP for storing reviews.
"""

import os
import sys
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

# Validate required environment variables
github_token = os.environ.get("GITHUB_TOKEN", "")
if not github_token:
    print("=" * 80, file=sys.stderr)
    print("⚠️  WARNING: GITHUB_TOKEN environment variable is not set!", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print("", file=sys.stderr)
    print("Workflows that require GitHub MCP will fail with authorization errors.", file=sys.stderr)
    print("", file=sys.stderr)
    print("To fix this:", file=sys.stderr)
    print("1. Create a GitHub Personal Access Token:", file=sys.stderr)
    print("   https://github.com/settings/tokens", file=sys.stderr)
    print("2. Required scope: 'repo' (full control of private repositories)", file=sys.stderr)
    print("3. Add to your .env file: GITHUB_TOKEN=ghp_your_token_here", file=sys.stderr)
    print("4. Restart the application", file=sys.stderr)
    print("", file=sys.stderr)
    print("See MCP_SETUP_GUIDE.md for detailed instructions.", file=sys.stderr)
    print("=" * 80, file=sys.stderr)

# GitHub MCP for storing security reviews in the target repository
github_mcp = MCPTools(
    command="npx -y @modelcontextprotocol/server-github",
    env={"GITHUB_PERSONAL_ACCESS_TOKEN": github_token},
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
