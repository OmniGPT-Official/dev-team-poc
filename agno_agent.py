"""
Agent OS Main Application

This is the main entry point for the Agent OS application.
It imports agents, teams, and workflows from their respective modules.
"""

from agno.os import AgentOS
from agents.product_lead import product_lead_agent
from agents.research_agent import research_agent


# Initialize Agent OS
agent_os = AgentOS(
    name="Product Lead OS",
    agents=[product_lead_agent, research_agent],
    tracing=True
)

# Get FastAPI app
app = agent_os.get_app()


if __name__ == "__main__":
    agent_os.serve(app="agno_agent:app", reload=True)
