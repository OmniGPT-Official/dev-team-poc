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
    from agno.tools.googlesheets import GoogleSheetsTools
    from services.oauth_store import get_google_credentials

    creds = get_google_credentials(user_id, "google_sheets")
    if not creds:
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
