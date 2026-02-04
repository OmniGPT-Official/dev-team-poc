# Google Docs API Tests

OAuth2-based tests for creating, reading, and updating Google Documents.

## Quick Start

```bash
# 1. Start the OAuth server
python tests/google_docs/oauth_server.py

# 2. Open browser -> Authorize -> Test runs automatically
open http://localhost:8000

# 3. (Optional) Run the standalone test using the saved token
python tests/google_docs/test_create_read_update.py
```

## Files

| File | Purpose |
|------|---------|
| `oauth_server.py` | FastAPI server: OAuth2 flow, token exchange, callback, auto-test |
| `test_create_read_update.py` | Standalone test: create, read, update a Google Doc |
| `token.json` | Persisted OAuth2 tokens (auto-created, **do not commit**) |

## How It Works

1. `oauth_server.py` starts on **http://localhost:8000**
2. You click **Authorize** -> Google login -> grant permissions
3. Google redirects to **http://localhost:8000/google-callback**
4. Server exchanges the code for **access token + refresh token**
5. Tokens are saved to **tests/google_docs/token.json**
6. Test runs automatically: creates a doc, reads it, updates it, displays results
7. Token auto-refreshes when expired

## Configuration

Credentials are set in the files (or override via env vars):

```
GOOGLE_CLIENT_ID=555194882766-...apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...
Redirect URI: http://localhost:8000/google-callback
```

Make sure this redirect URI is added in [Google Cloud Console](https://console.cloud.google.com/apis/credentials).

## Token Storage

Tokens are stored at `tests/google_docs/token.json` and automatically refresh when expired. This file is in `.gitignore`.
