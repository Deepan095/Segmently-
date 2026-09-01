"""Idempotent admin-user seeding.

Creates (or repairs) a single admin account from ``settings.ADMIN_EMAIL`` /
``settings.ADMIN_PASSWORD``. Safe to call repeatedly.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.jwt import hash_password
from app.config import settings
from app.models.user import User

logger = logging.getLogger("segmently.auth.seed")


def seed_admin(db: Session) -> User:
    """Ensure an active, verified admin user exists. Returns that user."""
    email = settings.ADMIN_EMAIL.lower()
    user = db.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            hashed_password=hash_password(settings.ADMIN_PASSWORD),
            full_name="Administrator",
            is_active=True,
            is_verified=True,
            is_admin=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Seeded admin user %s (id=%s)", email, user.id)
        return user

    changed = False
    if not user.is_admin:
        user.is_admin = True
        changed = True
    if not user.is_active:
        user.is_active = True
        changed = True
    if not user.is_verified:
        user.is_verified = True
        changed = True
    if changed:
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Repaired admin flags on existing user %s", email)
    else:
        logger.info("Admin user %s already present", email)
    return user
