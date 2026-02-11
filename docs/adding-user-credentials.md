# Adding OAuth or API Key Credentials for a User

This guide explains how to store per-user credentials so agents can use tools (Google Sheets, Gmail, Supabase, ElevenLabs, etc.) on behalf of a specific user.

## Which Table to Use

| Credential type | Table | When to use |
|-----------------|-------|-------------|
| OAuth (access + refresh tokens) | `user_oauth_connections` | Provider requires an OAuth flow (Google, Slack, Notion) |
| API key / PAT (single secret) | `user_api_keys` | User pastes a key from the provider's dashboard |

## Adding an OAuth Connection

Insert a row into `user_oauth_connections` with the user's tokens from the OAuth flow.

### Example: Google Sheets

```sql
INSERT INTO public.user_oauth_connections (
    user_id,
    provider,
    provider_account_id,
    account_label,
    access_token,
    refresh_token,
    token_uri,
    scopes
) VALUES (
    'b9d59094-51a4-48a3-8c0d-fc0870e6f6f9',   -- user's auth.users UUID
    'google_sheets',                             -- provider key (must match oauth_provider enum)
    'gianfranco@omnigpt.co',                     -- provider account identifier (e.g. email)
    'Google Sheets',                             -- friendly label for UI
    'ya29.a0AUM...',                             -- access token from OAuth flow
    '1//05GZ4qA...',                             -- refresh token from OAuth flow
    'https://oauth2.googleapis.com/token',       -- Google's token endpoint
    ARRAY[
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive.readonly'
    ]
);
```

### Example: Gmail

```sql
INSERT INTO public.user_oauth_connections (
    user_id,
    provider,
    provider_account_id,
    account_label,
    access_token,
    refresh_token,
    token_uri,
    scopes
) VALUES (
    'b9d59094-51a4-48a3-8c0d-fc0870e6f6f9',
    'google_gmail',
    'gianfranco@omnigpt.co',
    'Gmail',
    'ya29.a0AUM...',
    '1//05hTPBG...',
    'https://oauth2.googleapis.com/token',
    ARRAY[
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/calendar.events',
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/calendar.freebusy',
        'https://www.googleapis.com/auth/calendar.calendarlist.readonly'
    ]
);
```

### Required Fields

| Field | Description |
|-------|-------------|
| `user_id` | UUID from `auth.users` — the Supabase Auth user |
| `provider` | Must be a valid `oauth_provider` enum value. Adding a new provider requires a migration (`ALTER TYPE oauth_provider ADD VALUE 'new_provider'`) |
| `provider_account_id` | Unique identifier from the provider (e.g. email). Allows one user to connect multiple accounts for the same provider |
| `access_token` | Token from the OAuth flow |
| `refresh_token` | Refresh token for automatic renewal |
| `token_uri` | Provider's token endpoint (Google: `https://oauth2.googleapis.com/token`) |
| `scopes` | Array of granted OAuth scopes |

### How It Gets Used

`services/oauth_store.py` → `get_google_credentials(user_id, provider)` fetches the row and returns a `google.oauth2.credentials.Credentials` object. The `inject_user_tools` pre-hook in `services/tool_injector.py` calls this and wraps the credentials in the appropriate Agno tool class (`GoogleSheetsTools`, `GmailTools`).

## Adding an API Key

Insert a row into `user_api_keys` with the user's key.

### Example: Supabase PAT (with metadata)

```sql
INSERT INTO public.user_api_keys (
    user_id,
    provider,
    api_key,
    metadata
) VALUES (
    'b9d59094-51a4-48a3-8c0d-fc0870e6f6f9',
    'supabase',
    'sbp_14c0db...',                              -- Supabase Personal Access Token
    '{"project_ref": "qmfsbntaygggtjzlemyg"}'::jsonb  -- extra config needed by the tool
);
```

### Example: ElevenLabs (simple key, no metadata)

```sql
INSERT INTO public.user_api_keys (
    user_id,
    provider,
    api_key
) VALUES (
    'b9d59094-51a4-48a3-8c0d-fc0870e6f6f9',
    'elevenlabs',
    'sk_abc123...'
);
```

### Required Fields

| Field | Description |
|-------|-------------|
| `user_id` | UUID from `auth.users` |
| `provider` | Free-text string (e.g. `'elevenlabs'`, `'supabase'`, `'vercel'`). No migration needed for new providers |
| `api_key` | The secret key or PAT |
| `label` | Optional friendly name for UI display |
| `metadata` | Optional JSONB for provider-specific config (e.g. `project_ref` for Supabase) |

### How It Gets Used

`services/api_key_store.py` → `get_api_key(user_id, provider)` returns the key string. For providers that need metadata, use `get_api_key_with_metadata(user_id, provider)` which returns `{"api_key": ..., "metadata": ...}`. The `inject_user_tools` pre-hook handles both patterns.

## Adding Support for a New Provider

### New OAuth provider

1. Create a migration: `ALTER TYPE public.oauth_provider ADD VALUE 'new_provider';`
2. Add a credentials builder in `services/oauth_store.py` if the provider isn't Google-based.
3. Add the tool to `inject_user_tools` in `services/tool_injector.py`.

### New API key provider

1. No migration needed — `provider` is free-text.
2. Add a block in `inject_user_tools` in `services/tool_injector.py`:
   ```python
   key = get_api_key(user_id, "new_provider")
   if key:
       tools.append(NewProviderTools(api_key=key))
   ```
