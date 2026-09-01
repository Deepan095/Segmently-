"""Shared FastAPI dependencies.

The Auth module (Phase 2) wires the real JWT decode + user lookup logic
into :func:`get_current_user`; :func:`get_current_admin` builds on it.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.jwt import ACCESS_TOKEN_TYPE, decode_token
from app.exceptions import ForbiddenError, UnauthorizedError
from app.models.user import User

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger("segmently.dependencies")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_db() -> "Iterator[Any]":
    """Yield a database session.

    Re-exported from :mod:`app.database`, which is owned by DATABASE-AGENT.
    Falls back to a clear error until that module exists.
    """
    try:
        from app.database import get_db as _get_db
    except ImportError as exc:  # pragma: no cover - bootstrap only
        raise RuntimeError(
            "app.database.get_db is not available yet (DATABASE-AGENT owns it)."
        ) from exc
    yield from _get_db()


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Return the authenticated ``User`` for the bearer access token.

    Raises 401 if the token is missing, not an access token, expired, or the
    referenced user does not exist / is inactive.
    """
    if not token:
        raise UnauthorizedError("Not authenticated")

    payload = decode_token(token)
    if not payload or payload.get("type") != ACCESS_TOKEN_TYPE:
        raise UnauthorizedError("Invalid or expired token")

    subject = payload.get("sub")
    try:
        user_id = int(subject) if subject is not None else None
    except (TypeError, ValueError):
        user_id = None
    if user_id is None:
        raise UnauthorizedError("Invalid token subject")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    return user


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user, requiring ``is_admin``."""
    if not user.is_admin:
        raise ForbiddenError("Admin privileges required")
    return user
