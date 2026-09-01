"""Business logic for authentication: registration, login, token rotation, OAuth."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.jwt import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.config import settings
from app.exceptions import ConflictError, UnauthorizedError
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import Token

logger = logging.getLogger("segmently.services.auth")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _persist_refresh_token(db: Session, user: User, token: str) -> RefreshToken:
    expires_at = _now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    row = RefreshToken(user_id=user.id, token=token, expires_at=expires_at)
    db.add(row)
    return row


def _issue_token_pair(db: Session, user: User) -> Token:
    """Mint an access + refresh token pair and store the refresh token row."""
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    _persist_refresh_token(db, user, refresh_token)
    db.commit()
    return Token(access_token=access_token, refresh_token=refresh_token)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.execute(
        select(User).where(User.email == email.lower())
    ).scalar_one_or_none()


def register_user(
    db: Session, email: str, password: str, full_name: str | None = None
) -> User:
    """Create a new email/password user. Raises :class:`ConflictError` on dupes."""
    if get_user_by_email(db, email):
        raise ConflictError("An account with this email already exists")

    user = User(
        email=email.lower(),
        hashed_password=hash_password(password),
        full_name=full_name,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Registered new user id=%s", user.id)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Token:
    """Verify credentials and return a fresh token pair."""
    user = get_user_by_email(db, email)
    if not user or not user.hashed_password:
        raise UnauthorizedError("Incorrect email or password")
    if not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Incorrect email or password")
    if not user.is_active:
        raise UnauthorizedError("Account is disabled")
    return _issue_token_pair(db, user)


def rotate_refresh_token(db: Session, refresh_token: str) -> Token:
    """Validate a refresh token, revoke it, and issue a new token pair."""
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != REFRESH_TOKEN_TYPE:
        raise UnauthorizedError("Invalid refresh token")

    row = db.execute(
        select(RefreshToken).where(RefreshToken.token == refresh_token)
    ).scalar_one_or_none()
    if row is None or row.revoked:
        raise UnauthorizedError("Refresh token has been revoked")

    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < _now():
        raise UnauthorizedError("Refresh token has expired")

    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User is inactive")

    row.revoked = True
    db.add(row)
    return _issue_token_pair(db, user)


def revoke_refresh_token(db: Session, refresh_token: str) -> None:
    """Mark a refresh token row revoked. Idempotent / silent if unknown."""
    row = db.execute(
        select(RefreshToken).where(RefreshToken.token == refresh_token)
    ).scalar_one_or_none()
    if row is None:
        logger.info("logout: refresh token not found (already gone)")
        return
    row.revoked = True
    db.add(row)
    db.commit()


def get_or_create_google_user(
    db: Session, *, sub: str, email: str, full_name: str | None
) -> tuple[User, Token]:
    """Find or provision a user for a verified Google identity."""
    user = db.execute(
        select(User).where(
            User.oauth_provider == "google", User.oauth_sub == sub
        )
    ).scalar_one_or_none()

    if user is None:
        user = get_user_by_email(db, email)
        if user is not None:
            # Link Google to an existing email/password account.
            user.oauth_provider = "google"
            user.oauth_sub = sub
            user.is_verified = True
        else:
            user = User(
                email=email.lower(),
                hashed_password=None,
                full_name=full_name,
                is_active=True,
                is_verified=True,
                oauth_provider="google",
                oauth_sub=sub,
            )
            db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Provisioned Google user id=%s", user.id)

    if not user.is_active:
        raise UnauthorizedError("Account is disabled")

    return user, _issue_token_pair(db, user)


def update_profile(
    db: Session, user: User, *, full_name: str | None
) -> User:
    """Update mutable profile fields on ``user``."""
    if full_name is not None:
        user.full_name = full_name
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
