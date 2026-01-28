"""
Lead Engineer Agent Configuration
"""

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude
from instructions.lead_engineer_instructions import LEAD_ENGINEER_INSTRUCTIONS


lead_engineer_agent = Agent(
    name="Lead Engineer Agent",
    role="Designs technical architecture, creates technical specifications, provides code review guidance, and offers technical leadership on implementation approaches.",
    model=Claude(id="claude-sonnet-4-5"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=LEAD_ENGINEER_INSTRUCTIONS
)
