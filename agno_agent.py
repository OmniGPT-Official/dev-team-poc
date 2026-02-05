"""
Agent OS Main Application

This is the main entry point for the Agent OS application.
Clean architecture with 4 agents, 1 team, and 2 workflows.
"""

import os
from os import getenv

from agno.os import AgentOS
from agno.os.middleware import JWTMiddleware
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
    authorization=False,  # Phase 1: no RBAC, just JWT user identification
    tracing=True
)

# Get FastAPI app
app = agent_os.get_app()

# JWT middleware for multi-user authentication
# Validates Supabase JWTs (ES256) and auto-injects user_id from the `sub` claim into agent/team runs
# To temporarily disable authentication, comment out the entire app.add_middleware(...) block below
# app.add_middleware(
#     JWTMiddleware,
#     jwks_file=getenv("JWT_JWKS_FILE", "supabase/jwks.json"),
#     algorithm="ES256",
#     user_id_claim="sub",
#     validate=True,
#     authorization=False,
#     excluded_route_paths=["/health", "/docs", "/redoc", "/openapi.json"],
# )

# ---------------------------------------------------------------------------
# Google OAuth Token Generator (Built-in)
# ---------------------------------------------------------------------------
import json
import secrets
import requests as http_requests
from urllib.parse import urlencode
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

# Google OAuth Config
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
PORT = int(os.getenv("PORT", 8000))
BASE_URL = os.getenv("OAUTH_BASE_URL", f"http://localhost:{PORT}")
REDIRECT_URI = f"{BASE_URL}/google-callback"

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]

AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"

# In-memory storage for OAuth state and tokens
oauth_state = {}
latest_token = {}


@app.get("/google-auth", response_class=HTMLResponse)
async def google_auth_home():
    """Google OAuth Token Generator home page."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return HTMLResponse("""<!DOCTYPE html>
<html><head><title>Configuration Error</title></head>
<body style="font-family:system-ui;background:#1a1a2e;color:#e74c3c;padding:40px;text-align:center;">
  <h1>Missing Google OAuth Credentials</h1>
  <p>Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.</p>
  <a href="https://console.cloud.google.com/apis/credentials" style="color:#4ecca3;">Google Cloud Console</a>
</body></html>""")

    has_token = bool(latest_token)
    token_section = ""
    if has_token:
        token_json = json.dumps(latest_token, separators=(',', ':'))
        token_section = f'''
        <div class="token-box">
            <h2>Your Token (copy this for GOOGLE_DOCS_TOKEN env var):</h2>
            <textarea id="token" readonly onclick="this.select()">{token_json}</textarea>
            <button onclick="copyToken()">Copy to Clipboard</button>
            <p class="success">Token generated successfully!</p>
        </div>
        <script>
            function copyToken() {{
                const textarea = document.getElementById('token');
                textarea.select();
                document.execCommand('copy');
                alert('Token copied to clipboard!');
            }}
            console.log('GOOGLE_DOCS_TOKEN:', {json.dumps(token_json)});
        </script>
        '''

    return f"""<!DOCTYPE html>
<html><head><title>Google OAuth Token Generator</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 50px auto; padding: 20px; background: #1a1a2e; color: #eee; }}
  .card {{ background: #16213e; padding: 32px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,.3); }}
  h1 {{ color: #4ecca3; margin-top: 0; }}
  h2 {{ color: #4ecca3; font-size: 1.1em; margin-bottom: 10px; }}
  .btn {{ display: inline-block; padding: 12px 28px; border-radius: 6px; text-decoration: none; color: #fff; font-weight: 600; margin: 8px 4px; border: none; cursor: pointer; font-size: 1em; }}
  .btn.primary {{ background: #4ecca3; color: #1a1a2e; }}
  .btn.primary:hover {{ background: #3db892; }}
  .info {{ background: #0f3460; padding: 16px; border-radius: 8px; margin: 20px 0; }}
  .info code {{ background: #1a1a2e; padding: 2px 8px; border-radius: 4px; }}
  .token-box {{ background: #0f3460; padding: 20px; border-radius: 8px; margin: 20px 0; }}
  .token-box textarea {{ width: 100%; height: 120px; background: #1a1a2e; color: #4ecca3; border: 1px solid #4ecca3; border-radius: 6px; padding: 12px; font-family: monospace; font-size: 12px; resize: vertical; }}
  .token-box button {{ background: #4ecca3; color: #1a1a2e; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: 600; margin-top: 10px; }}
  .token-box button:hover {{ background: #3db892; }}
  .success {{ color: #4ecca3; font-weight: 600; }}
  .warn {{ color: #f39c12; }}
</style></head>
<body><div class="card">
  <h1>Google OAuth Token Generator</h1>

  <div class="info">
    <p><strong>Redirect URI:</strong> <code>{REDIRECT_URI}</code></p>
    <p class="warn">Make sure this URI is added to your Google Cloud Console OAuth credentials!</p>
  </div>

  <a href="/google-auth/authorize" class="btn primary">Authorize with Google</a>

  {token_section}

  <div class="info" style="margin-top: 30px;">
    <h3>How to use:</h3>
    <ol>
      <li>Click "Authorize with Google"</li>
      <li>Sign in and grant permissions</li>
      <li>Copy the JSON token displayed</li>
      <li>Paste it as <code>GOOGLE_DOCS_TOKEN</code> in your env vars</li>
    </ol>
  </div>
</div></body></html>"""


@app.get("/google-auth/authorize")
async def google_auth_authorize():
    """Initiate Google OAuth flow."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return JSONResponse({"error": "Google OAuth credentials not configured"}, status_code=503)

    state = secrets.token_urlsafe(32)
    oauth_state["current"] = state

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }

    url = f"{AUTH_URI}?{urlencode(params)}"
    print(f"\n-> Redirecting to Google OAuth ({state[:12]}...)")
    return RedirectResponse(url)


@app.get("/google-callback")
async def google_callback(code: str = None, state: str = None, error: str = None):
    """Handle Google OAuth callback - returns JSON token."""
    global latest_token

    if error:
        return JSONResponse({"error": error, "message": "Authorization failed"}, status_code=400)

    if state != oauth_state.get("current"):
        return JSONResponse({"error": "invalid_state", "message": "CSRF check failed"}, status_code=400)

    if not code:
        return JSONResponse({"error": "no_code", "message": "No authorization code received"}, status_code=400)

    print(f"\n-> Callback received, exchanging code...")

    # Exchange code for tokens
    resp = http_requests.post(TOKEN_URI, data={
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    })

    if resp.status_code != 200:
        return JSONResponse({
            "error": "token_exchange_failed",
            "message": "Failed to exchange authorization code for tokens",
            "details": resp.text
        }, status_code=500)

    tokens = resp.json()

    # Build the token object
    latest_token = {
        "token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token"),
        "token_uri": TOKEN_URI,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "scopes": SCOPES,
    }

    token_json = json.dumps(latest_token, separators=(',', ':'))

    print(f"\n{'='*60}")
    print("TOKEN GENERATED - Copy this for GOOGLE_DOCS_TOKEN:")
    print(f"{'='*60}")
    print(token_json)
    print(f"{'='*60}\n")

    return JSONResponse(latest_token)


@app.get("/google-auth/token")
async def get_google_token():
    """Return the latest token as JSON (for API access)."""
    if not latest_token:
        return JSONResponse({"error": "No token generated yet. Visit /google-auth first."}, status_code=404)
    return JSONResponse(latest_token)


@app.get("/google-auth/token-raw")
async def get_google_token_raw():
    """Return the latest token as plain text JSON (easy to copy)."""
    from fastapi.responses import PlainTextResponse

    if not latest_token:
        return PlainTextResponse("No token generated yet. Visit /google-auth first.", status_code=404)

    token_json = json.dumps(latest_token, separators=(',', ':'))
    return PlainTextResponse(token_json, media_type="text/plain")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        app="agno_agent:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
