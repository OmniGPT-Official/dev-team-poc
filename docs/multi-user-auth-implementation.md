# Multi-User Authentication and Credential Storage

## Overview

AgentOS identifies users via a lightweight JWT middleware and stores per-user credentials in two Supabase tables. This enables multi-tenant operation where each user connects their own Google account, API keys, etc.

```
Client (with Supabase JWT)
  → SupabaseUserMiddleware (extracts user_id from JWT `sub` claim)
    → Agent pre-hook (fetches per-user credentials from Supabase)
      → Agent runs with user's own tools
```

## User Identification: JWT Middleware

Defined in `agno_agent.py` as `SupabaseUserMiddleware`.

**How it works:**

1. Checks `X-Supabase-Token` header first (used by Agno UI custom headers)
2. Falls back to `Authorization: Bearer <token>` header (used by frontend)
3. Decodes the JWT **without signature verification** and extracts the `sub` claim
4. Sets `request.state.user_id` for downstream use by agent pre-hooks

**Current limitations:**

- No signature verification (`verify_signature: False`). The server trusts that tokens come from an authenticated frontend that already validated with Supabase Auth.
- No RBAC or scope checking.
- No `session_id` extraction — only `user_id`.

## Credential Storage

Per-user credentials are stored in two Supabase tables, separated by credential type.

| Credential type | Table | Example providers | Backend module |
|-----------------|-------|-------------------|----------------|
| OAuth (access + refresh tokens) | `user_oauth_connections` | `google_sheets`, `google_gmail` | `services/oauth_store.py` |
| API key / PAT (single secret) | `user_api_keys` | `elevenlabs`, `vercel`, `supabase` | `services/api_key_store.py` |

### OAuth tokens (`user_oauth_connections`)

Schema: `supabase/migrations/20260209105739_create_user_oauth_connections.sql`

Key columns: `user_id`, `provider`, `provider_account_id`, `access_token`, `refresh_token`, `token_uri`, `scopes`, `metadata`.

Unique constraint: `(user_id, provider, provider_account_id)` — allows multiple accounts per provider (e.g. work Gmail + personal Gmail).

Retrieved by `get_google_credentials(user_id, provider)` in `services/oauth_store.py`, which returns a `google.oauth2.credentials.Credentials` object with auto-refresh support (passes `refresh_token`, `client_id`, `client_secret`).

### API keys (`user_api_keys`)

Schema: `supabase/migrations/20260210102113_create_user_api_keys.sql`

Key columns: `user_id`, `provider`, `api_key`, `label`, `metadata`.

Unique constraint: `(user_id, provider)` — one key per provider per user.

Retrieved by `get_api_key(user_id, provider)` or `get_api_key_with_metadata(user_id, provider)` in `services/api_key_store.py`.

## Tool Injection: Pre-Hook

`services/tool_injector.py` defines `inject_user_tools(agent, user_id)`, which runs before each agent invocation. It:

1. Fetches Google Sheets and Gmail OAuth credentials → wraps in `GoogleSheetsTools`, `GmailTools`
2. Fetches ElevenLabs API key → wraps in `ElevenLabsTools`
3. Fetches Supabase PAT + project ref from metadata → wraps in `MCPTools`
4. Calls `agent.set_tools(tools)` with whatever was found

Agents use this by passing `pre_hooks=[inject_user_tools]` at instantiation.

## Security Model

- **Service role key** is used server-side in `oauth_store.py` and `api_key_store.py`. This bypasses RLS because `user_id` comes from the JWT (not user input).
- **RLS policies** are configured on both tables as defense-in-depth — users can only SELECT/INSERT/UPDATE/DELETE their own rows.
- **Tokens and keys are stored as plaintext.** Supabase encrypts data at rest. Application-level encryption can be added later.

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `SUPABASE_URL` | Supabase project API URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key for server-side DB access |
| `GOOGLE_CLIENT_ID` | Google OAuth app client ID (shared across users) |
| `GOOGLE_CLIENT_SECRET` | Google OAuth app client secret (shared across users) |
