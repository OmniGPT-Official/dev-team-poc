"""Per-user OAuth credential storage backed by Supabase."""

from os import getenv
from typing import Any, Optional

from google.oauth2.credentials import Credentials
from supabase import Client, create_client

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Return a singleton Supabase client using the service role key."""
    global _supabase_client
    if _supabase_client is None:
        url = getenv("SUPABASE_URL")
        key = getenv("SUPABASE_SERVICE_ROLE_KEY")
        url_preview = f"{url[:30]}..." if url and len(url) > 30 else url
        key_preview = f"{key[:8]}...{key[-4:]}" if key and len(key) > 12 else ("(not set)" if not key else "***")
        print(f"[supabase] Initializing client — URL={url_preview}, KEY={key_preview}")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
            )
        _supabase_client = create_client(url, key)
        print(f"[supabase] Client created successfully")
    return _supabase_client


def get_google_credentials(user_id: str, provider: str) -> Optional[Credentials]:
    """Fetch stored OAuth connection and return a Google Credentials object, or None."""
    result = (
        get_supabase_client()
        .table("user_oauth_connections")
        .select("access_token, refresh_token, token_uri, scopes, expires_at")
        .eq("user_id", user_id)
        .eq("provider", provider)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None

    row = result.data[0]

    # Parse expiry if available
    expiry = None
    if row.get("expires_at"):
        try:
            from datetime import datetime
            expiry = datetime.fromisoformat(row["expires_at"].replace('Z', '+00:00'))
        except Exception as e:
            print(f"[oauth_store] Could not parse expires_at: {e}")

    # Get scopes from database (should be an array)
    scopes = row.get("scopes") or []

    print(f"[oauth_store] Retrieved credentials for {provider}: scopes={scopes}, expires_at={row.get('expires_at')}")

    return Credentials(
        token=row["access_token"],
        refresh_token=row.get("refresh_token"),
        token_uri=row.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=getenv("GOOGLE_CLIENT_ID"),
        client_secret=getenv("GOOGLE_CLIENT_SECRET"),
        scopes=scopes,
        expiry=expiry,
    )


def get_instagram_credentials(user_id: str) -> Optional[dict[str, Any]]:
    """Fetch stored Instagram OAuth connection and return credentials dict, or None."""
    result = (
        get_supabase_client()
        .table("user_oauth_connections")
        .select("access_token, metadata")
        .eq("user_id", user_id)
        .eq("provider", "instagram")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None

    row = result.data[0]
    metadata = row.get("metadata") or {}
    ig_user_id = metadata.get("ig_user_id")
    if not ig_user_id:
        print(f"[oauth_store] Instagram credentials found but missing ig_user_id in metadata")
        return None

    print(f"[oauth_store] Retrieved Instagram credentials for user {user_id}")
    return {"access_token": row["access_token"], "ig_user_id": ig_user_id}


def update_google_credentials(user_id: str, provider: str, creds: Credentials) -> bool:
    """Update stored OAuth connection with refreshed credentials.

    Args:
        user_id: User ID
        provider: OAuth provider (e.g. 'google_sheets', 'google_docs', 'google_gmail')
        creds: Google Credentials object (potentially refreshed)

    Returns:
        True if update successful, False otherwise
    """
    if not creds or not creds.token:
        print(f"[oauth_store] Cannot update credentials - invalid creds object")
        return False

    try:
        # Calculate expiry timestamp if available
        expires_at = None
        if creds.expiry:
            expires_at = creds.expiry.isoformat()

        update_data = {
            "access_token": creds.token,
        }

        # Only update expiry if available
        if expires_at:
            update_data["expires_at"] = expires_at

        result = (
            get_supabase_client()
            .table("user_oauth_connections")
            .update(update_data)
            .eq("user_id", user_id)
            .eq("provider", provider)
            .execute()
        )

        if result.data:
            token_preview = f"{creds.token[:8]}...{creds.token[-4:]}" if len(creds.token) > 12 else "***"
            print(f"[oauth_store] Updated credentials for {provider}: token={token_preview}, expires_at={expires_at}")
            return True
        else:
            print(f"[oauth_store] No rows updated for user_id={user_id}, provider={provider}")
            return False
    except Exception as e:
        print(f"[oauth_store] ERROR updating credentials: {e}")
        return False
