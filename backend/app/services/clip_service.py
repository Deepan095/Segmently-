"""Business logic for the Clips module.

Ownership is enforced on every lookup: a clip is only visible to the user
that owns its parent :class:`~app.models.project.Project` (``Project.user_id``).

External collaborators (owned by the Projects agent, may land moments later):

* ``app.services.storage.generate_presigned_get(key, expires)`` - signed GETs
* ``app.workers.queue.enqueue("run_render", clip_id)`` - trigger a re-render

Both are imported lazily inside the functions that need them so this module
still imports cleanly if those files are not present yet.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError
from app.models.clip import Clip, ClipStatus
from app.models.clip_caption import ClipCaption
from app.models.project import Project
from app.schemas.clip import (
    CaptionSegment,
    ClipDetailResponse,
    ClipDownloadResponse,
    ClipResponse,
    ClipUpdateRequest,
)
from app.schemas.common import Page, PaginationParams

logger = logging.getLogger("segmently.services.clip")

_DOWNLOAD_URL_TTL_SECONDS = 900
_THUMBNAIL_URL_TTL_SECONDS = 3600


# --- External collaborator shims -------------------------------------------------

def _presigned_get(key: str | None, expires: int) -> str | None:
    """Return a signed GET URL for ``key`` or ``None`` if unavailable.

    TODO(projects-agent): remove the fallback once ``app.services.storage``
    is guaranteed to exist. Until then a missing module is logged and treated
    as "no URL available".
    """
    if not key:
        return None
    try:
        from app.services.storage import generate_presigned_get
    except ImportError:
        logger.warning(
            "app.services.storage not available yet - cannot sign key %s", key
        )
        return None
    return generate_presigned_get(key, expires)


async def _enqueue_render(clip_id: int) -> bool:
    """Enqueue a ``run_render`` job for ``clip_id``. Returns ``True`` if queued."""
    try:
        from app.workers.queue import enqueue
    except ImportError:
        logger.warning(
            "app.workers.queue not available yet - render for clip %s not enqueued",
            clip_id,
        )
        return False
    try:
        await enqueue("run_render", clip_id)
    except Exception:  # noqa: BLE001 - a queue outage must not fail the request
        logger.exception("Failed to enqueue render for clip %s", clip_id)
        return False
    return True


def _delete_storage_key(key: str | None) -> None:
    """Best-effort delete of a stored object. Never raises."""
    if not key:
        return
    try:
        from app.services.storage import delete_key as delete_object
    except ImportError:
        logger.warning(
            "app.services.storage not available yet - orphaned key %s", key
        )
        return
    try:
        delete_object(key)
    except Exception:  # noqa: BLE001 - cleanup must not break the request
        logger.exception("Failed to delete storage key %s", key)


# --- Lookups -------------------------------------------------------------------

def _get_owned_clip(db: Session, clip_id: int, user_id: int) -> Clip:
    """Fetch a clip that belongs to ``user_id`` (via its project) or 404."""
    clip = db.execute(
        select(Clip)
        .join(Project, Clip.project_id == Project.id)
        .where(Clip.id == clip_id, Project.user_id == user_id)
    ).scalar_one_or_none()
    if clip is None:
        raise NotFoundError("Clip")
    return clip


def _get_owned_project(db: Session, project_id: int, user_id: int) -> Project:
    project = db.execute(
        select(Project).where(
            Project.id == project_id, Project.user_id == user_id
        )
    ).scalar_one_or_none()
    if project is None:
        raise NotFoundError("Project")
    return project


# --- Serialisation ------------------------------------------------------------

def _caption_segments(clip: Clip) -> list[CaptionSegment]:
    raw = clip.caption.segments if clip.caption else None
    if not raw:
        return []
    return [CaptionSegment.model_validate(seg) for seg in raw]


def _to_response(clip: Clip) -> ClipResponse:
    return ClipResponse(
        id=clip.id,
        project_id=clip.project_id,
        title=clip.title,
        start_seconds=clip.start_seconds,
        end_seconds=clip.end_seconds,
        duration_seconds=clip.duration_seconds,
        aspect_ratio=clip.aspect_ratio,
        status=clip.status.value if hasattr(clip.status, "value") else str(clip.status),
        score=clip.score,
        score_reason=clip.score_reason,
        thumbnail_url=_presigned_get(clip.thumbnail_key, _THUMBNAIL_URL_TTL_SECONDS),
        created_at=clip.created_at,
    )


def _to_detail(clip: Clip) -> ClipDetailResponse:
    base = _to_response(clip)
    is_ready = clip.status == ClipStatus.ready and bool(clip.storage_key)
    if is_ready:
        hint = "Call GET /api/v1/clips/{id}/download for a signed MP4 URL."
    elif clip.status == ClipStatus.failed:
        hint = "Rendering failed. Edit the clip or POST /clips/{id}/rerender to retry."
    else:
        hint = "Clip is not rendered yet. Poll until status is 'ready'."
    return ClipDetailResponse(
        **base.model_dump(),
        caption_segments=_caption_segments(clip),
        caption_style=clip.caption_style,
        caption_edited=bool(clip.caption and clip.caption.edited),
        download_available=is_ready,
        download_hint=hint,
    )


# --- Public API --------------------------------------------------------------

def list_for_project(
    db: Session, project_id: int, user_id: int, params: PaginationParams
) -> Page[ClipResponse]:
    """List clips for a project the caller owns, highest score first."""
    _get_owned_project(db, project_id, user_id)

    total = db.execute(
        select(func.count())
        .select_from(Clip)
        .where(Clip.project_id == project_id)
    ).scalar_one()

    rows = (
        db.execute(
            select(Clip)
            .where(Clip.project_id == project_id)
            .order_by(Clip.score.desc(), Clip.start_seconds.asc())
            .offset(params.offset)
            .limit(params.limit)
        )
        .scalars()
        .all()
    )
    items = [_to_response(clip) for clip in rows]
    return Page.create(items=items, total=total, params=params)


def get_for_user(db: Session, clip_id: int, user_id: int) -> ClipDetailResponse:
    """Return the full clip detail for a clip the caller owns."""
    clip = _get_owned_clip(db, clip_id, user_id)
    return _to_detail(clip)


async def update_for_user(
    db: Session, clip_id: int, user_id: int, payload: ClipUpdateRequest
) -> ClipResponse:
    """Apply edits to a clip.

    Any edit to the trim points, caption text or caption style invalidates the
    rendered output: the clip is moved back to ``queued`` so a re-render can be
    triggered. Caption text edits also flag ``ClipCaption.edited``.
    """
    clip = _get_owned_clip(db, clip_id, user_id)
    needs_rerender = False

    if payload.title is not None:
        clip.title = payload.title

    new_start = payload.start_seconds if payload.start_seconds is not None else clip.start_seconds
    new_end = payload.end_seconds if payload.end_seconds is not None else clip.end_seconds
    if payload.start_seconds is not None or payload.end_seconds is not None:
        if new_end <= new_start:
            raise ConflictError("end_seconds must be greater than start_seconds")
        clip.start_seconds = new_start
        clip.end_seconds = new_end
        clip.duration_seconds = round(new_end - new_start, 3)
        needs_rerender = True

    if payload.caption_style is not None:
        clip.caption_style = payload.caption_style
        needs_rerender = True

    if payload.caption_segments is not None:
        segments = [seg.model_dump() for seg in payload.caption_segments]
        if clip.caption is None:
            clip.caption = ClipCaption(segments=segments, edited=True)
        else:
            clip.caption.segments = segments
            clip.caption.edited = True
        needs_rerender = True

    if needs_rerender:
        clip.status = ClipStatus.queued

    db.add(clip)
    db.commit()
    db.refresh(clip)
    if needs_rerender:
        await _enqueue_render(clip.id)
    logger.info(
        "Updated clip id=%s user=%s rerender_needed=%s", clip.id, user_id, needs_rerender
    )
    return _to_response(clip)


async def rerender_for_user(db: Session, clip_id: int, user_id: int) -> None:
    """Queue a re-render for a clip the caller owns."""
    clip = _get_owned_clip(db, clip_id, user_id)
    clip.status = ClipStatus.queued
    db.add(clip)
    db.commit()
    queued = await _enqueue_render(clip.id)
    logger.info(
        "Re-render requested clip id=%s user=%s enqueued=%s", clip.id, user_id, queued
    )


def download_url_for_user(
    db: Session, clip_id: int, user_id: int
) -> ClipDownloadResponse:
    """Return a signed, expiring MP4 download URL for a ready clip."""
    clip = _get_owned_clip(db, clip_id, user_id)
    if clip.status != ClipStatus.ready or not clip.storage_key:
        raise ConflictError("Clip is not ready for download yet")

    url = _presigned_get(clip.storage_key, _DOWNLOAD_URL_TTL_SECONDS)
    if url is None:
        raise ConflictError("Download is temporarily unavailable")

    expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=_DOWNLOAD_URL_TTL_SECONDS
    )
    logger.info("Issued download URL for clip id=%s user=%s", clip.id, user_id)
    return ClipDownloadResponse(url=url, expires_at=expires_at)


def delete_for_user(db: Session, clip_id: int, user_id: int) -> None:
    """Delete a clip the caller owns along with its stored media."""
    clip = _get_owned_clip(db, clip_id, user_id)
    storage_key = clip.storage_key
    thumbnail_key = clip.thumbnail_key

    db.delete(clip)
    db.commit()

    _delete_storage_key(storage_key)
    _delete_storage_key(thumbnail_key)
    logger.info("Deleted clip id=%s user=%s", clip_id, user_id)
