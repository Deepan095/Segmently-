"""Database engine, session factory, declarative Base and FastAPI dependency.

Follows skills/DATABASE.md. The connection URL is read from ``app.config.settings``
when the backend config module is available (owned by BACKEND-AGENT), otherwise it
falls back to the ``DATABASE_URL`` environment variable so this module and Alembic
can operate stand-alone.
"""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

_DEFAULT_URL = "postgresql://user:password@localhost:5432/segmently"

try:  # pragma: no cover - depends on BACKEND-AGENT's config module
    from app.config import settings  # type: ignore

    DATABASE_URL: str = settings.DATABASE_URL
except Exception:  # noqa: BLE001 - config module may not exist yet
    DATABASE_URL = os.getenv("DATABASE_URL", _DEFAULT_URL)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, future=True
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models (SQLAlchemy 2.0 style)."""


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and guarantee it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
