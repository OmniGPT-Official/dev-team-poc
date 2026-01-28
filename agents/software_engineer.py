"""
Software Engineer Agent Configuration
"""

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude
from instructions.software_engineer_instructions import SOFTWARE_ENGINEER_INSTRUCTIONS


software_engineer_agent = Agent(
    name="Software Engineer Agent",
    role="Implements code, fixes bugs, writes tests, and creates code documentation. Handles version control and follows coding best practices.",
    model=Claude(id="claude-sonnet-4-5"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=SOFTWARE_ENGINEER_INSTRUCTIONS
)
