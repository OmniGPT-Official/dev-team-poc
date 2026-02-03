"""
Product Lead Agent

Asks business questions, creates PRD or Feature Spec, saves to Google Docs.
After PRD creation, delegates to Lead Engineer for implementation.
"""

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude

from instructions.product_lead_instructions import PRODUCT_LEAD_INSTRUCTIONS
from tools.google_docs_tools import GoogleDocsTools


product_lead_agent = Agent(
    name="Product Lead",
    role="Conducts product discovery, creates PRDs and Feature Specs, saves to Google Docs, then delegates to Lead Engineer for implementation.",
    model=Claude(id="claude-sonnet-4-20250514"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=PRODUCT_LEAD_INSTRUCTIONS,
    tools=[GoogleDocsTools()],
)
