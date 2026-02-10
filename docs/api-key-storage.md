# Architecture Decision Record: Per-User API Key Storage

## Problem

Some tools (ElevenLabs, Vercel, Supabase Management API, etc.) authenticate via simple API keys or Personal Access Tokens (PATs) rather than OAuth flows. These credentials need to be stored per-user, but the existing `user_oauth_connections` table is designed for OAuth — it carries refresh tokens, scopes, token URIs, and provider account IDs that don't apply to plain API keys.

## Decision

Create a separate `user_api_keys` table for storing per-user API keys and PATs. This keeps the schema clean — each table serves one credential model — and avoids nullable columns or overloaded fields.

## Schema Design

See `supabase/migrations/*_create_user_api_keys.sql` for the full schema.

### Column rationale

- **`provider text`** (not enum): Adding a new provider requires only an INSERT, not a DDL migration. This avoids the `ALTER TYPE` ceremony used by the OAuth table's enum.
- **Unique constraint on `(user_id, provider)`**: One key per provider per user. If a provider needs multiple keys in the future, this can be relaxed.
- **`label text`**: Optional friendly name (e.g. "My ElevenLabs Pro key") for display in a settings UI.
- **`metadata jsonb`**: Extensible per-provider data. Could store plan tier, key permissions, or expiration info.

### Relationship to `user_oauth_connections`

| Credential type | Table | Example providers |
|-----------------|-------|-------------------|
| OAuth (access + refresh tokens, scopes) | `user_oauth_connections` | Google Sheets, Gmail, Slack |
| API key / PAT (single secret string) | `user_api_keys` | ElevenLabs, Vercel, Supabase |

Use `user_oauth_connections` when the provider requires an OAuth flow. Use `user_api_keys` when the user pastes in a key from the provider's dashboard.

## Security Model

- **Service role key** is used server-side in `api_key_store.py` (via the shared `get_supabase_client()`). This bypasses RLS intentionally because `user_id` comes from the verified JWT.
- **RLS policies** are configured for defense-in-depth: users can only SELECT/INSERT/UPDATE/DELETE their own rows.
- **Keys are stored as plaintext** in the database. Supabase encrypts data at rest. Application-level encryption can be added in a future iteration.

## How to Add a New API-Key-Based Provider

1. **Choose a provider name**: Use lowercase, no spaces (e.g. `'elevenlabs'`, `'vercel'`, `'supabase'`).
2. **Frontend**: Add a settings UI field where the user pastes their key. Insert into `user_api_keys` with the chosen provider name.
3. **Backend** (`services/tool_injector.py`): In the `inject_user_tools` pre-hook, add a block:
   ```python
   key = get_api_key(user_id, "your_provider")
   if key:
       tools.append(YourProviderTools(api_key=key))
   ```
   For providers that need extra metadata (e.g. Supabase project ref), use `get_api_key_with_metadata()`:
   ```python
   data = get_api_key_with_metadata(user_id, "supabase")
   if data:
       project_ref = (data.get("metadata") or {}).get("project_ref")
       if project_ref:
           pat = data["api_key"]
           tools.append(MCPTools(
               url=f"https://mcp.supabase.com/mcp?project_ref={project_ref}",
               transport="streamable-http",
               server_params=StreamableHTTPClientParams(
                   url=f"https://mcp.supabase.com/mcp?project_ref={project_ref}",
                   headers={"Authorization": f"Bearer {pat}"},
               ),
           ))
   ```
4. **No migration needed** — the `provider` column is free-text.

## Environment Variables Required

| Variable | Purpose |
|----------|---------|
| `SUPABASE_URL` | Supabase project API URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key for server-side DB access |

No provider-specific env vars are needed — keys come from the database per-user.
