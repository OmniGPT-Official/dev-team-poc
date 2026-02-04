#!/usr/bin/env python3
"""
Google Docs OAuth2 Server

FastAPI server that handles the full OAuth2 flow:
  1. /authorize        -> Redirects to Google login
  2. /google-callback  -> Exchanges code for access + refresh tokens
  3. /test             -> Creates, reads, and updates a Google Doc

Tokens are persisted to tests/google_docs/token.json for reuse.

Run:
    cd <project-root>
    source venv/bin/activate
    pip install -r requirements.txt
    python tests/google_docs/oauth_server.py

    Then open http://localhost:8000
"""

import os
import json
import secrets
import requests as http_requests
import uvicorn
from pathlib import Path
from datetime import datetime
from urllib.parse import urlencode
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ---------------------------------------------------------------------------
# Configuration - Set these in your .env file or environment variables
# ---------------------------------------------------------------------------
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError(
        "Missing Google OAuth credentials. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
    )
REDIRECT_URI = "http://localhost:8000/google-callback"

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]

AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"

# Token is stored alongside this file so it's easy to find and .gitignore
TOKEN_DIR = Path(__file__).resolve().parent
TOKEN_FILE = TOKEN_DIR / "token.json"

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Google Docs OAuth2 Server")
oauth_state: dict = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def save_token(token_data: dict) -> None:
    """Persist token to disk."""
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)
    print(f"   Token saved -> {TOKEN_FILE}")


def load_credentials() -> Credentials:
    """Load credentials from token.json and refresh if needed."""
    if not TOKEN_FILE.exists():
        raise FileNotFoundError(
            f"Token file not found: {TOKEN_FILE}\n"
            "Visit http://localhost:8000/authorize to create one."
        )

    with open(TOKEN_FILE) as f:
        data = json.load(f)

    creds = Credentials(
        token=data["token"],
        refresh_token=data.get("refresh_token"),
        token_uri=TOKEN_URI,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=SCOPES,
    )

    # Auto-refresh if expired
    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request as GoogleRequest

        print("   Token expired - refreshing...")
        creds.refresh(GoogleRequest())
        save_token({
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": TOKEN_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scopes": SCOPES,
        })
        print("   Token refreshed")

    return creds


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def home():
    token_exists = TOKEN_FILE.exists()
    status_html = (
        '<div class="status success">Token found - <a href="/test">Run Test</a></div>'
        if token_exists
        else '<div class="status warn">No token yet - authorize first</div>'
    )

    return f"""<!DOCTYPE html>
<html><head><title>Google Docs OAuth2</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 700px; margin: 50px auto; padding: 20px; background: #f5f5f5; }}
  .card {{ background: #fff; padding: 32px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
  h1 {{ color: #1a73e8; margin-top: 0; }}
  .btn {{ display: inline-block; padding: 10px 22px; border-radius: 5px; text-decoration: none; color: #fff; font-weight: 500; margin: 6px 4px; }}
  .btn.primary {{ background: #1a73e8; }}
  .btn.green {{ background: #34a853; }}
  .status {{ padding: 12px; border-radius: 5px; margin: 16px 0; }}
  .status.success {{ background: #e6f4ea; color: #137333; border-left: 4px solid #34a853; }}
  .status.warn {{ background: #fef7e0; color: #8a6d3b; border-left: 4px solid #f9ab00; }}
  pre {{ background: #f8f9fa; padding: 12px; border-radius: 5px; font-size: 13px; overflow-x: auto; }}
</style></head>
<body><div class="card">
  <h1>Google Docs OAuth2 Test</h1>
  {status_html}
  <p>Redirect URI: <code>{REDIRECT_URI}</code></p>
  <a href="/authorize" class="btn primary">Authorize with Google</a>
  <a href="/test" class="btn green">Run Test</a>
  <a href="/status" class="btn primary">Token Status</a>
  <h3>Endpoints</h3>
  <pre>GET /              Home (this page)
GET /authorize     Start OAuth2 flow
GET /google-callback   Callback (automatic)
GET /test          Create, read, update a Google Doc
GET /status        Token status
GET /token         Token info (JSON)</pre>
</div></body></html>"""


@app.get("/authorize")
async def authorize():
    state = secrets.token_urlsafe(32)
    oauth_state["current"] = state

    params = {
        "client_id": CLIENT_ID,
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
    """Exchange authorization code for tokens and persist them."""

    if error:
        return HTMLResponse(f"<h2>Authorization error: {error}</h2><a href='/'>Home</a>")

    if state != oauth_state.get("current"):
        return HTMLResponse("<h2>Invalid state (CSRF check failed)</h2><a href='/'>Home</a>")

    if not code:
        return HTMLResponse("<h2>No authorization code received</h2><a href='/'>Home</a>")

    print(f"\n-> Callback received, exchanging code...")

    # Exchange code for tokens
    resp = http_requests.post(TOKEN_URI, data={
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    })

    if resp.status_code != 200:
        return HTMLResponse(
            f"<h2>Token exchange failed ({resp.status_code})</h2>"
            f"<pre>{resp.text}</pre><a href='/'>Home</a>"
        )

    tokens = resp.json()
    print(f"   Access token:  {tokens['access_token'][:24]}...")
    print(f"   Refresh token: {str(tokens.get('refresh_token', ''))[:24]}...")

    save_token({
        "token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token"),
        "token_uri": TOKEN_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scopes": SCOPES,
    })

    return RedirectResponse("/test")


@app.get("/status")
async def status():
    if not TOKEN_FILE.exists():
        return HTMLResponse(
            "<h2>No token found</h2>"
            "<a href='/authorize'>Authorize now</a>"
        )
    with open(TOKEN_FILE) as f:
        data = json.load(f)
    return HTMLResponse(
        f"<h2>Token Status</h2>"
        f"<p>Access token: <code>{data['token'][:30]}...</code></p>"
        f"<p>Refresh token: <code>{'present' if data.get('refresh_token') else 'missing'}</code></p>"
        f"<p>File: <code>{TOKEN_FILE}</code></p>"
        f"<a href='/test'>Run Test</a> | <a href='/'>Home</a>"
    )


@app.get("/token")
async def token_json():
    if not TOKEN_FILE.exists():
        return JSONResponse({"error": "No token"}, status_code=404)
    with open(TOKEN_FILE) as f:
        data = json.load(f)
    return JSONResponse({
        "token": data["token"][:30] + "...",
        "has_refresh_token": data.get("refresh_token") is not None,
        "file": str(TOKEN_FILE),
    })


@app.get("/test", response_class=HTMLResponse)
async def run_test():
    """Create -> Read -> Update -> Read a Google Doc and show results."""
    out: list[str] = []

    def log(msg: str):
        out.append(msg)
        print(msg)

    try:
        log("Loading credentials...")
        creds = load_credentials()
        service = build("docs", "v1", credentials=creds)

        # -- CREATE --------------------------------------------------------
        title = f"OAuth2 Test - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        log(f"\n[1] Creating document: {title}")
        doc = service.documents().create(body={"title": title}).execute()
        doc_id = doc["documentId"]
        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        log(f"    ID:  {doc_id}")
        log(f"    URL: {doc_url}")

        # -- READ (empty) --------------------------------------------------
        log("\n[2] Reading empty document")
        doc = service.documents().get(documentId=doc_id).execute()
        log(f"    Title: {doc['title']}  (content is empty)")

        # -- UPDATE ---------------------------------------------------------
        log("\n[3] Inserting content")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = (
            f"Google Docs API Test\n\n"
            f"Created: {ts}\n\n"
            f"This document was created through the FastAPI OAuth2 callback flow.\n\n"
            f"Features tested:\n"
            f"  - OAuth2 web flow with callback\n"
            f"  - Token exchange and storage\n"
            f"  - Document creation\n"
            f"  - Content insertion\n"
            f"  - Document reading\n\n"
            f"Status: All tests passed!\n"
        )
        service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": [{"insertText": {"location": {"index": 1}, "text": text}}]},
        ).execute()
        log(f"    Inserted {len(text)} characters")

        # -- READ (final) ---------------------------------------------------
        log("\n[4] Reading final document")
        final = service.documents().get(documentId=doc_id).execute()
        content = ""
        for el in final.get("body", {}).get("content", []):
            if "paragraph" in el:
                for run in el["paragraph"].get("elements", []):
                    if "textRun" in run:
                        content += run["textRun"].get("content", "")

        log("-" * 60)
        log(content.strip())
        log("-" * 60)

        log("\nAll tests passed!")

        # -- HTML output ----------------------------------------------------
        escaped = "\n".join(out).replace("&", "&amp;").replace("<", "&lt;")
        return f"""<!DOCTYPE html>
<html><head><title>Test Results</title>
<style>
  body {{ font-family: 'Monaco', monospace; background: #1e1e1e; color: #d4d4d4; padding: 20px; }}
  .box {{ max-width: 900px; margin: 0 auto; background: #252526; padding: 28px; border-radius: 10px; }}
  h1 {{ color: #4ec9b0; font-family: system-ui; }}
  pre {{ white-space: pre-wrap; line-height: 1.6; }}
  .btn {{ display: inline-block; margin-top: 16px; padding: 10px 20px; background: #0e639c; color: #fff; text-decoration: none; border-radius: 5px; }}
</style></head>
<body><div class="box">
  <h1>Test Passed</h1>
  <pre>{escaped}</pre>
  <a class="btn" href="{doc_url}" target="_blank">Open Document</a>
  <a class="btn" href="/">Home</a>
</div></body></html>"""

    except Exception as exc:
        import traceback

        out.append(f"\nERROR: {exc}")
        out.append(traceback.format_exc())
        escaped = "\n".join(out).replace("&", "&amp;").replace("<", "&lt;")
        return f"""<!DOCTYPE html>
<html><head><title>Test Failed</title></head>
<body style="font-family:monospace;background:#1e1e1e;color:#f48771;padding:20px;">
  <h1>Test Failed</h1><pre>{escaped}</pre>
  <a href="/" style="color:#4ec9b0;">Home</a>
</body></html>"""


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("  Google Docs OAuth2 Server")
    print("=" * 70)
    print(f"  Client ID:    {CLIENT_ID[:30]}...")
    print(f"  Redirect URI: {REDIRECT_URI}")
    print(f"  Token file:   {TOKEN_FILE}")
    print(f"  Server:       http://localhost:8000")
    print("=" * 70)
    print()
    print("  1. Open  http://localhost:8000")
    print("  2. Click 'Authorize with Google'")
    print("  3. Log in and grant permissions")
    print("  4. Test runs automatically")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8000)
