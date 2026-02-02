# Supabase MCP Tests

Tests for Supabase operations via the Model Context Protocol (MCP).

## Status: Placeholder

No tests implemented yet. This folder is reserved for Supabase MCP integration tests.

## Planned Tests

- Database CRUD operations
- Auth / user management
- Storage (file upload/download)
- Realtime subscriptions
- Edge Functions invocation

## Quick Start (once implemented)

```bash
# Set your Supabase credentials
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_KEY="YOUR_SUPABASE_SERVICE_KEY_HERE"

# Run tests
python tests/supabase_mcp/test_supabase_mcp.py
```

## Get Credentials

1. Go to https://app.supabase.com
2. Select your project
3. Go to Settings > API
4. Copy the Project URL and service_role key
