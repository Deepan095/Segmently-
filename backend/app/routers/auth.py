"""Authentication endpoints: register, login, refresh, logout, profile, Google OAuth.

Rate limiting
-------------
``/register`` and ``/login`` are protected by a tiny in-process fixed-window
limiter (:func:`_rate_limit`). It is per-process only and resets on restart -
good enough to blunt credential-stuffing in a single-node dev/MVP setup.
TODO: replace with a Redis-backed limiter (e.g. slowapi / fastapi-limiter)
once the worker Redis instance is wired up - do not add the dep here.

Google OAuth callback
---------------------
``GET /auth/google/callback`` verifies the signed ``state`` (CSRF), exchanges
the code, provisions/links the user, then **redirects** (302) to
``{FRONTEND_URL}/auth/callback#access_token=...&refresh_token=...&token_type=bearer``.
Tokens are placed in the URL *fragment* so they are never sent to the server
or logged. The SPA reads ``window.location.hash`` and stores them.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.exceptions import UnauthorizedError, ValidationError
from app.models.user import User
from app.schemas.auth import (
    RefreshRequest,
    RegisterRequest,
    Token,
    UpdateProfileRequest,
    UserResponse,
)
from app.services import auth_service
from app.auth import oauth

logger = logging.getLogger("segmently.routers.auth")

router = APIRouter(prefix="/auth", tags=["auth"])

# --- Minimal in-process rate limiter -------------------------------------------------
_RATE_LIMIT_MAX = 10
_RATE_LIMIT_WINDOW_SECONDS = 60
_rate_buckets: dict[str, list[float]] = defaultdict(list)


def _rate_limit(request: Request, scope: str) -> None:
    """Raise 422 if ``scope`` has had too many hits from this client IP."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"{scope}:{client_ip}"
    now = time.monotonic()
    hits = [t for t in _rate_buckets[key] if now - t < _RATE_LIMIT_WINDOW_SECONDS]
    if len(hits) >= _RATE_LIMIT_MAX:
        logger.warning("Rate limit hit for %s", key)
        raise ValidationError("Too many attempts, please try again later")
    hits.append(now)
    _rate_buckets[key] = hits


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Create a new email/password account."""
    _rate_limit(request, "register")
    return auth_service.register_user(
        db,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
    )


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """Exchange email (``username``) + password for an access/refresh token pair."""
    _rate_limit(request, "login")
    return auth_service.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )


@router.post("/refresh", response_model=Token)
async def refresh(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
) -> Token:
    """Rotate a refresh token: revoke the old row, issue a new token pair."""
    return auth_service.rotate_refresh_token(db, payload.refresh_token)


@router.post("/logout", status_code=204)
async def logout(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
) -> None:
    """Revoke a refresh token."""
    auth_service.revoke_refresh_token(db, payload.refresh_token)


@router.get("/me", response_model=UserResponse)
async def read_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the current user's profile."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_me(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Update the current user's profile."""
    return auth_service.update_profile(
        db, current_user, full_name=payload.full_name
    )


@router.get("/google/login")
async def google_login() -> RedirectResponse:
    """Begin the Google OAuth flow (redirects to Google with a signed state)."""
    if not settings.GOOGLE_CLIENT_ID:
        raise ValidationError("Google OAuth is not configured")
    state = oauth.create_oauth_state()
    url = oauth.build_authorization_url(state)
    response = RedirectResponse(url, status_code=302)
    # Also drop the state in a short-lived cookie for defence in depth.
    response.set_cookie(
        "oauth_state",
        state,
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=not settings.FRONTEND_URL.startswith("http://localhost"),
    )
    return response


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Handle the Google redirect: verify state, exchange code, issue tokens."""
    if error:
        raise UnauthorizedError(f"Google OAuth error: {error}")
    if not code or not state:
        raise ValidationError("Missing code or state")

    cookie_state = request.cookies.get("oauth_state")
    if not oauth.verify_oauth_state(state) or (
        cookie_state is not None and cookie_state != state
    ):
        raise UnauthorizedError("Invalid OAuth state")

    try:
        token_data = await oauth.exchange_code_for_token(code)
        userinfo = await oauth.fetch_userinfo(token_data["access_token"])
    except (oauth.OAuthError, KeyError) as exc:
        logger.warning("Google OAuth exchange failed: %s", exc)
        raise UnauthorizedError("Google authentication failed") from exc

    sub = userinfo.get("sub")
    email = userinfo.get("email")
    if not sub or not email:
        raise UnauthorizedError("Google profile missing sub/email")

    _user, tokens = auth_service.get_or_create_google_user(
        db,
        sub=str(sub),
        email=str(email),
        full_name=userinfo.get("name"),
    )

    fragment = (
        f"access_token={tokens.access_token}"
        f"&refresh_token={tokens.refresh_token}"
        f"&token_type=bearer"
    )
    redirect_url = f"{settings.FRONTEND_URL}/auth/callback#{fragment}"
    response = RedirectResponse(redirect_url, status_code=302)
    response.delete_cookie("oauth_state")
    return response
