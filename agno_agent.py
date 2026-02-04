"""
Agent OS Main Application

This is the main entry point for the Agent OS application.
Clean architecture with 4 agents, 1 team, and 2 workflows.
"""

import os
from agno.os import AgentOS
from agents.product_lead import product_lead_agent
from agents.lead_engineer import lead_engineer_agent
from agents.software_engineer import software_engineer_agent
from agents.security_engineer import security_engineer_agent
from teams.product_team import product_team
from workflows.product_requirements_workflow import product_requirements_workflow
from workflows.software_development_workflow import software_development_workflow
from workflows.sales_followup_workflow import sales_followup_workflow, simple_followup_workflow
from agents.sales_followup_agents import followup_coordinator_agent
from content_creation import (
    content_strategist,
    content_writer,
    image_generator,
    content_creation_team,
    requirement_gathering_workflow_definition,
)

# Initialize Agent OS
agent_os = AgentOS(
    name="Agent OS",
    agents=[
        product_lead_agent,
        lead_engineer_agent,
        software_engineer_agent,
        security_engineer_agent,
        followup_coordinator_agent,  # Sales Follow-Up Manager
        content_strategist,  # Content Creation Team
        content_writer,  # Content Creation Team
        image_generator,  # Content Creation Team
    ],
    teams=[
        product_team,  # Product Development Team
        content_creation_team,  # Content Creation Team
    ],
    workflows=[
        product_requirements_workflow,
        software_development_workflow,
        sales_followup_workflow,  # Sales Follow-Up Manager (full version)
        simple_followup_workflow,  # Sales Follow-Up Manager (simple testing version)
        requirement_gathering_workflow_definition,  # Content Creation Workflow
    ],
    tracing=True
)

# Get FastAPI app
app = agent_os.get_app()

# ---------------------------------------------------------------------------
# Google Auth Service Integration
# ---------------------------------------------------------------------------
GOOGLE_AUTH_SERVICE_URL = os.getenv("GOOGLE_AUTH_SERVICE_URL")


@app.get("/google-auth")
async def google_auth_redirect():
    """Redirect to Google Auth Token Generator service."""
    from fastapi.responses import RedirectResponse, JSONResponse

    if not GOOGLE_AUTH_SERVICE_URL:
        return JSONResponse(
            {
                "error": "GOOGLE_AUTH_SERVICE_URL not configured",
                "message": "Set GOOGLE_AUTH_SERVICE_URL env var to your deployed google-auth-token service",
                "repo": "https://github.com/OmniGPT-Official/google-auth-token"
            },
            status_code=503
        )
    return RedirectResponse(GOOGLE_AUTH_SERVICE_URL)


@app.get("/google-auth/info")
async def google_auth_info():
    """Get Google Auth service configuration info."""
    from fastapi.responses import JSONResponse

    return JSONResponse({
        "service_url": GOOGLE_AUTH_SERVICE_URL,
        "configured": bool(GOOGLE_AUTH_SERVICE_URL),
        "repo": "https://github.com/OmniGPT-Official/google-auth-token",
        "endpoints": {
            "authorize": f"{GOOGLE_AUTH_SERVICE_URL}/authorize" if GOOGLE_AUTH_SERVICE_URL else None,
            "token": f"{GOOGLE_AUTH_SERVICE_URL}/token" if GOOGLE_AUTH_SERVICE_URL else None,
            "health": f"{GOOGLE_AUTH_SERVICE_URL}/health" if GOOGLE_AUTH_SERVICE_URL else None,
        }
    })


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        app="agno_agent:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
