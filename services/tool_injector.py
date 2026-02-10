"""Shared pre-hook that injects per-user tools (OAuth + API keys + MCP) before each agent run."""

from agno.agent import Agent
from agno.tools.eleven_labs import ElevenLabsTools
from agno.tools.gmail import GmailTools
from agno.tools.googlesheets import GoogleSheetsTools
from agno.tools.mcp import MCPTools
from agno.tools.mcp.params import StreamableHTTPClientParams

from services.api_key_store import get_api_key, get_api_key_with_metadata
from services.oauth_store import get_google_credentials


def inject_user_tools(agent: Agent, user_id: str) -> None:
    """Pre-hook: fetch per-user credentials (OAuth + API keys) and inject tools before each run."""
    print(f"[pre-hook] inject_user_tools called for {agent.name} — user_id={user_id!r}")
    if not user_id:
        print("[pre-hook] No user_id, skipping tool injection")
        return

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

    # --- API-key-based tools ---
    elevenlabs_key = get_api_key(user_id, "elevenlabs")
    if elevenlabs_key:
        tools.append(ElevenLabsTools(api_key=elevenlabs_key))

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
