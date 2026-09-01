"""Business logic for the Admin Panel module (Module 5).

Every function here assumes the caller has already been authorised as an
admin by the router-level ``Depends(get_current_admin)`` guard.

Queries are written to avoid N+1: user listings fold the per-user project
and clip counts into the same statement via grouped sub-queries, and the
platform stats are a handful of scalar aggregates.
"""

from __future__ import annotations

import inspect
import logging

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError
from app.models.clip import Clip
from app.models.processing_job import JobStatus, JobType, ProcessingJob
from app.models.project import Project
from app.models.user import User
from app.schemas.admin import (
    AdminJobResponse,
    AdminUserResponse,
    AdminUserUpdateRequest,
    PlatformStats,
)
from app.schemas.common import PaginationParams

logger = logging.getLogger("segmently.services.admin")


# --- helpers ----------------------------------------------------------------


def _serialize_user(
    user: User, projects_count: int, clips_count: int
) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_admin=user.is_admin,
        oauth_provider=user.oauth_provider,
        created_at=user.created_at,
        projects_count=projects_count,
        clips_count=clips_count,
    )


def _user_counts(db: Session, user_id: int) -> tuple[int, int]:
    """Return ``(projects_count, clips_count)`` for a single user."""
    projects_count = db.execute(
        select(func.count()).select_from(Project).where(Project.user_id == user_id)
    ).scalar_one()
    clips_count = db.execute(
        select(func.count()).select_from(Clip).where(Clip.user_id == user_id)
    ).scalar_one()
    return projects_count, clips_count


async def _enqueue_job(job: ProcessingJob) -> None:
    """Re-enqueue a job on the worker queue.

    The queue module is owned by the worker pipeline and may not exist yet,
    so the import is lazy and failure is non-fatal (the job row is already
    reset to ``queued`` in the DB, which the worker can pick up on its next
    sweep). TODO: remove the shim once ``app.workers.queue.enqueue`` lands.

    ``enqueue`` is currently an async coroutine; it is awaited here if so, but
    a plain-sync implementation is tolerated too.

    The worker registers tasks as ``run_download`` / ``run_transcribe`` /
    ``run_segment`` / ``run_render`` (not the bare ``JobType`` value). A render
    job carries only a ``project_id`` (no clip id on the row), so a render retry
    is re-driven from the idempotent ``run_segment`` stage, which recreates the
    clips and fans out fresh render jobs.
    """
    task_by_type = {
        JobType.download: "run_download",
        JobType.transcribe: "run_transcribe",
        JobType.segment: "run_segment",
        JobType.render: "run_segment",
    }
    task_name = task_by_type.get(job.job_type)
    if task_name is None:  # pragma: no cover - enum is exhaustive
        logger.error("Unknown job_type %s on job id=%s", job.job_type, job.id)
        return

    try:
        from app.workers.queue import enqueue  # type: ignore[import-not-found]
    except ImportError:
        logger.warning(
            "app.workers.queue.enqueue unavailable; job id=%s reset to 'queued' "
            "in DB only (worker will pick it up). TODO: wire the queue.",
            job.id,
        )
        return

    try:
        result = enqueue(task_name, job.project_id)
        if inspect.isawaitable(result):
            await result
    except Exception:  # noqa: BLE001 - queue outage must not fail the request
        logger.exception(
            "Failed to enqueue retried job id=%s; it stays 'queued' in the DB",
            job.id,
        )
        return
    logger.info("Re-enqueued job id=%s type=%s", job.id, job.job_type.value)


# --- users -----------------------------------------------------------------


def list_users(
    db: Session, q: str | None, pagination: PaginationParams
) -> tuple[list[AdminUserResponse], int]:
    """List users, newest first, with owned project/clip counts.

    ``q`` does a case-insensitive substring match on email and full name.
    """
    projects_subq = (
        select(Project.user_id, func.count(Project.id).label("cnt"))
        .group_by(Project.user_id)
        .subquery()
    )
    clips_subq = (
        select(Clip.user_id, func.count(Clip.id).label("cnt"))
        .group_by(Clip.user_id)
        .subquery()
    )

    stmt: Select = (
        select(
            User,
            func.coalesce(projects_subq.c.cnt, 0),
            func.coalesce(clips_subq.c.cnt, 0),
        )
        .outerjoin(projects_subq, projects_subq.c.user_id == User.id)
        .outerjoin(clips_subq, clips_subq.c.user_id == User.id)
    )

    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(User.email.ilike(pattern), User.full_name.ilike(pattern))
        )

    total = db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()

    rows = db.execute(
        stmt.order_by(User.created_at.desc(), User.id.desc())
        .offset(pagination.offset)
        .limit(pagination.limit)
    ).all()

    items = [
        _serialize_user(user, projects_count, clips_count)
        for user, projects_count, clips_count in rows
    ]
    return items, total


def update_user(
    db: Session,
    user_id: int,
    patch: AdminUserUpdateRequest,
    acting_admin_id: int,
) -> AdminUserResponse:
    """Apply a partial update to a user account.

    Guard: an admin may not remove their **own** ``is_admin`` flag. Attempting
    to do so raises :class:`ConflictError` (HTTP 409) and no change is made -
    this prevents an admin from accidentally locking every admin out.
    """
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User")

    if (
        patch.is_admin is False
        and user.id == acting_admin_id
    ):
        raise ConflictError("You cannot remove your own admin privileges")

    changed: list[str] = []
    if patch.is_active is not None and patch.is_active != user.is_active:
        user.is_active = patch.is_active
        changed.append("is_active")
    if patch.is_admin is not None and patch.is_admin != user.is_admin:
        user.is_admin = patch.is_admin
        changed.append("is_admin")
    if patch.is_verified is not None and patch.is_verified != user.is_verified:
        user.is_verified = patch.is_verified
        changed.append("is_verified")

    if changed:
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(
            "Admin id=%s updated user id=%s fields=%s",
            acting_admin_id,
            user.id,
            ",".join(changed),
        )

    projects_count, clips_count = _user_counts(db, user.id)
    return _serialize_user(user, projects_count, clips_count)


# --- stats ---------------------------------------------------------------


def get_platform_stats(db: Session) -> PlatformStats:
    """Compute aggregate platform metrics.

    ``storage_bytes_estimate`` sums ``Project.file_size_bytes`` over all
    projects (see :class:`PlatformStats` for the caveats).
    """
    users_total = db.execute(select(func.count()).select_from(User)).scalar_one()
    users_active = db.execute(
        select(func.count()).select_from(User).where(User.is_active.is_(True))
    ).scalar_one()
    projects_total = db.execute(
        select(func.count()).select_from(Project)
    ).scalar_one()
    clips_total = db.execute(select(func.count()).select_from(Clip)).scalar_one()
    storage_bytes_estimate = db.execute(
        select(func.coalesce(func.sum(Project.file_size_bytes), 0))
    ).scalar_one()
    jobs_failed = db.execute(
        select(func.count())
        .select_from(ProcessingJob)
        .where(ProcessingJob.status == JobStatus.failed)
    ).scalar_one()

    return PlatformStats(
        users_total=users_total,
        users_active=users_active,
        projects_total=projects_total,
        clips_total=clips_total,
        storage_bytes_estimate=int(storage_bytes_estimate or 0),
        jobs_failed=jobs_failed,
    )


# --- jobs --------------------------------------------------------------


def list_jobs(
    db: Session, status: JobStatus | None, pagination: PaginationParams
) -> tuple[list[AdminJobResponse], int]:
    """List processing jobs, newest first, optionally filtered by status."""
    stmt: Select = select(ProcessingJob)
    if status is not None:
        stmt = stmt.where(ProcessingJob.status == status)

    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one()

    rows = (
        db.execute(
            stmt.order_by(ProcessingJob.created_at.desc(), ProcessingJob.id.desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        .scalars()
        .all()
    )
    items = [AdminJobResponse.model_validate(job) for job in rows]
    return items, total


async def retry_job(db: Session, job_id: int) -> AdminJobResponse:
    """Reset a failed job to ``queued`` and re-enqueue it on the worker queue.

    Only jobs in the ``failed`` state can be retried; anything else raises
    :class:`ConflictError` (HTTP 409).
    """
    job = db.get(ProcessingJob, job_id)
    if job is None:
        raise NotFoundError("Job")

    if job.status != JobStatus.failed:
        raise ConflictError(
            f"Only failed jobs can be retried (job is '{job.status.value}')"
        )

    job.status = JobStatus.queued
    job.progress_pct = 0
    job.error_message = None
    job.started_at = None
    job.finished_at = None
    db.add(job)
    db.commit()
    db.refresh(job)

    await _enqueue_job(job)
    return AdminJobResponse.model_validate(job)
