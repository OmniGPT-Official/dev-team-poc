"""
Credential Management Tools

Tools for validating, storing, and managing user credentials (GitHub, Vercel, Google, etc.)
Used by the Credentials Manager agent to ensure all required tokens are present and valid.
"""

import os
import requests
from typing import Optional, Dict, Any
from services.api_key_store import get_api_key, store_api_key
from services.oauth_store import get_google_credentials, get_supabase_client
from services.user_context import get_current_user_id


# ============================================================================
# GITHUB CREDENTIAL TOOLS
# ============================================================================

def check_github_token(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Check if GitHub token exists for user.

    Args:
        user_id: User UUID (optional - will auto-fetch from context if not provided)

    Returns:
        {
            "exists": bool,
            "valid": bool (if exists),
            "username": str (if valid),
            "message": str
        }
    """
    try:
        # Auto-fetch user_id from context if not provided
        if not user_id:
            user_id = get_current_user_id()

        if not user_id:
            return {
                "exists": False,
                "valid": False,
                "username": None,
                "message": "No user_id available in context. Please authenticate first."
            }

        token = get_api_key(user_id, "github")

        if not token:
            return {
                "exists": False,
                "valid": False,
                "username": None,
                "message": "No GitHub token found for this user"
            }

        # Validate token by calling GitHub API
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        response = requests.get("https://api.github.com/user", headers=headers, timeout=10)

        if response.status_code == 200:
            user_data = response.json()
            username = user_data.get("login", "unknown")
            return {
                "exists": True,
                "valid": True,
                "username": username,
                "message": f"GitHub token is valid. Owner: {username}"
            }
        else:
            return {
                "exists": True,
                "valid": False,
                "username": None,
                "message": f"GitHub token exists but is invalid (status: {response.status_code})"
            }

    except Exception as e:
        return {
            "exists": False,
            "valid": False,
            "username": None,
            "message": f"Error checking GitHub token: {str(e)}"
        }


def validate_and_store_github_token(github_token: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Validate a GitHub token and store it if valid.

    Args:
        github_token: GitHub personal access token to validate
        user_id: User UUID (optional - will auto-fetch from context if not provided)

    Returns:
        {
            "success": bool,
            "username": str (if successful),
            "message": str
        }
    """
    try:
        # Auto-fetch user_id from context if not provided
        if not user_id:
            user_id = get_current_user_id()

        if not user_id:
            return {
                "success": False,
                "username": None,
                "message": "No user_id available in context. Please authenticate first."
            }

        # Validate token by calling GitHub API
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        response = requests.get("https://api.github.com/user", headers=headers, timeout=10)

        if response.status_code != 200:
            return {
                "success": False,
                "username": None,
                "message": f"Invalid GitHub token. GitHub API returned status {response.status_code}"
            }

        user_data = response.json()
        username = user_data.get("login", "unknown")

        # Store the token
        store_api_key(user_id, "github", github_token)

        return {
            "success": True,
            "username": username,
            "message": f"GitHub token validated and stored successfully. Owner: {username}"
        }

    except Exception as e:
        return {
            "success": False,
            "username": None,
            "message": f"Error validating GitHub token: {str(e)}"
        }


# ============================================================================
# VERCEL CREDENTIAL TOOLS
# ============================================================================

def check_vercel_token(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Check if Vercel token exists for user.

    Args:
        user_id: User UUID (optional - will auto-fetch from context if not provided)

    Returns:
        {
            "exists": bool,
            "valid": bool (if exists),
            "message": str
        }
    """
    try:
        # Auto-fetch user_id from context if not provided
        if not user_id:
            user_id = get_current_user_id()

        if not user_id:
            return {
                "exists": False,
                "valid": False,
                "message": "No user_id available in context. Please authenticate first."
            }

        token = get_api_key(user_id, "vercel")

        if not token:
            return {
                "exists": False,
                "valid": False,
                "message": "No Vercel token found for this user"
            }

        # Validate token by calling Vercel API
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.get("https://api.vercel.com/v2/user", headers=headers, timeout=10)

        if response.status_code == 200:
            return {
                "exists": True,
                "valid": True,
                "message": "Vercel token is valid"
            }
        else:
            return {
                "exists": True,
                "valid": False,
                "message": f"Vercel token exists but is invalid (status: {response.status_code})"
            }

    except Exception as e:
        return {
            "exists": False,
            "valid": False,
            "message": f"Error checking Vercel token: {str(e)}"
        }


def validate_and_store_vercel_token(vercel_token: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Validate a Vercel token and store it if valid.

    Args:
        vercel_token: Vercel API token to validate
        user_id: User UUID (optional - will auto-fetch from context if not provided)

    Returns:
        {
            "success": bool,
            "message": str
        }
    """
    try:
        # Auto-fetch user_id from context if not provided
        if not user_id:
            user_id = get_current_user_id()

        if not user_id:
            return {
                "success": False,
                "message": "No user_id available in context. Please authenticate first."
            }

        # Validate token by calling Vercel API
        headers = {
            "Authorization": f"Bearer {vercel_token}",
            "Content-Type": "application/json"
        }

        response = requests.get("https://api.vercel.com/v2/user", headers=headers, timeout=10)

        if response.status_code != 200:
            return {
                "success": False,
                "message": f"Invalid Vercel token. Vercel API returned status {response.status_code}"
            }

        # Store the token
        store_api_key(user_id, "vercel", vercel_token)

        return {
            "success": True,
            "message": "Vercel token validated and stored successfully"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error validating Vercel token: {str(e)}"
        }


# ============================================================================
# SUPABASE CREDENTIAL TOOLS
# ============================================================================

def check_supabase_token(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Check if Supabase token exists for user.

    Args:
        user_id: User UUID (optional - will auto-fetch from context if not provided)

    Returns:
        {
            "exists": bool,
            "valid": bool (if exists),
            "project_ref": str (if valid),
            "message": str
        }
    """
    try:
        # Auto-fetch user_id from context if not provided
        if not user_id:
            user_id = get_current_user_id()

        if not user_id:
            return {
                "exists": False,
                "valid": False,
                "project_ref": None,
                "message": "No user_id available in context. Please authenticate first."
            }

        token = get_api_key(user_id, "supabase")

        if not token:
            return {
                "exists": False,
                "valid": False,
                "project_ref": None,
                "message": "No Supabase token found for this user"
            }

        # Validate token by calling Supabase Management API
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.get("https://api.supabase.com/v1/projects", headers=headers, timeout=10)

        if response.status_code == 200:
            projects = response.json()
            if projects and len(projects) > 0:
                # Get first project ref as example
                project_ref = projects[0].get("ref", "unknown")
                return {
                    "exists": True,
                    "valid": True,
                    "project_ref": project_ref,
                    "message": f"Supabase token is valid. Found {len(projects)} project(s)"
                }
            else:
                return {
                    "exists": True,
                    "valid": True,
                    "project_ref": None,
                    "message": "Supabase token is valid but no projects found"
                }
        else:
            return {
                "exists": True,
                "valid": False,
                "project_ref": None,
                "message": f"Supabase token exists but is invalid (status: {response.status_code})"
            }

    except Exception as e:
        return {
            "exists": False,
            "valid": False,
            "project_ref": None,
            "message": f"Error checking Supabase token: {str(e)}"
        }


def validate_and_store_supabase_token(supabase_token: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Validate a Supabase token and store it if valid.

    Args:
        supabase_token: Supabase Personal Access Token to validate
        user_id: User UUID (optional - will auto-fetch from context if not provided)

    Returns:
        {
            "success": bool,
            "project_count": int (if successful),
            "message": str
        }
    """
    try:
        # Auto-fetch user_id from context if not provided
        if not user_id:
            user_id = get_current_user_id()

        if not user_id:
            return {
                "success": False,
                "project_count": 0,
                "message": "No user_id available in context. Please authenticate first."
            }

        # Validate token by calling Supabase Management API
        headers = {
            "Authorization": f"Bearer {supabase_token}",
            "Content-Type": "application/json"
        }

        response = requests.get("https://api.supabase.com/v1/projects", headers=headers, timeout=10)

        if response.status_code != 200:
            return {
                "success": False,
                "project_count": 0,
                "message": f"Invalid Supabase token. Supabase API returned status {response.status_code}"
            }

        projects = response.json()
        project_count = len(projects) if projects else 0

        # Store the token
        store_api_key(user_id, "supabase", supabase_token)

        return {
            "success": True,
            "project_count": project_count,
            "message": f"Supabase token validated and stored successfully. Found {project_count} project(s)"
        }

    except Exception as e:
        return {
            "success": False,
            "project_count": 0,
            "message": f"Error validating Supabase token: {str(e)}"
        }


# ============================================================================
# GOOGLE CREDENTIALS TOOLS
# ============================================================================

def check_google_credentials(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Check if Google OAuth credentials exist for user by querying user_oauth_connections table.

    Args:
        user_id: User UUID (optional - will auto-fetch from context if not provided)

    Returns:
        {
            "exists": bool,
            "providers": list of provider names found,
            "message": str
        }
    """
    try:
        # Auto-fetch user_id from context if not provided
        if not user_id:
            user_id = get_current_user_id()

        if not user_id:
            return {
                "exists": False,
                "providers": [],
                "message": "No user_id available in context. Please authenticate first."
            }

        # Query user_oauth_connections table for known Google providers
        # Note: provider column is an enum, so we check specific values
        supabase = get_supabase_client()

        # Check for common Google OAuth provider names
        google_providers = ["google_docs", "google_sheets", "google_gmail"]
        found_providers = []

        for provider in google_providers:
            result = supabase.table("user_oauth_connections") \
                .select("provider") \
                .eq("user_id", user_id) \
                .eq("provider", provider) \
                .limit(1) \
                .execute()

            if result.data and len(result.data) > 0:
                found_providers.append(provider)

        if found_providers:
            return {
                "exists": True,
                "providers": found_providers,
                "message": f"Google OAuth credentials found: {', '.join(found_providers)}"
            }

        return {
            "exists": False,
            "providers": [],
            "message": "No Google OAuth credentials found in user_oauth_connections table"
        }

    except Exception as e:
        return {
            "exists": False,
            "providers": [],
            "message": f"Error checking Google credentials: {str(e)}"
        }


# ============================================================================
# VALIDATION SUMMARY
# ============================================================================

def validate_all_credentials(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Check all required credentials for a user.

    Args:
        user_id: User UUID (optional - will auto-fetch from context if not provided)

    Returns:
        {
            "github": {...},
            "vercel": {...},
            "supabase": {...},
            "google": {...},
            "all_valid": bool,
            "missing": list of missing providers
        }
    """
    # Auto-fetch user_id from context if not provided
    if not user_id:
        user_id = get_current_user_id()

    if not user_id:
        return {
            "github": {"exists": False, "valid": False, "message": "No user_id in context"},
            "vercel": {"exists": False, "valid": False, "message": "No user_id in context"},
            "supabase": {"exists": False, "valid": False, "message": "No user_id in context"},
            "google": {"exists": False, "providers": [], "message": "No user_id in context"},
            "all_valid": False,
            "missing": ["github", "vercel", "supabase", "google"],
            "error": "No user_id available in context. Please authenticate first.",
            "summary": "❌ Missing: github, vercel, supabase, google"
        }

    github = check_github_token(user_id)
    vercel = check_vercel_token(user_id)
    supabase = check_supabase_token(user_id)
    google = check_google_credentials(user_id)

    missing = []
    if not github.get("valid"):
        missing.append("github")
    if not vercel.get("valid"):
        missing.append("vercel")
    if not supabase.get("valid"):
        missing.append("supabase")
    if not google.get("exists"):
        missing.append("google")

    all_valid = len(missing) == 0

    # Build summary message
    if all_valid:
        summary = "✅ All credentials valid"
    else:
        summary = f"❌ Missing: {', '.join(missing)}"

    return {
        "github": github,
        "vercel": vercel,
        "supabase": supabase,
        "google": google,
        "all_valid": all_valid,
        "missing": missing,
        "summary": summary
    }


# ============================================================================
# SMART BROWSER SESSION STORAGE
# Stores browser session cookies per user per domain so the AI browser
# can skip login on repeat visits.
# ============================================================================

def save_platform_session(
    user_id: str,
    domain: str,
    cookies: list,
) -> bool:
    """Save browser session cookies for a platform domain.

    Args:
        user_id: The authenticated user's UUID.
        domain:  The domain the cookies belong to (e.g. 'th.indeed.com').
        cookies: List of cookie dicts from Playwright context.cookies().

    Returns:
        True on success, False on failure.
    """
    import json as _json
    provider = f"session_{domain}"
    try:
        return bool(store_api_key(user_id, provider, _json.dumps(cookies)))
    except Exception as e:
        print(f"[credential_tools] save_platform_session error: {e}")
        return False


def get_platform_session(
    user_id: str,
    domain: str,
) -> Optional[list]:
    """Retrieve saved browser session cookies for a platform domain.

    Args:
        user_id: The authenticated user's UUID.
        domain:  The domain (e.g. 'th.indeed.com').

    Returns:
        List of cookie dicts if found, or None.
    """
    import json as _json
    provider = f"session_{domain}"
    try:
        raw = get_api_key(user_id, provider)
        if not raw:
            return None
        return _json.loads(raw)
    except Exception as e:
        print(f"[credential_tools] get_platform_session error: {e}")
        return None
