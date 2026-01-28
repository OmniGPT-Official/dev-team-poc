"""
Product Lead Agent Configuration
"""

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude
from instructions.product_lead_instructions import PRODUCT_LEAD_INSTRUCTIONS


product_lead_agent = Agent(
    name="Product Lead Agent",
    model=Claude(id="claude-sonnet-4-5"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=PRODUCT_LEAD_INSTRUCTIONS
)
