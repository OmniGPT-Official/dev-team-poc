"""
Product Lead Agent

Asks business questions, triggers Product Requirements Workflow.
Workflow creates PRD or Feature Spec and saves to Google Docs.
After PRD creation, delegates to Lead Engineer for implementation.
"""

from agno.agent import Agent
from db import db
from agno.models.openrouter import OpenRouter

from instructions.product_lead_instructions import PRODUCT_LEAD_INSTRUCTIONS
from tools.google_docs_tools import GoogleDocsTools


product_lead_agent = Agent(
    name="Product Lead",
    role="Conducts product discovery, creates PRDs/Feature Specs in Google Docs, then delegates to Lead Engineer for implementation.",
    model=OpenRouter(id="google/gemini-3-flash-preview", max_tokens=16384),
    db=db,
    add_history_to_context=True,
    num_history_messages=20,  # Keep last 20 messages in context
    markdown=True,
    instructions=PRODUCT_LEAD_INSTRUCTIONS,
    tools=[
        GoogleDocsTools(),
    ],
    tool_call_limit=50,  # Prevent infinite tool call loops
    debug_mode=True,
)
