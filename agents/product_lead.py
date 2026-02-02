"""
Product Lead Agent

Asks business questions, creates PRD or Feature Spec, writes to Google Docs.
Equipped with: GoogleDocsTools, product_requirements_workflow (lazy).
Knowledge base is provided by the team.
"""

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude

from instructions.product_lead_instructions import PRODUCT_LEAD_INSTRUCTIONS
from tools.google_docs_tools import GoogleDocsTools


product_lead_agent = Agent(
    name="Product Lead",
    role="Conducts product discovery, creates PRDs and Feature Specs, writes documents to Google Docs.",
    model=Claude(id="claude-sonnet-4-20250514"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=PRODUCT_LEAD_INSTRUCTIONS,
    tools=[
        GoogleDocsTools(),
    ],
)


# Workflow tool is added lazily to avoid circular imports
_workflow_tools_added = False


def add_workflow_tools():
    """
    Add workflow tools to the product lead agent.

    Adds:
    - Product Requirements Workflow (for creating PRD/Feature Spec)
    - Software Development Workflow (for implementation after permission)
    """
    global _workflow_tools_added
    if _workflow_tools_added:
        return

    from agno.tools.workflow import WorkflowTools
    from workflows.product_requirements_workflow import product_requirements_workflow
    from workflows.software_development_workflow import software_development_workflow

    # Add product requirements workflow
    product_lead_agent.tools.append(
        WorkflowTools(
            workflow=product_requirements_workflow,
            enable_run_workflow=True,
            add_instructions=True,
        )
    )

    # Add software development workflow (triggered after permission)
    product_lead_agent.tools.append(
        WorkflowTools(
            workflow=software_development_workflow,
            enable_run_workflow=True,
            add_instructions=True,
        )
    )

    _workflow_tools_added = True
