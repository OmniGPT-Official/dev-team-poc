"""
Product Team Configuration

This module defines the product development team equipped with workflow tools
for software development and implementation.
"""

from agno.db.in_memory import InMemoryDb
from agno.team import Team
from agno.models.anthropic import Claude
from agno.tools.workflow import WorkflowTools

from agents.product_lead import product_lead_agent
from agents.research_agent import research_agent
from agents.lead_engineer import lead_engineer_agent
from agents.software_engineer import software_engineer_agent

from workflows.software_development_workflow import software_development_workflow
from workflows.implementation_cycle_workflow import implementation_cycle_workflow


# In-memory database for team session history
db = InMemoryDb()

# Create workflow tools for the team
software_dev_tools = WorkflowTools(
    workflow=software_development_workflow,
)

implementation_tools = WorkflowTools(
    workflow=implementation_cycle_workflow,
    async_mode=True,  # Required for async executors using MCP tools
)

# Product Development Team with workflow tools
product_team = Team(
    name="Product Development Team",
    model=Claude(id="claude-sonnet-4-5"),
    db=db,
    add_history_to_context=True,
    members=[
        product_lead_agent,
        research_agent,
        lead_engineer_agent,
        software_engineer_agent,
    ],
    # tools=[software_dev_tools, implementation_tools],  # Team-level workflow tools
    tools=[implementation_tools],  # Team-level workflow tools
    instructions=[
        "You are the Product Development Team.",
        "You have access to TWO workflow tools:",
        "",
        "1. **Software Development Workflow** - Creates PRD and Technical Architecture",
        "   - Use this first to analyze requirements and design the solution",
        "   - Output: PRD and Architecture documents in the conversation",
        "",
        "2. **Implementation Cycle Workflow** - Implements code with review loops",
        "   - Use AFTER user approves the PRD/Architecture",
        "   - Loops until code review and security review approve",
        "",
        "**Process:**",
        "1. Gather project context (GitHub repo/owner required)",
        "2. Run Software Development workflow for PRD + Architecture",
        "3. Review output with user",
        "4. Run Implementation workflow when user is ready",
        "",
        "Delegate specialized tasks to team members as needed.",
    ],
    markdown=True,
    show_members_responses=True,
)
