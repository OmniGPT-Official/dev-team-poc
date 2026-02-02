"""
Agent OS Main Application

This is the main entry point for the Agent OS application.
Clean architecture with 4 agents, 1 team, and 2 workflows.
"""

import os
from agno.os import AgentOS
from agents.product_lead import product_lead_agent, add_workflow_tools
from agents.lead_engineer import lead_engineer_agent
from agents.software_engineer import software_engineer_agent
from agents.security_engineer import security_engineer_agent
from teams.product_team import product_team
from workflows.product_requirements_workflow import product_requirements_workflow
from workflows.software_development_workflow import software_development_workflow

# Add workflow tools to product lead agent (after all imports to avoid circular dependency)
add_workflow_tools()

# Initialize Agent OS
agent_os = AgentOS(
    name="Agent OS",
    agents=[
        product_lead_agent,
        lead_engineer_agent,
        software_engineer_agent,
        security_engineer_agent,
    ],
    teams=[
        product_team,
    ],
    workflows=[
        product_requirements_workflow,
        software_development_workflow,
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
        reload=False
    )
