"""Shared pre-hook that injects per-user tools (OAuth + API keys + MCP) before each agent run."""

from agno.agent import Agent
from agno.tools.eleven_labs import ElevenLabsTools
from agno.tools.gmail import GmailTools
from agno.tools.googlesheets import GoogleSheetsTools
from agno.tools.mcp import MCPTools
from agno.tools.mcp.params import StreamableHTTPClientParams

from services.api_key_store import get_api_key, get_api_key_with_metadata
from services.oauth_store import get_google_credentials
from services.user_context import set_current_user_id
from tools.github_tools import GitHubTools
from tools.vercel_deploy_tools import VercelDeployTools
from tools.google_docs_tools import GoogleDocsTools


def inject_user_tools(agent: Agent, user_id: str) -> None:
    """Pre-hook: fetch per-user credentials (OAuth + API keys) and inject tools before each run."""
    print(f"[pre-hook] inject_user_tools called for {agent.name} — user_id={user_id!r}")
    if not user_id:
        print("[pre-hook] No user_id, skipping tool injection")
        return

    # Store user_id so workflow steps can read it
    set_current_user_id(user_id)

    tools = []

    # --- OAuth-based tools ---
    sheets_creds = get_google_credentials(user_id, "google_sheets")
    if sheets_creds:
        tools.append(
            GoogleSheetsTools(
                creds=sheets_creds,
                enable_read_sheet=True,
                enable_update_sheet=True,
                enable_create_sheet=True,
                enable_create_duplicate_sheet=False,
            )
        )

    gmail_creds = get_google_credentials(user_id, "google_gmail")
    if gmail_creds:
        tools.append(GmailTools(creds=gmail_creds))

    google_docs_creds = get_google_credentials(user_id, "google_sheets")
    if google_docs_creds:
        tools.append(GoogleDocsTools(creds=google_docs_creds))

    # --- API-key-based tools ---
    elevenlabs_key = get_api_key(user_id, "elevenlabs")
    if elevenlabs_key:
        tools.append(ElevenLabsTools(api_key=elevenlabs_key))

    github_token = get_api_key(user_id, "github")
    if github_token:
        print(f"[pre-hook] GitHub token found, creating GitHubTools with per-user token")
        tools.append(GitHubTools(token=github_token))
    else:
        print(f"[pre-hook] No GitHub token in DB for user_id={user_id!r} — agent will use env var fallback")

    vercel_token = get_api_key(user_id, "vercel")
    if vercel_token:
        print(f"[pre-hook] Vercel token found, creating VercelDeployTools with per-user token")
        tools.append(VercelDeployTools(token=vercel_token))
    else:
        print(f"[pre-hook] No Vercel token in DB for user_id={user_id!r} — agent will use env var fallback")

    # --- Supabase MCP tools ---
    supabase_data = get_api_key_with_metadata(user_id, "supabase")
    if supabase_data:
        project_ref = (supabase_data.get("metadata") or {}).get("project_ref")
        if project_ref:
            pat = supabase_data["api_key"]
            tools.append(
                MCPTools(
                    url=f"https://mcp.supabase.com/mcp?project_ref={project_ref}",
                    transport="streamable-http",
                    server_params=StreamableHTTPClientParams(
                        url=f"https://mcp.supabase.com/mcp?project_ref={project_ref}",
                        headers={"Authorization": f"Bearer {pat}"},
                    ),
                )
            )

    print(f"[pre-hook] Injecting {len(tools)} tool(s): {[type(t).__name__ for t in tools]}")
    agent.set_tools(tools)
