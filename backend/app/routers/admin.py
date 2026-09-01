"""Admin Panel endpoints (Module 5).

Every route in this router is gated by ``Depends(get_current_admin)`` at the
router level, so any authenticated non-admin gets a 403 and an unauthenticated
caller gets a 401 before the handler runs.

Routes (mounted under ``/api/v1``):
    GET  /admin/users            -> Page[AdminUserResponse]   (?q= search, ?page=&size=)
    PUT  /admin/users/{user_id}  -> AdminUserResponse
    GET  /admin/stats            -> PlatformStats
    GET  /admin/jobs             -> Page[AdminJobResponse]     (?status= filter, ?page=&size=)
    POST /admin/jobs/{job_id}/retry -> 202, AdminJobResponse
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_current_admin, get_db
from app.models.processing_job import JobStatus
from app.models.user import User
from app.schemas.admin import (
    AdminJobResponse,
    AdminUserResponse,
    AdminUserUpdateRequest,
    PlatformStats,
)
from app.schemas.common import Page, PaginationParams
from app.services import admin_service

logger = logging.getLogger("segmently.routers.admin")

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin)],
)


def _pagination(
    page: int = Query(default=1, ge=1, description="1-based page number"),
    size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> PaginationParams:
    return PaginationParams(page=page, size=size)


@router.get("/users", response_model=Page[AdminUserResponse])
async def list_users(
    q: str | None = Query(default=None, description="Search email / full name"),
    pagination: PaginationParams = Depends(_pagination),
    db: Session = Depends(get_db),
) -> Page[AdminUserResponse]:
    """List all users with per-user project/clip counts."""
    items, total = admin_service.list_users(db, q=q, pagination=pagination)
    return Page.create(items=items, total=total, params=pagination)


@router.put("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: int,
    patch: AdminUserUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> AdminUserResponse:
    """Update ``is_active`` / ``is_admin`` / ``is_verified`` on a user.

    An admin cannot strip their own ``is_admin`` flag (-> 409).
    """
    return admin_service.update_user(
        db, user_id=user_id, patch=patch, acting_admin_id=current_admin.id
    )


@router.get("/stats", response_model=PlatformStats)
async def platform_stats(db: Session = Depends(get_db)) -> PlatformStats:
    """Aggregate platform metrics for the admin dashboard."""
    return admin_service.get_platform_stats(db)


@router.get("/jobs", response_model=Page[AdminJobResponse])
async def list_jobs(
    status: JobStatus | None = Query(default=None, description="Filter by job status"),
    pagination: PaginationParams = Depends(_pagination),
    db: Session = Depends(get_db),
) -> Page[AdminJobResponse]:
    """Monitor processing jobs, newest first."""
    items, total = admin_service.list_jobs(db, status=status, pagination=pagination)
    return Page.create(items=items, total=total, params=pagination)


@router.post("/jobs/{job_id}/retry", status_code=202, response_model=AdminJobResponse)
async def retry_job(
    job_id: int,
    db: Session = Depends(get_db),
) -> AdminJobResponse:
    """Retry a failed job: reset it to ``queued`` and re-enqueue it."""
    return await admin_service.retry_job(db, job_id=job_id)
