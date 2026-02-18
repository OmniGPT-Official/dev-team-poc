"""Hook factory for per-user tool injection.

Usage::

    from services.tool_injector import make_tool_hook

    agent = Agent(
        ...
        pre_hooks=[make_tool_hook("google_sheets", "google_gmail")],
    )

    team = Team(
        ...
        pre_hooks=[make_tool_hook("instagram")],
    )

Each agent/team declares only the providers it needs.  Static tools defined
at init time are preserved across runs.
"""

from __future__ import annotations

import re

from services.tool_providers import resolve_tools

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# In-memory cache: email → user_uuid (persists for process lifetime)
_id_cache: dict[str, str | None] = {}


def _resolve_user_id(raw_id: str) -> str | None:
    """Return a UUID user_id for *raw_id*.

    Resolution order:
      1. Already a UUID → return as-is
      2. Looks like an email → look up via Supabase auth admin
    Results are cached in-memory after the first DB hit.
    """
    if _UUID_RE.match(raw_id):
        return raw_id

    # Check cache first
    if raw_id in _id_cache:
        cached = _id_cache[raw_id]
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
                _id_cache[raw_id] = uuid
                print(f"[pre-hook] Resolved email {raw_id!r} → {uuid!r} (cached)")
                return uuid
        except Exception as e:
            print(f"[pre-hook] email lookup failed: {e}")
        _id_cache[raw_id] = None
        print(f"[pre-hook] No user found for email {raw_id!r}, skipping tool injection")
        return None

    # Unknown format — cannot resolve
    print(f"[pre-hook] {raw_id!r} is not a UUID or email, skipping tool injection")
    return None


def make_tool_hook(*provider_names: str):
    """Return a pre-hook that injects only the requested providers.

    Works with both Agent and Team pre-hooks.  Agno passes ``agent=self``
    for Agent hooks and ``team=self`` for Team hooks — we accept both.

    Static tools (those already on the target before the first hook run) are
    snapshotted and prepended on every subsequent run so they are never lost.
    """

    def _hook(agent=None, team=None, user_id: str = "") -> None:
        target = agent or team
        if target is None:
            print("[pre-hook] WARNING: Neither agent nor team provided to hook, skipping")
            return

        print(f"[pre-hook] make_tool_hook({provider_names}) called for {target.name} — user_id={user_id!r}")
        if not user_id:
            # Fallback: workflow step agents don't receive user_id directly from Agno.
            # Read from the context variable set by the HTTP middleware for this request.
            from services.user_context import get_current_user_id
            user_id = get_current_user_id() or ""
            if user_id:
                print(f"[pre-hook] Resolved user_id from request context: {user_id!r}")
            else:
                print(f"[pre-hook] WARNING: No user_id for {target.name} — tools cannot be injected. "
                      f"Ensure user_id is passed when running agents/workflows.")
                return

        # Resolve emails to UUIDs (cached after first lookup)
        user_id = _resolve_user_id(user_id)
        if not user_id:
            return

        # Snapshot static tools on first invocation.
        # TODO(production): This monkey-patches _static_tools onto the instance.
        # For production, move the snapshot into the closure (nonlocal) or use a more
        # unique attribute name (e.g. _omnigpt_static_tools) to avoid potential
        # collisions with future Agno internals.
        if not hasattr(target, "_static_tools"):
            target._static_tools = list(target.tools or [])

        user_tools = resolve_tools(user_id, *provider_names)
        combined = target._static_tools + user_tools

        print(f"[pre-hook] Injecting {len(user_tools)} user tool(s): {[type(t).__name__ for t in user_tools]} "
              f"(+ {len(target._static_tools)} static)")
        target.set_tools(combined)

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
