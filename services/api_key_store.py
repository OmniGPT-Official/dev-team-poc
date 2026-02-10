"""Per-user API key storage backed by Supabase."""

from typing import Optional

from services.oauth_store import get_supabase_client


def get_api_key(user_id: str, provider: str) -> Optional[str]:
    """Fetch a stored API key for the given user and provider, or None."""
    result = (
        get_supabase_client()
        .table("user_api_keys")
        .select("api_key")
        .eq("user_id", user_id)
        .eq("provider", provider)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return result.data[0]["api_key"]


def get_api_key_with_metadata(user_id: str, provider: str) -> Optional[dict]:
    """Return {"api_key": ..., "metadata": ...} or None."""
    result = (
        get_supabase_client()
        .table("user_api_keys")
        .select("api_key, metadata")
        .eq("user_id", user_id)
        .eq("provider", provider)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return result.data[0]
