"""Per-user OAuth credential storage backed by Supabase."""

from os import getenv
from typing import Optional

from google.oauth2.credentials import Credentials
from supabase import Client, create_client

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Return a singleton Supabase client using the service role key."""
    global _supabase_client
    if _supabase_client is None:
        url = getenv("SUPABASE_URL")
        key = getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
            )
        _supabase_client = create_client(url, key)
    return _supabase_client


def get_google_credentials(user_id: str, provider: str) -> Optional[Credentials]:
    """Fetch stored OAuth connection and return a Google Credentials object, or None."""
    result = (
        get_supabase_client()
        .table("user_oauth_connections")
        .select("access_token, refresh_token, token_uri")
        .eq("user_id", user_id)
        .eq("provider", provider)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None

    row = result.data[0]
    return Credentials(
        token=row["access_token"],
        refresh_token=row.get("refresh_token"),
        token_uri=row.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=getenv("GOOGLE_CLIENT_ID"),
        client_secret=getenv("GOOGLE_CLIENT_SECRET"),
    )
