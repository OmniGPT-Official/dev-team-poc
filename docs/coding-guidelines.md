# Coding Guidelines

## Creating Agents

Follow the canonical pattern in [`email_followup.py`](../email_followup.py).

### Agent Structure

1. **Imports** — Import `Agent` and model from `agno`, any tool classes, credential helpers from `services/oauth_store.py`, and the shared `db` instance from `db.py`.
2. **Pre-hook function** — If the agent needs OAuth tools, define an `inject_oauth_tools` function that fetches per-user credentials and calls `agent.set_tools()`. See `email_followup.py` for the exact signature and flow.
3. **Agent instance** — Instantiate the `Agent` at module level with `pre_hooks`, `db=db`, and the standard configuration flags. Refer to `email_followup.py` for the full set of flags.

## Creating or Equipping OAuth Tools

Follow the pattern in [`services/oauth_store.py`](../services/oauth_store.py) and its usage in [`email_followup.py`](../email_followup.py).

### Rules

- Reuse `get_google_credentials` with a new `provider` string when adding support for a new Google service (e.g. `"google_calendar"`).
- Wrap the returned credentials in the corresponding Agno tool class inside the agent's pre-hook.
- Never hardcode tokens — credentials are always fetched at runtime from the `user_oauth_connections` table via Supabase.
- Use the naming format `google_<service>` for provider keys (e.g. `google_gmail`, `google_sheets`).

## Database Changes

All DDL changes (new tables, altered columns, new indexes, RLS policies, etc.) must be tracked via Supabase migration files under `supabase/migrations/`. Never apply schema changes directly — always create a migration so that changes are versioned and reproducible across environments.

## Database (`db.py`)

`db.py` provides the shared `PostgresDb` instance used by all agents, teams, and workflows.

**Do not modify `db.py` unless necessary.** It is a shared dependency — changes affect the entire project. If a modification is needed:

1. Document the reason clearly.
2. Check all imports (`from db import ...`) for downstream impact.
3. Ensure backward compatibility.
4. Discuss with the team before committing.
