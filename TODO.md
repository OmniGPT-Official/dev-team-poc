# TODO

## JWT Token Refresh

**Problem:** Our backend authenticates with Supabase using a JWT access token, but we call the Supabase REST API directly — we don't use the Supabase client library (`supabase-py`), which would automatically detect an expired token and use the refresh token to silently get a new one. Since we're making raw API calls, there's no automatic refresh. When the access token expires, requests fail with 401.

**Workaround:** Increased access token expiry from 1 hour to 7 days (604800s) in Supabase dashboard (Auth > JWT Keys > Access token expiry time). Every 7 days we manually regenerate the token.

**Ideal fix:** Either implement refresh token rotation in our backend (detect expiry, call `/auth/v1/token?grant_type=refresh_token`, swap in the new token), or use the `supabase-py` client library which handles it automatically. Once fixed, revert the access token expiry back to `3600` seconds (1 hour).
