"""
Agent OS Main Application

This is the main entry point for the Agent OS application.
It imports agents, teams, and workflows from their respective modules.
"""

from agno.os import AgentOS
from agents.product_lead import product_lead_agent
from agents.research_agent import research_agent
from agents.lead_engineer import lead_engineer_agent
from agents.software_engineer import software_engineer_agent
from workflows.code_review_workflow import code_review_workflow


# Initialize Agent OS
agent_os = AgentOS(
    name="Product Lead OS",
    agents=[product_lead_agent, research_agent, lead_engineer_agent, software_engineer_agent],
    workflows=[code_review_workflow],
    tracing=True
)

# Get FastAPI app
app = agent_os.get_app()


if __name__ == "__main__":
    agent_os.serve(app="agno_agent:app", reload=True)
