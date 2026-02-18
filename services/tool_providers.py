"""Registry of per-user tool providers.

Each provider is a callable registered under a short name (e.g. "google_sheets").
It receives a ``user_id`` and returns an Agno tool instance (or ``None`` when
credentials are missing).

To add a new provider, decorate a function with ``@register("name")``.
No other files need to change.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_PROVIDERS: Dict[str, Callable[[str], Optional[Any]]] = {}


def register(name: str):
    """Decorator that registers a tool-provider function under *name*."""

    def decorator(fn: Callable[[str], Optional[Any]]):
        _PROVIDERS[name] = fn
        return fn

    return decorator


def get_provider(name: str) -> Callable[[str], Optional[Any]]:
    """Return the provider registered under *name*, or raise ``KeyError``."""
    return _PROVIDERS[name]


def resolve_tools(user_id: str, *provider_names: str) -> list:
    """Build a list of tool instances for *user_id* from the given providers.

    Providers whose credentials are missing (return ``None``) are silently
    skipped.
    """
    tools: list = []
    for name in provider_names:
        provider_fn = _PROVIDERS.get(name)
        if provider_fn is None:
            print(f"[tool_providers] Unknown provider: {name!r}")
            continue
        tool = provider_fn(user_id)
        if tool is not None:
            tools.append(tool)
    return tools


# ---------------------------------------------------------------------------
# Built-in providers
# ---------------------------------------------------------------------------

@register("google_sheets")
def _google_sheets(user_id: str):
    import os
    from agno.tools.googlesheets import GoogleSheetsTools
    from services.oauth_store import get_google_credentials

    creds = get_google_credentials(user_id, "google_sheets")

    if not creds:
        print(f"[tool_providers] No google_sheets credentials found in Supabase for user_id={user_id!r}")
        # Fallback: use global env var credentials (set via get_google_token.py)
        refresh_token = os.getenv("GOOGLE_OAUTH_REFRESH_TOKEN")
        if refresh_token:
            from google.oauth2.credentials import Credentials
            print(f"[tool_providers] Using GOOGLE_OAUTH_REFRESH_TOKEN env var as fallback for google_sheets")
            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.getenv("GOOGLE_CLIENT_ID"),
                client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                scopes=["https://www.googleapis.com/auth/spreadsheets"],
            )
        else:
            print(f"[tool_providers] No GOOGLE_OAUTH_REFRESH_TOKEN env var either — google_sheets unavailable for user_id={user_id!r}")
            return None

    return GoogleSheetsTools(
        creds=creds,
        enable_read_sheet=True,
        enable_update_sheet=True,
        enable_create_sheet=True,
        enable_create_duplicate_sheet=False,
    )


@register("google_gmail")
def _google_gmail(user_id: str):
    from agno.tools.gmail import GmailTools
    from services.oauth_store import get_google_credentials

    creds = get_google_credentials(user_id, "google_gmail")
    if not creds:
        return None
    return GmailTools(creds=creds)


@register("elevenlabs")
def _elevenlabs(user_id: str):
    from agno.tools.eleven_labs import ElevenLabsTools
    from services.api_key_store import get_api_key

    key = get_api_key(user_id, "elevenlabs")
    if not key:
        return None
    return ElevenLabsTools(api_key=key)


@register("supabase_mcp")
def _supabase_mcp(user_id: str):
    from agno.tools.mcp import MCPTools
    from agno.tools.mcp.params import StreamableHTTPClientParams
    from services.api_key_store import get_api_key_with_metadata

    data = get_api_key_with_metadata(user_id, "supabase")
    if not data:
        return None
    project_ref = (data.get("metadata") or {}).get("project_ref")
    if not project_ref:
        return None
    pat = data["api_key"]
    url = f"https://mcp.supabase.com/mcp?project_ref={project_ref}"
    return MCPTools(
        url=url,
        transport="streamable-http",
        server_params=StreamableHTTPClientParams(
            url=url,
            headers={"Authorization": f"Bearer {pat}"},
        ),
    )


@register("github")
def _github(user_id: str):
    from tools.github_tools import GitHubTools
    from services.api_key_store import get_api_key

    token = get_api_key(user_id, "github")
    if not token:
        return None
    print(f"[tool_providers] GitHub token found for user {user_id!r}")
    return GitHubTools(token=token)


@register("vercel")
def _vercel(user_id: str):
    """Vercel project management tools (comprehensive GitHub integration)."""
    from tools.vercel_project_tools import VercelProjectTools
    from services.api_key_store import get_api_key

    token = get_api_key(user_id, "vercel")
    if not token:
        return None
    print(f"[tool_providers] Vercel token found for user {user_id!r}")
    return VercelProjectTools(token=token)


@register("vercel_deploy")
def _vercel_deploy(user_id: str):
    """Vercel one-time deployment tools (fallback for quick deployments)."""
    from tools.vercel_deploy_tools import VercelDeployTools
    from services.api_key_store import get_api_key

    token = get_api_key(user_id, "vercel")
    if not token:
        return None
    return VercelDeployTools(token=token)


@register("google_docs")
def _google_docs(user_id: str):
    from tools.google_docs_tools import GoogleDocsTools
    from services.oauth_store import get_google_credentials

    # Fetch Google Docs OAuth credentials (separate provider from google_sheets)
    creds = get_google_credentials(user_id, "google_docs")
    if not creds:
        return None
    return GoogleDocsTools(creds=creds)


@register("instagram")
def _instagram(user_id: str):
    from os import getenv
    from tools.instagram import InstagramTools, InstagramConnectTools
    from services.oauth_store import get_instagram_credentials

    ig_creds = get_instagram_credentials(user_id)
    if ig_creds:
        print(f"[tool_providers] Instagram credentials found for user {user_id!r}")
        return InstagramTools(
            access_token=ig_creds["access_token"],
            ig_user_id=ig_creds["ig_user_id"],
            supabase_url=getenv("SUPABASE_STORAGE_URL", ""),
            supabase_key=getenv("SUPABASE_STORAGE_KEY", ""),
        )

    # No credentials — offer a connect flow if Meta OAuth is configured
    from routes.oauth import generate_instagram_auth_url

    auth_url = generate_instagram_auth_url(user_id)
    if not auth_url:
        return None
    return InstagramConnectTools(auth_url=auth_url)


@register("job_boards")
def _job_boards(user_id: str):
    """Multi-platform job board tools — post to any registered board.

    Auto-discovers plugins from tools/job_boards/*.py.
    No credentials stored here — each plugin checks its own env vars.

    Currently installed boards:
      indeed_th  — Indeed Thailand (INDEED_EMAIL + GMAIL_APP_PASSWORD)

    To add a new board: create tools/job_boards/<board_id>.py with @register_board.
    No other files need to change.
    """
    from tools.generic_job_board_tools import GenericJobBoardTools

    print(f"[tool_providers] GenericJobBoardTools for user {user_id!r}")
    return GenericJobBoardTools(user_id=user_id)


@register("smart_browser")
def _smart_browser(user_id: str):
    """Browserbase managed browser with full page interaction.

    Provides: navigate_to, get_page_content, screenshot, close_session, execute_javascript
    Requires: BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID env vars in Railway.
    """
    import os
    api_key = os.getenv("BROWSERBASE_API_KEY", "")
    project_id = os.getenv("BROWSERBASE_PROJECT_ID", "")
    if not api_key or not project_id:
        print(f"[tool_providers] BROWSERBASE_API_KEY or BROWSERBASE_PROJECT_ID not set — smart_browser disabled")
        return None
    from tools.browserbase_tools import BrowserbaseInteractiveTools
    print(f"[tool_providers] BrowserbaseInteractiveTools for user {user_id!r}")
    return BrowserbaseInteractiveTools()


@register("job_feeds")
def _job_feeds(user_id: str):
    """Unified job feed tools — generates Indeed XML + LinkedIn XML from one store.

    No API keys required. Register each feed URL once with the platform.
    Env vars:
      APP_BASE_URL          - public URL of this app (e.g. https://your-app.railway.app)
      HR_POSTER_EMAIL       - email shown on LinkedIn job postings (required by LinkedIn)
      LINKEDIN_COMPANY_ID   - numeric LinkedIn Page ID (optional, improves LinkedIn matching)
    """
    import os
    from tools.job_feed_tools import get_feed_instance

    base_url = os.getenv("APP_BASE_URL", "")
    poster_email = os.getenv("HR_POSTER_EMAIL", "")
    linkedin_company_id = os.getenv("LINKEDIN_COMPANY_ID", "")

    print(f"[tool_providers] JobFeedTools for user {user_id!r} (base_url={base_url!r})")
    return get_feed_instance(
        base_url=base_url,
        poster_email=poster_email,
        linkedin_company_id=linkedin_company_id,
    )
