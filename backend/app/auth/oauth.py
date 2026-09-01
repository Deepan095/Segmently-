"""Google OAuth 2.0 helper functions.

All network calls use ``httpx.AsyncClient``. The redirect URI always comes
from ``settings.GOOGLE_REDIRECT_URI`` so it matches the value registered in
the Google Cloud console.

The OAuth ``state`` parameter is a short-lived signed JWT (CSRF protection):
:func:`create_oauth_state` mints it before redirecting the user to Google and
:func:`verify_oauth_state` validates it on the callback.
"""

from __future__ import annotations

import logging
import secrets
from datetime import timedelta
from typing import Any
from urllib.parse import urlencode

import httpx

from app.auth.jwt import create_access_token, decode_token
from app.config import settings

logger = logging.getLogger("segmently.auth.oauth")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

_OAUTH_STATE_TYPE = "oauth_state"
_HTTP_TIMEOUT = 10.0


class OAuthError(Exception):
    """Raised when the Google OAuth exchange fails."""


def create_oauth_state() -> str:
    """Return a signed, short-lived state token for the OAuth redirect."""
    return create_access_token(
        {"type_hint": _OAUTH_STATE_TYPE, "nonce": secrets.token_urlsafe(16)},
        expires_delta=timedelta(minutes=10),
    )


def verify_oauth_state(state: str) -> bool:
    """Return ``True`` if ``state`` is a valid, unexpired state token."""
    payload = decode_token(state)
    if not payload:
        return False
    return payload.get("type_hint") == _OAUTH_STATE_TYPE


def build_authorization_url(state: str) -> str:
    """Build the Google consent-screen URL the user is redirected to."""
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> dict[str, Any]:
    """Exchange an authorization ``code`` for Google access tokens."""
    data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
    }
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        response = await client.post(GOOGLE_TOKEN_URL, data=data)
    if response.status_code != httpx.codes.OK:
        logger.warning("Google token exchange failed: %s", response.text)
        raise OAuthError("Failed to exchange authorization code")
    return response.json()


async def fetch_userinfo(access_token: str) -> dict[str, Any]:
    """Fetch the Google profile for ``access_token``."""
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.status_code != httpx.codes.OK:
        logger.warning("Google userinfo fetch failed: %s", response.text)
        raise OAuthError("Failed to fetch Google user info")
    return response.json()
