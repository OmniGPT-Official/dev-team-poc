# Architecture Decision Record: Per-User OAuth Token Storage

## Problem

The application previously hardcoded OAuth tokens (Google Sheets, Gmail) as environment variables shared across all users. This is incompatible with a multi-tenant SaaS where each user has their own Google account and needs independent OAuth connections. Environment variables are server-wide and cannot vary per user or per request.

## Decision

Store per-user OAuth tokens in a Supabase `user_oauth_connections` table. Each row links a user to a specific provider account with its own access/refresh tokens. The server retrieves the correct credentials at request time based on the authenticated user's ID from the JWT.

## Schema Design

See `supabase/migrations/*_create_user_oauth_connections.sql` for the full schema.

### Column rationale

- **`provider oauth_provider`** (enum): Initially created as `text`, then converted to an enum via `20260209105747_add_oauth_provider_enum.sql`. Adding a new provider requires an `ALTER TYPE oauth_provider ADD VALUE` migration.
- **`scopes text[]`**: Array of granted scopes for the connection. Useful for checking if a connection has the required permissions before use.
- **`metadata jsonb`**: Extensible per-provider data. For example, a per-user OAuth app could store its own `client_id`/`client_secret` here, or provider-specific fields like `team_id` for Slack.
- **`provider_account_id`**: The provider's unique identifier for the account (e.g. email address for Google). Combined with the unique constraint on `(user_id, provider, provider_account_id)`, this allows a user to connect multiple accounts for the same provider (e.g. work Gmail and personal Gmail).

## Security Model

- **Service role key** is used server-side in `oauth_store.py`. This bypasses RLS intentionally because the `user_id` comes from the decoded JWT `sub` claim (note: signature is not verified server-side — the server trusts that the frontend already authenticated via Supabase Auth).
- **RLS policies** are still configured for defense-in-depth. If the table is ever accessed from a client-side context (e.g. Supabase JS client), users can only see/modify their own rows.
- **Tokens are stored as plaintext** in the database. Supabase encrypts data at rest. For additional security, consider adding application-level encryption in a future iteration.

## Token Refresh

Google's `Credentials` object supports automatic token refresh when provided with a `refresh_token`, `client_id`, and `client_secret`. The current implementation passes these values so credentials auto-refresh during API calls.

**Future improvement**: After a successful refresh, persist the new `access_token` and `expires_at` back to the database so subsequent requests don't need to refresh again.

## How to Add a New Provider

1. Insert a row into `user_oauth_connections` with the new provider name (e.g. `'slack'`, `'notion'`).
2. Add a credentials builder function in `services/oauth_store.py` (similar to `get_google_credentials`) that constructs the provider's expected credential format.
3. Register a provider function in `services/tool_providers.py` using the `@register("name")` decorator. Then reference it in agents via `make_tool_hook("name")`.

## Environment Variables Required

| Variable | Purpose |
|----------|---------|
| `SUPABASE_URL` | Supabase project API URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key for server-side DB access |
| `GOOGLE_CLIENT_ID` | Google OAuth app client ID (shared across users) |
| `GOOGLE_CLIENT_SECRET` | Google OAuth app client secret (shared across users) |

The previous per-token env vars (`GOOGLE_SHEETS_ACCESS_TOKEN`, `GOOGLE_SHEETS_REFRESH_TOKEN`, `GOOGLE_GMAIL_ACCESS_TOKEN`, `GOOGLE_GMAIL_REFRESH_TOKEN`) are no longer used and should be removed from deployment configurations.
