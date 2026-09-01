"""Signed media-URL helpers.

Buckets are private; the app never exposes a raw storage URL. This module
re-exports the signed-URL helpers from :mod:`app.services.storage` and adds
small conveniences for building consistent storage keys.
"""

from __future__ import annotations

from app.config import settings
from app.services.storage import (
    generate_presigned_get,
    generate_presigned_put,
)

__all__ = [
    "generate_presigned_get",
    "generate_presigned_put",
    "signed_media_url",
    "source_key",
    "clip_key",
    "clip_thumbnail_key",
    "project_prefix",
]


def signed_media_url(key: str | None, expires: int | None = None) -> str | None:
    """Return a signed GET URL for *key*, or ``None`` when *key* is falsy."""
    if not key:
        return None
    return generate_presigned_get(key, expires or settings.SIGNED_URL_EXPIRE_SECONDS)


def project_prefix(project_id: int) -> str:
    """Root storage prefix for everything belonging to a project."""
    return f"projects/{project_id}/"


def source_key(project_id: int, ext: str = "mp4") -> str:
    """Storage key for a project's source video."""
    return f"{project_prefix(project_id)}source.{ext.lstrip('.')}"


def clip_key(project_id: int, clip_id: int, ext: str = "mp4") -> str:
    """Storage key for a rendered clip."""
    return f"{project_prefix(project_id)}clips/{clip_id}.{ext.lstrip('.')}"


def clip_thumbnail_key(project_id: int, clip_id: int) -> str:
    """Storage key for a clip's thumbnail image."""
    return f"{project_prefix(project_id)}clips/{clip_id}.jpg"
