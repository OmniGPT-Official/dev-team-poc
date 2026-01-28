"""
Product Team Configuration

This module defines the product development team with the Product Lead agent
as the team leader, coordinating delegation to specialized agents.
"""

from agno.team import Team
from agno.models.anthropic import Claude

from agents.product_lead import product_lead_agent
from agents.research_agent import research_agent
from agents.lead_engineer import lead_engineer_agent
from agents.software_engineer import software_engineer_agent


# Product Development Team - Product Lead coordinates the team
# The team includes Product Lead, Research, Lead Engineer, and Software Engineer
product_team = Team(
    name="Product Development Team",
    model=Claude(id="claude-sonnet-4-5"),
    members=[
        product_lead_agent,  # Product Lead coordinates and has workflow tools
        research_agent,
        lead_engineer_agent,
        software_engineer_agent,
    ],
    instructions=[
        "You are the Product Development Team.",
        "The Product Lead (member) orchestrates the software development workflow:",
        "  - Has access to Software Development workflow tool",
        "  - Creates PRDs and coordinates technical architecture",
        "  - Guides the team through product development",
        "The Research Agent handles market research and competitor analysis.",
        "The Lead Engineer Agent designs technical architecture and specifications.",
        "The Software Engineer Agent implements features and handles code reviews.",
        "Delegate tasks appropriately and work together to deliver complete solutions.",
    ],
    markdown=True,
    show_members_responses=True,
)
