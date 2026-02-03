"""
Product Lead Agent

Asks business questions, triggers Product Requirements Workflow.
Workflow creates PRD or Feature Spec and saves to Google Docs.
After PRD creation, delegates to Lead Engineer for implementation.
"""

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude
from agno.tools.workflow import WorkflowTools

from instructions.product_lead_instructions import PRODUCT_LEAD_INSTRUCTIONS
from workflows.product_requirements_workflow import product_requirements_workflow


product_lead_agent = Agent(
    name="Product Lead",
    role="Conducts product discovery, triggers Product Requirements Workflow to create PRDs/Feature Specs, then delegates to Lead Engineer for implementation.",
    model=Claude(id="claude-sonnet-4-20250514"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=PRODUCT_LEAD_INSTRUCTIONS,
    tools=[
        WorkflowTools(
            workflow=product_requirements_workflow,
            enable_run_workflow=True,
            add_instructions=True,
        ),
    ],
)
