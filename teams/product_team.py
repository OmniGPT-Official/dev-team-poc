"""
Product Team Configuration

This module defines the product development team using Agno Team.
The Team's model acts as the Product Lead (team leader), coordinating
delegation to specialized agents for research, engineering, and implementation.
"""

from agno.team import Team
from agno.models.anthropic import Claude

from agents.research_agent import research_agent
from agents.lead_engineer import lead_engineer_agent
from agents.software_engineer import software_engineer_agent
from instructions.product_lead_instructions import PRODUCT_LEAD_INSTRUCTIONS


# Product Development Team - The Team itself is the Product Lead (leader)
# who coordinates and delegates to the specialized member agents
product_team = Team(
    name="Product Development Team",
    model=Claude(id="claude-sonnet-4-5"),
    members=[
        research_agent,
        lead_engineer_agent,
        software_engineer_agent,
    ],
    instructions=[
        PRODUCT_LEAD_INSTRUCTIONS,
        "As the Product Lead and team leader, coordinate the Product Development Team.",
        "Delegate research tasks (market analysis, competitor research, industry trends) to the Research Agent.",
        "Delegate technical architecture, specifications, and code review guidance to the Lead Engineer Agent.",
        "Delegate code implementation, bug fixes, testing, and documentation to the Software Engineer Agent.",
        "Synthesize results from team members into cohesive, actionable deliverables.",
    ],
    markdown=True,
    show_members_responses=True,
)
