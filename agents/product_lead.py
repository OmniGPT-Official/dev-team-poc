"""
Product Lead Agent Configuration

The Product Lead creates PRDs and coordinates product development.
"""

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude
from instructions.product_lead_instructions import PRODUCT_LEAD_INSTRUCTIONS


# Create the product lead agent
product_lead_agent = Agent(
    name="Product Lead",
    role="Creates PRDs, structured tickets, product descriptions, goal setting (OKRs), and RICE prioritization.",
    model=Claude(id="claude-sonnet-4-5"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=PRODUCT_LEAD_INSTRUCTIONS
)
