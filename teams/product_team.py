"""
Product Team Configuration

This module defines teams of agents working together.
Teams can include multiple agents with different specializations.
"""

from agents.product_lead import product_lead_agent
from agents.research_agent import research_agent


# Product team with all agents
product_team = [
    product_lead_agent,
    research_agent,
    # Add more agents here as needed:
    # designer_agent,
    # analyst_agent,
    # engineer_agent,
]
