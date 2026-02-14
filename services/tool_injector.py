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

from agno.agent import Agent

from services.tool_providers import resolve_tools


def make_tool_hook(*provider_names: str):
    """Return a pre-hook that injects only the requested providers.

    Static tools (those already on the agent before the first hook run) are
    snapshotted and prepended on every subsequent run so they are never lost.
    """

    def _hook(agent: Agent, user_id: str) -> None:
        print(f"[pre-hook] make_tool_hook({provider_names}) called for {agent.name} — user_id={user_id!r}")
        if not user_id:
            print("[pre-hook] No user_id, skipping tool injection")
            return

        # Snapshot static tools on first invocation
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
