"""OAuth routes for third-party provider connections (Instagram via Instagram Login)."""

import base64
import hashlib
import hmac
import json
import secrets
from os import getenv
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

oauth_router = APIRouter(prefix="/oauth")


def _get_meta_config() -> dict:
    """Return Meta app configuration from environment variables."""
    return {
        "app_id": getenv("META_APP_ID", ""),
        "app_secret": getenv("META_APP_SECRET", ""),
        "redirect_uri": getenv("META_REDIRECT_URI", ""),
    }


def _sign_state(payload: dict, secret: str) -> str:
    """Create a signed state parameter: base64(json(payload)) + HMAC signature."""
    data = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
    return f"{data}.{sig}"


def generate_instagram_auth_url(user_id: str) -> str | None:
    """Build an Instagram OAuth authorization URL for the given user.

    Returns ``None`` when Meta OAuth environment variables are not configured.
    """
    meta = _get_meta_config()
    if not meta["app_id"] or not meta["app_secret"] or not meta["redirect_uri"]:
        return None

    state = _sign_state(
        {"user_id": user_id, "nonce": secrets.token_hex(16)},
        meta["app_secret"],
    )

    params = {
        "enable_fb_login": "0",
        "force_authentication": "1",
        "client_id": meta["app_id"],
        "redirect_uri": meta["redirect_uri"],
        "response_type": "code",
        "scope": "instagram_business_basic,instagram_business_content_publish",
        "state": state,
    }
    qs = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
    return f"https://www.instagram.com/oauth/authorize?{qs}"


@oauth_router.get("/instagram/authorize")
async def instagram_authorize(request: Request):
    """Generate an Instagram OAuth URL for authorization (Instagram Login flow)."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    url = generate_instagram_auth_url(user_id)
    if not url:
        return JSONResponse(
            {"error": "Instagram OAuth is not configured"}, status_code=500
        )

    return JSONResponse({"url": url})
