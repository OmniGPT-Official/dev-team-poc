"""
Agent OS Main Application

This is the main entry point for the Agent OS application.
Clean architecture with multiple specialized agents, teams, and workflows.
"""

import os
from agno.os import AgentOS
from agno.os.interfaces.slack import Slack
from agents.product_lead import product_lead_agent
from agents.lead_engineer import lead_engineer_agent
from agents.software_engineer import software_engineer_agent
from agents.security_engineer import security_engineer_agent
from agents.devops_engineer import devops_engineer_agent
from agents.database_engineer import database_engineer_agent
from agents.credentials_manager import credentials_manager_agent
from teams.product_team import product_team
from workflows.product_requirements_workflow import product_requirements_workflow
from workflows.software_development_workflow import software_development_workflow
from content_creation import (
    content_strategist,
    content_writer,
    content_creation_team,
)
from email_followup import email_followup_agent
from gmail_sheets_agent import gmail_sheets_agent
from supabase_manager import supabase_manager_agent
from workflows.email_followup_workflow_working import email_followup_workflow
from workflows.outbound_calling_workflow import outbound_calling_workflow, simple_calling_workflow
from workflows.outbound_calling_test_workflow import outbound_calling_test_workflow
from agents.calling_agents import (
    lead_reader_agent,
    calling_coordinator_agent,
    results_logger_agent,
    campaign_coordinator_agent
)
from campaign_manager import campaign_manager  # Pattern 1: Single Agent + Workflow

# Initialize Agent OS with Enhanced Tracing
# Tracing provides visibility into:
# - Every agent run and interaction
# - Model calls and token usage
# - Tool executions and results
# - Workflow step progression
# - Error tracking and debugging
#
# Traces are stored in the shared SQLite database (agno.db)
# For production, consider using a dedicated PostgreSQL database
# Learn more: https://docs.agno.com/agent-os/tracing/overview
agent_os = AgentOS(
    name="Agent OS",
    interfaces=[
        Slack(agent=software_engineer_agent),
    ],
    agents=[
        credentials_manager_agent,  # Credentials Manager (validates tokens before workflows)
        product_lead_agent,
        lead_engineer_agent,
        software_engineer_agent,
        security_engineer_agent,
        devops_engineer_agent,  # DevOps Engineer (repo creation + Vercel deployment)
        database_engineer_agent,  # Database Engineer (schema design + Supabase operations)
        content_strategist,  # Content Creation Team
        content_writer,  # Content Creation Team
        email_followup_agent,  # Email Follow-Up Agent (OAuth-enabled)
        gmail_sheets_agent,  # Gmail & Sheets Agent (OAuth-enabled, Claude)
        supabase_manager_agent,  # Supabase Manager (MCP-enabled)
        lead_reader_agent,  # Outbound Calling: Lead Reader
        calling_coordinator_agent,  # Outbound Calling: Calling Coordinator
        results_logger_agent,  # Outbound Calling: Results Logger
        campaign_coordinator_agent,  # Outbound Calling: Campaign Coordinator
        campaign_manager,  # Campaign Manager (Pattern 1: Single Agent + Internal Workflow)
    ],
    teams=[
        product_team,  # Product Development Team
        content_creation_team,  # Content Creation Team
    ],
    workflows=[
        product_requirements_workflow,
        software_development_workflow,
        email_followup_workflow,  # Email Follow-Up Manager (3-step, OAuth-enabled) ✅
        outbound_calling_workflow,  # Outbound Calling Campaign (full with ElevenLabs)
        simple_calling_workflow,  # Outbound Calling Campaign (simple test version)
        outbound_calling_test_workflow,  # Outbound Calling Test (OAuth, first iteration)
    ],
    tracing=True,  # Enable built-in OpenTelemetry tracing
)

# Get FastAPI app
app = agent_os.get_app()

# ---------------------------------------------------------------------------
# CORS Configuration - Allow frontend to access the API
# ---------------------------------------------------------------------------
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://os.agno.com",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Startup Check - Test Database Connection & Token Fetching
# ---------------------------------------------------------------------------
import logging
import sys

logger = logging.getLogger("uvicorn.error")

@app.on_event("startup")
async def startup_check():
    """Run startup checks to verify database and credential fetching."""
    msg = "\n" + "="*80 + "\n🚀 AGENT-OS STARTUP - CREDENTIAL SYSTEM CHECK\n" + "="*80
    logger.info(msg)
    print(msg, flush=True)

    # Test Supabase connection
    try:
        from services.oauth_store import get_supabase_client
        client = get_supabase_client()
        msg = "✅ Supabase client initialized successfully"
        logger.info(msg)
        print(msg, flush=True)
    except Exception as e:
        msg = f"❌ Supabase client initialization FAILED: {e}"
        logger.error(msg)
        print(msg, flush=True)
        return

    # Test API key fetching with a dummy user_id
    test_user_id = "test-user-startup-check"
    msg = f"\n📋 Testing API key retrieval (user_id='{test_user_id}')..."
    logger.info(msg)
    print(msg, flush=True)

    try:
        from services.api_key_store import get_api_key

        # Try fetching GitHub token
        github_token = get_api_key(test_user_id, "github")
        if github_token:
            msg = "   ✅ GitHub token fetch successful (test data exists)"
        else:
            msg = "   ℹ️  No GitHub token for test user (this is normal - add real user tokens to DB)"
        logger.info(msg)
        print(msg, flush=True)

        # Try fetching Vercel token
        vercel_token = get_api_key(test_user_id, "vercel")
        if vercel_token:
            msg = "   ✅ Vercel token fetch successful (test data exists)"
        else:
            msg = "   ℹ️  No Vercel token for test user"
        logger.info(msg)
        print(msg, flush=True)

    except Exception as e:
        msg1 = f"   ❌ API key fetch FAILED: {e}"
        msg2 = "   ⚠️  Check that 'user_api_keys' table exists in Supabase"
        logger.error(msg1)
        logger.warning(msg2)
        print(msg1, flush=True)
        print(msg2, flush=True)

    # Test OAuth credentials fetching
    msg = "\n📋 Testing OAuth credentials retrieval..."
    logger.info(msg)
    print(msg, flush=True)

    try:
        from services.oauth_store import get_google_credentials

        google_docs_creds = get_google_credentials(test_user_id, "google_sheets")
        if google_docs_creds:
            msg = "   ✅ Google Docs OAuth fetch successful (test data exists)"
        else:
            msg = "   ℹ️  No Google Docs OAuth for test user (this is normal)"
        logger.info(msg)
        print(msg, flush=True)

    except Exception as e:
        msg1 = f"   ❌ OAuth fetch FAILED: {e}"
        msg2 = "   ⚠️  Check that 'user_oauth_connections' table exists in Supabase"
        logger.error(msg1)
        logger.warning(msg2)
        print(msg1, flush=True)
        print(msg2, flush=True)

    summary = "\n" + "="*80 + "\n💡 To add real user tokens, run SQL in Supabase:\n" + \
              "   INSERT INTO user_api_keys (user_id, provider, api_key)\n" + \
              "   VALUES ('your-user-id', 'github', 'ghp_your_token');\n" + \
              "="*80 + "\n"
    logger.info(summary)
    print(summary, flush=True)

# ---------------------------------------------------------------------------
# Supabase JWT Middleware - Extract user_id for per-user sessions and pre-hooks
# ---------------------------------------------------------------------------
import jwt as pyjwt
from starlette.middleware.base import BaseHTTPMiddleware


class SupabaseUserMiddleware(BaseHTTPMiddleware):
    """Extract user_id from Supabase JWT and set on request.state.

    Checks X-Supabase-Token header first (for Agno UI custom headers),
    then falls back to Authorization: Bearer header (for frontend).

    Also sets the global user context for workflows and tools.
    """

    async def dispatch(self, request, call_next):
        from services.user_context import set_current_user_id
        from services.oauth_store import get_supabase_client

        # Extract JWT token
        token = request.headers.get("X-Supabase-Token", "")
        if not token:
            auth = request.headers.get("Authorization", "")
            if auth.lower().startswith("bearer "):
                token = auth[7:].strip()

        # Decode JWT and extract user_id
        user_id = None
        if token:
            try:
                payload = pyjwt.decode(token, options={"verify_signature": False})
                extracted_sub = payload.get("sub")

                if extracted_sub:
                    # Check if it's an email (contains @) - need to look up UUID
                    if "@" in extracted_sub:
                        print(f"[middleware] JWT contains email: {extracted_sub}, looking up UUID...")
                        try:
                            supabase = get_supabase_client()
                            result = supabase.table("user_oauth_connections").select("user_id").eq("provider_account_id", extracted_sub).limit(1).execute()

                            if result.data and len(result.data) > 0:
                                user_id = result.data[0]["user_id"]
                                print(f"[middleware] Found UUID for {extracted_sub}: {user_id}")
                            else:
                                print(f"[middleware] No user found for email {extracted_sub}")
                                user_id = None
                        except Exception as e:
                            print(f"[middleware] Failed to lookup user UUID: {e}")
                            user_id = None
                    else:
                        # Already a UUID
                        user_id = extracted_sub
                        print(f"[middleware] Extracted UUID from JWT: {user_id}")

                    if user_id:
                        request.state.user_id = user_id
                        set_current_user_id(user_id)
                else:
                    print(f"[middleware] JWT decoded but no 'sub' field found")
            except Exception as e:
                print(f"[middleware] JWT decode failed: {e}")
        else:
            print(f"[middleware] No JWT token found in request")

        # No cleanup needed - contextvars automatically isolate each request
        response = await call_next(request)
        return response


app.add_middleware(SupabaseUserMiddleware)

# ---------------------------------------------------------------------------
# Health Check Endpoint
# ---------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    """Health check endpoint for Railway and monitoring."""
    return {"status": "healthy", "service": "agent-os"}


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
