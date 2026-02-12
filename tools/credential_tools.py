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


# ============================================================================
# GITHUB CREDENTIAL TOOLS
# ============================================================================

def check_github_token(user_id: str) -> Dict[str, Any]:
    """Check if GitHub token exists for user.

    Args:
        user_id: User UUID

    Returns:
        {
            "exists": bool,
            "valid": bool (if exists),
            "username": str (if valid),
            "message": str
        }
    """
    try:
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


def validate_and_store_github_token(user_id: str, github_token: str) -> Dict[str, Any]:
    """Validate a GitHub token and store it if valid.

    Args:
        user_id: User UUID
        github_token: GitHub personal access token to validate

    Returns:
        {
            "success": bool,
            "username": str (if successful),
            "message": str
        }
    """
    try:
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

def check_vercel_token(user_id: str) -> Dict[str, Any]:
    """Check if Vercel token exists for user.

    Args:
        user_id: User UUID

    Returns:
        {
            "exists": bool,
            "valid": bool (if exists),
            "message": str
        }
    """
    try:
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


def validate_and_store_vercel_token(user_id: str, vercel_token: str) -> Dict[str, Any]:
    """Validate a Vercel token and store it if valid.

    Args:
        user_id: User UUID
        vercel_token: Vercel API token to validate

    Returns:
        {
            "success": bool,
            "message": str
        }
    """
    try:
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
# GOOGLE CREDENTIALS TOOLS
# ============================================================================

def check_google_credentials(user_id: str) -> Dict[str, Any]:
    """Check if Google OAuth credentials exist for user.

    Args:
        user_id: User UUID

    Returns:
        {
            "exists": bool,
            "provider": str (google_docs or google_sheets),
            "message": str
        }
    """
    try:
        # Try google_docs first
        creds = get_google_credentials(user_id, "google_docs")
        if creds:
            return {
                "exists": True,
                "provider": "google_docs",
                "message": "Google Docs credentials found"
            }

        # Try google_sheets
        creds = get_google_credentials(user_id, "google_sheets")
        if creds:
            return {
                "exists": True,
                "provider": "google_sheets",
                "message": "Google Sheets credentials found"
            }

        return {
            "exists": False,
            "provider": None,
            "message": "No Google OAuth credentials found"
        }

    except Exception as e:
        return {
            "exists": False,
            "provider": None,
            "message": f"Error checking Google credentials: {str(e)}"
        }


# ============================================================================
# VALIDATION SUMMARY
# ============================================================================

def validate_all_credentials(user_id: str) -> Dict[str, Any]:
    """Check all required credentials for a user.

    Args:
        user_id: User UUID

    Returns:
        {
            "github": {...},
            "vercel": {...},
            "google": {...},
            "all_valid": bool,
            "missing": list of missing providers
        }
    """
    github = check_github_token(user_id)
    vercel = check_vercel_token(user_id)
    google = check_google_credentials(user_id)

    missing = []
    if not github.get("valid"):
        missing.append("github")
    if not vercel.get("valid"):
        missing.append("vercel")
    if not google.get("exists"):
        missing.append("google")

    return {
        "github": github,
        "vercel": vercel,
        "google": google,
        "all_valid": len(missing) == 0,
        "missing": missing
    }
