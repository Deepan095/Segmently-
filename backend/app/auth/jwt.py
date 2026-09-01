"""JWT creation / decoding and password hashing.

Uses passlib (bcrypt) for password hashing and python-jose for JWT.
Never hardcode secrets - all values come from ``app.config.settings``.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

logger = logging.getLogger("segmently.auth.jwt")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def hash_password(password: str) -> str:
    """Return a bcrypt hash for ``password``."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return ``True`` if ``plain_password`` matches ``hashed_password``."""
    if not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:  # pragma: no cover - malformed hash
        logger.warning("verify_password called with a malformed hash")
        return False


def _create_token(data: dict[str, Any], expires_delta: timedelta, token_type: str) -> str:
    to_encode: dict[str, Any] = dict(data)
    now = datetime.now(timezone.utc)
    to_encode.update(
        {
            "exp": now + expires_delta,
            "iat": now,
            "type": token_type,
            # Unique token id: without it, two tokens minted in the same second
            # with the same payload are byte-identical, which collides with the
            # UNIQUE constraint on ``refresh_tokens.token`` (e.g. rapid refresh).
            "jti": secrets.token_urlsafe(16),
        }
    )
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Create a signed JWT access token with a ``type=access`` claim."""
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token(data, delta, ACCESS_TOKEN_TYPE)


def create_refresh_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Create a signed JWT refresh token with a ``type=refresh`` claim."""
    delta = expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token(data, delta, REFRESH_TOKEN_TYPE)


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode / verify a JWT. Returns the claims dict or ``None`` if invalid."""
    try:
        return jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError as exc:
        logger.debug("Token decode failed: %s", exc)
        return None
