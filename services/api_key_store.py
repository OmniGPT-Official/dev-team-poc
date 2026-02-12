"""Per-user API key storage backed by Supabase."""

from typing import Optional

from services.oauth_store import get_supabase_client


def get_api_key(user_id: str, provider: str) -> Optional[str]:
    """Fetch a stored API key for the given user and provider, or None."""
    print(f"[api_key_store] get_api_key(user_id={user_id!r}, provider={provider!r})")
    try:
        result = (
            get_supabase_client()
            .table("user_api_keys")
            .select("api_key")
            .eq("user_id", user_id)
            .eq("provider", provider)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as e:
        print(f"[api_key_store] ERROR querying user_api_keys: {e}")
        return None
    if not result.data:
        print(f"[api_key_store] No rows found for user_id={user_id!r}, provider={provider!r}")
        return None
    key = result.data[0]["api_key"]
    preview = f"{key[:6]}...{key[-4:]}" if key and len(key) > 10 else "(empty)"
    print(f"[api_key_store] Found key for {provider}: {preview}")
    return key


def get_api_key_with_metadata(user_id: str, provider: str) -> Optional[dict]:
    """Return {"api_key": ..., "metadata": ...} or None."""
    result = (
        get_supabase_client()
        .table("user_api_keys")
        .select("api_key, metadata")
        .eq("user_id", user_id)
        .eq("provider", provider)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return result.data[0]
