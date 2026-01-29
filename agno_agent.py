"""
Agent OS Main Application

This is the main entry point for the Agent OS application.
It imports agents, teams, and workflows from their respective modules.
"""

import os
from agno.os import AgentOS
from agents.product_lead import product_lead_agent, add_workflow_tools
from agents.research_agent import research_agent
from agents.lead_engineer import lead_engineer_agent
from agents.software_engineer import software_engineer_agent
from teams.product_team import product_team
from workflows.product_discovery_workflow import discovery_and_requirements_workflow
from workflows.architecture_design_workflow import architecture_design_workflow
from workflows.software_development_workflow import software_development_workflow

# Add workflow tools to product lead agent (after all imports to avoid circular dependency)
add_workflow_tools()

# Initialize Agent OS
agent_os = AgentOS(
    name="Agent OS",
    agents=[
        product_lead_agent,  # Main orchestrator - has Software Development workflow as tool
        research_agent,
        lead_engineer_agent,
        software_engineer_agent
    ],
    teams=[
        product_team,  # Product Development Team with Product Lead as leader
    ],
    workflows=[
        software_development_workflow,  # Main workflow (orchestrates Product Discovery + Architecture Design + Implementation Cycle)
        architecture_design_workflow,
        discovery_and_requirements_workflow,
    ],
    tracing=True
)

# Get FastAPI app
app = agent_os.get_app()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        app="agno_agent:app",
        host="0.0.0.0",
        port=port,
        reload=False  # Set to False for production
    )
