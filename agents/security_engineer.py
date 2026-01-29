"""
Security Engineer Agent Configuration

The Security Engineer can read code files and save security review reports.
"""

from pathlib import Path
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude
from agno.tools.file import FileTools
from instructions.security_engineer_instructions import SECURITY_ENGINEER_INSTRUCTIONS


# Shared output directory - all agents can read/write here
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "security_reviews").mkdir(exist_ok=True)

security_engineer_agent = Agent(
    name="Security Engineer Agent",
    role="Reviews code for security vulnerabilities, ensures secure coding practices, and provides security guidance on implementations.",
    model=Claude(id="claude-sonnet-4-5"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=SECURITY_ENGINEER_INSTRUCTIONS,
    tools=[
        FileTools(
            base_dir=OUTPUT_DIR,
            enable_read_file=True,
            enable_save_file=True,
            enable_list_files=True,
        )
    ]
)
