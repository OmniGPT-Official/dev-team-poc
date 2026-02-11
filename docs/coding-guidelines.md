# Coding Guidelines

## Creating Agents

Follow the canonical pattern in [`email_followup.py`](../email_followup.py).

### Agent Structure

1. **Imports** — Import `Agent` and model from `agno`, any static tool functions, `make_tool_hook` from `services/tool_injector`, and the shared `db` instance from `db.py`.
2. **Pre-hook** — Use `make_tool_hook("provider_a", "provider_b")` listing only the providers the agent actually needs. This replaces the old monolithic `inject_user_tools`.
3. **Agent instance** — Instantiate the `Agent` at module level with `pre_hooks`, `db=db`, and the standard configuration flags. Refer to `email_followup.py` for the full set of flags.

### Example

```python
from agno.agent import Agent
from agno.models.google import Gemini
from services.tool_injector import make_tool_hook
from db import db

my_agent = Agent(
    name="My Agent",
    model=Gemini(id="gemini-3-flash-preview"),
    pre_hooks=[make_tool_hook("google_sheets", "google_gmail")],
    db=db,
)
```

### Static Tool Preservation

If an agent has static tools defined at init (e.g. custom function tools), the hook preserves them automatically. Static tools are snapshotted on first run and prepended on every subsequent call:

```python
agent = Agent(
    tools=[submit_batch_call, get_batch_status],  # static tools
    pre_hooks=[make_tool_hook("google_sheets")],   # OAuth tools injected at runtime
)
# At runtime the agent will have: [submit_batch_call, get_batch_status, GoogleSheetsTools(...)]
```

## Adding a New Tool Provider

Add one function to [`services/tool_providers.py`](../services/tool_providers.py). No other files need to change.

```python
@register("google_calendar")
def _google_calendar(user_id: str):
    from agno.tools.google_calendar import GoogleCalendarTools
    from services.oauth_store import get_google_credentials

    creds = get_google_credentials(user_id, "google_calendar")
    if not creds:
        return None
    return GoogleCalendarTools(creds=creds)
```

Then reference it in agents: `make_tool_hook("google_calendar")`.

### Available Providers

| Name | Credential source | Tool class |
|------|-------------------|------------|
| `google_sheets` | `oauth_store` | `GoogleSheetsTools` |
| `google_gmail` | `oauth_store` | `GmailTools` |
| `elevenlabs` | `api_key_store` | `ElevenLabsTools` |
| `supabase_mcp` | `api_key_store` | `MCPTools` |

## Creating or Equipping OAuth Tools

Follow the pattern in [`services/oauth_store.py`](../services/oauth_store.py) and its usage in [`services/tool_providers.py`](../services/tool_providers.py).

### Rules

- Reuse `get_google_credentials` with a new `provider` string when adding support for a new Google service (e.g. `"google_calendar"`).
- Wrap the returned credentials in the corresponding Agno tool class inside a provider function in `tool_providers.py`.
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
