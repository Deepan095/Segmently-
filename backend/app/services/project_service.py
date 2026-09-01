"""Business logic for the Projects / Uploads module.

Request handlers call into here; the heavy pipeline work is always
*enqueued* (arq), never executed inline.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.exceptions import NotFoundError, ValidationError
from app.models.clip import Clip
from app.models.processing_job import ProcessingJob
from app.models.project import Project, ProjectStatus, SourceType
from app.models.transcript import Transcript
from app.models.user import User
from app.schemas.common import Page, PaginationParams
from app.services import storage
from app.services.media_url import project_prefix, signed_media_url, source_key
from app.services.ssrf import validate_public_url
from app.workers.queue import enqueue

logger = logging.getLogger("segmently.services.project")


def _title_from_url(url: str) -> str:
    tail = url.rstrip("/").split("/")[-1] or url
    return (tail.split("?")[0] or "Imported video")[:255]


def _ext_from_filename(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    return ext or "mp4"


def to_response_dict(project: Project) -> dict[str, Any]:
    """Serialise a project with a signed thumbnail URL (never a raw key)."""
    return {
        "id": project.id,
        "title": project.title,
        "source_type": project.source_type.value
        if hasattr(project.source_type, "value")
        else str(project.source_type),
        "source_url": project.source_url,
        "status": project.status.value
        if hasattr(project.status, "value")
        else str(project.status),
        "duration_seconds": project.duration_seconds,
        "file_size_bytes": project.file_size_bytes,
        "error_message": project.error_message,
        "thumbnail_url": signed_media_url(project.thumbnail_key),
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


async def create_from_url(db: Session, user: User, *, url: str, title: str | None) -> Project:
    """Create a URL-import project and enqueue the download stage."""
    validate_public_url(url)  # defence in depth - schema already checked it
    project = Project(
        user_id=user.id,
        title=title or _title_from_url(url),
        source_type=SourceType.url,
        source_url=url,
        status=ProjectStatus.pending,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    logger.info("Created URL project %s for user %s", project.id, user.id)
    await enqueue("run_download", project.id)
    return project


def create_from_upload(
    db: Session,
    user: User,
    *,
    filename: str,
    content_type: str,
    file_size_bytes: int,
    title: str | None,
) -> tuple[Project, str, str, int]:
    """Create an upload project and return a presigned PUT URL.

    Returns ``(project, upload_url, storage_key, expires_in)``. The client
    PUTs the file directly to storage, then calls
    ``POST /projects/{id}/reprocess`` (or the pipeline auto-starts on the
    storage event) - for the MVP the frontend calls the complete endpoint.
    """
    if content_type not in settings.ALLOWED_UPLOAD_CONTENT_TYPES:
        raise ValidationError(f"Unsupported content type: {content_type}")
    if file_size_bytes > settings.MAX_UPLOAD_BYTES:
        raise ValidationError("File exceeds the maximum allowed size")

    project = Project(
        user_id=user.id,
        title=title or os.path.splitext(filename)[0][:255] or "Uploaded video",
        source_type=SourceType.upload,
        status=ProjectStatus.pending,
        file_size_bytes=file_size_bytes,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    key = source_key(project.id, _ext_from_filename(filename))
    project.storage_key = key
    db.commit()
    db.refresh(project)

    expires = settings.SIGNED_URL_EXPIRE_SECONDS
    upload_url = storage.generate_presigned_put(
        key, expires=expires, content_type=content_type
    )
    logger.info("Created upload project %s for user %s", project.id, user.id)
    return project, upload_url, key, expires


async def store_uploaded_file(
    db: Session,
    user: User,
    *,
    filename: str,
    content_type: str,
    data: bytes,
    title: str | None,
) -> Project:
    """Handle a small multipart upload: store bytes, then enqueue the pipeline."""
    if content_type not in settings.ALLOWED_UPLOAD_CONTENT_TYPES:
        raise ValidationError(f"Unsupported content type: {content_type}")
    if len(data) > settings.MAX_UPLOAD_BYTES:
        raise ValidationError("File exceeds the maximum allowed size")

    project = Project(
        user_id=user.id,
        title=title or os.path.splitext(filename)[0][:255] or "Uploaded video",
        source_type=SourceType.upload,
        status=ProjectStatus.pending,
        file_size_bytes=len(data),
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    key = source_key(project.id, _ext_from_filename(filename))
    storage.put_object(key, data, content_type=content_type)
    project.storage_key = key
    db.commit()
    db.refresh(project)

    # Upload already in storage - skip download, go straight to transcription.
    await enqueue("run_transcribe", project.id)
    return project


async def mark_upload_complete(db: Session, user: User, project_id: int) -> Project:
    """Client finished a presigned PUT - verify the object and start the pipeline."""
    project = get_for_user(db, user, project_id)
    if project.source_type != SourceType.upload or not project.storage_key:
        raise ValidationError("Project is not a pending upload")
    if not storage.object_exists(project.storage_key):
        raise ValidationError("Uploaded object not found in storage")
    project.status = ProjectStatus.pending
    project.error_message = None
    db.commit()
    db.refresh(project)
    await enqueue("run_transcribe", project.id)
    return project


def list_for_user(db: Session, user: User, params: PaginationParams) -> Page[Project]:
    """Return a page of the user's own projects, newest first."""
    base = select(Project).where(Project.user_id == user.id)
    total = db.scalar(
        select(func.count()).select_from(base.subquery())
    ) or 0
    rows = (
        db.execute(
            base.order_by(Project.created_at.desc())
            .offset(params.offset)
            .limit(params.limit)
        )
        .scalars()
        .all()
    )
    return Page.create(list(rows), total, params)


def get_for_user(db: Session, user: User, project_id: int) -> Project:
    """Return the project, or raise 404 (missing) / 403 (not owner)."""
    project = db.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project")
    if project.user_id != user.id:
        # 404 rather than 403 - don't leak the existence of other users' projects
        # (matches the Clips module's ownership convention).
        raise NotFoundError("Project")
    return project


def get_detail_for_user(db: Session, user: User, project_id: int) -> Project:
    """Like :func:`get_for_user` but eager-loads jobs for the detail view."""
    project = db.get(
        Project,
        project_id,
        options=[selectinload(Project.jobs)],
    )
    if project is None:
        raise NotFoundError("Project")
    if project.user_id != user.id:
        raise NotFoundError("Project")
    return project


def clips_count(db: Session, project_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(Clip).where(Clip.project_id == project_id)
    ) or 0


def get_transcript(db: Session, user: User, project_id: int) -> Transcript:
    """Return the transcript for a project the user owns, or 404."""
    get_for_user(db, user, project_id)  # ownership check
    transcript = db.scalar(
        select(Transcript).where(Transcript.project_id == project_id)
    )
    if transcript is None:
        raise NotFoundError("Transcript")
    return transcript


def delete_for_user(db: Session, user: User, project_id: int) -> None:
    """Delete a project, its DB children (cascade), and all stored media."""
    project = get_for_user(db, user, project_id)
    prefix = project_prefix(project.id)
    try:
        removed = storage.delete_prefix(prefix)
        logger.info("Deleted %d storage objects for project %s", removed, project.id)
    except storage.StorageError as exc:  # noqa: BLE001 - don't block DB delete
        logger.error("Storage cleanup failed for project %s: %s", project.id, exc)
    db.delete(project)  # ORM cascade removes transcript, jobs, clips, captions
    db.commit()


async def reprocess(db: Session, user: User, project_id: int) -> Project:
    """Reset a project and re-run the pipeline from the appropriate stage."""
    project = get_for_user(db, user, project_id)

    # Clear previous derived data so the run is idempotent.
    db.query(ProcessingJob).filter(ProcessingJob.project_id == project.id).delete()
    db.query(Clip).filter(Clip.project_id == project.id).delete()
    transcript = db.scalar(
        select(Transcript).where(Transcript.project_id == project.id)
    )
    if transcript is not None:
        db.delete(transcript)

    project.status = ProjectStatus.pending
    project.error_message = None
    db.commit()
    db.refresh(project)

    if project.source_type == SourceType.url and not project.storage_key:
        await enqueue("run_download", project.id)
    else:
        await enqueue("run_transcribe", project.id)
    return project
