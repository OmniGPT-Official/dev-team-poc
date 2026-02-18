"""Hook factory for per-user tool injection.

Usage::

    from services.tool_injector import make_tool_hook

    agent = Agent(
        ...
        pre_hooks=[make_tool_hook("google_sheets", "google_gmail")],
    )

Each agent declares only the providers it needs.  Static tools defined at
agent init time are preserved across runs.
"""

from __future__ import annotations

import re

from agno.agent import Agent

from services.tool_providers import resolve_tools

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# In-memory cache: slack_id → user_uuid (persists for process lifetime)
_slack_id_cache: dict[str, str | None] = {}


def _resolve_user_id(raw_id: str) -> str | None:
    """Return a UUID user_id for *raw_id*.

    Resolution order:
      1. Already a UUID → return as-is
      2. Looks like an email → look up via Supabase auth admin
      3. Otherwise → treat as Slack user ID, look up from user_oauth_connections
    Results are cached in-memory after the first DB hit.
    """
    if _UUID_RE.match(raw_id):
        return raw_id

    # Check cache first
    if raw_id in _slack_id_cache:
        cached = _slack_id_cache[raw_id]
        if cached:
            print(f"[pre-hook] {raw_id!r} → cached UUID {cached!r}")
        return cached

    # Email lookup via Supabase auth admin
    if "@" in raw_id:
        print(f"[pre-hook] {raw_id!r} looks like email, looking up UUID via auth admin...")
        try:
            from services.oauth_store import get_supabase_client
            response = get_supabase_client().auth.admin.get_user_by_email(raw_id)
            if response and response.user:
                uuid = response.user.id
                _slack_id_cache[raw_id] = uuid
                print(f"[pre-hook] Resolved email {raw_id!r} → {uuid!r} (cached)")
                return uuid
        except Exception as e:
            print(f"[pre-hook] email lookup failed: {e}")
        _slack_id_cache[raw_id] = None
        print(f"[pre-hook] No user found for email {raw_id!r}, skipping tool injection")
        return None

    # Slack ID lookup
    print(f"[pre-hook] {raw_id!r} is not a UUID, looking up via slack_id...")
    try:
        from services.oauth_store import get_supabase_client

        result = (
            get_supabase_client()
            .table("user_oauth_connections")
            .select("user_id")
            .eq("slack_id", raw_id)
            .limit(1)
            .execute()
        )
        if result.data:
            uuid = result.data[0]["user_id"]
            _slack_id_cache[raw_id] = uuid
            print(f"[pre-hook] Resolved slack_id {raw_id!r} → {uuid!r} (cached)")
            return uuid
        else:
            _slack_id_cache[raw_id] = None
            print(f"[pre-hook] No user found for slack_id {raw_id!r}, skipping tool injection")
            return None
    except Exception as e:
        print(f"[pre-hook] slack_id lookup failed: {e}")
        return None


def make_tool_hook(*provider_names: str):
    """Return a pre-hook that injects only the requested providers.

    Static tools (those already on the agent before the first hook run) are
    snapshotted and prepended on every subsequent run so they are never lost.
    """

    def _hook(agent: Agent, user_id: str) -> None:
        print(f"[pre-hook] make_tool_hook({provider_names}) called for {agent.name} — user_id={user_id!r}")
        if not user_id:
            print(f"[pre-hook] WARNING: No user_id for {agent.name} — tools cannot be injected. "
                  f"Ensure user_id is passed when running agents/workflows.")
            return

        # Resolve Slack IDs to UUIDs (cached after first lookup)
        user_id = _resolve_user_id(user_id)
        if not user_id:
            return

        # Resolve Slack IDs to UUIDs (cached after first lookup)
        user_id = _resolve_user_id(user_id)
        if not user_id:
            return

        # Snapshot static tools on first invocation.
        # TODO(production): This monkey-patches _static_tools onto the Agent instance.
        # For production, move the snapshot into the closure (nonlocal) or use a more
        # unique attribute name (e.g. _omnigpt_static_tools) to avoid potential
        # collisions with future Agno internals.
        if not hasattr(agent, "_static_tools"):
            agent._static_tools = list(agent.tools or [])

        user_tools = resolve_tools(user_id, *provider_names)
        combined = agent._static_tools + user_tools

        print(f"[pre-hook] Injecting {len(user_tools)} user tool(s): {[type(t).__name__ for t in user_tools]} "
              f"(+ {len(agent._static_tools)} static)")
        agent.set_tools(combined)

    return _hook


# Backward-compat shim — injects ALL known providers (previous behavior).
inject_user_tools = make_tool_hook(
    "google_sheets",
    "google_gmail",
    "google_docs",
    "elevenlabs",
    "github",
    "vercel",  # Comprehensive Vercel project tools with GitHub integration
    "vercel_deploy",  # Fallback one-time deployment tools
    "supabase_mcp",
)
