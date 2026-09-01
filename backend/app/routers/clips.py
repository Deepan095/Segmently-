"""Clips module endpoints.

Routes are registered on a single prefix-less router (``main.py`` mounts it
under ``/api/v1``) so both the project-scoped list route and the flat
``/clips/{id}`` routes live together:

    GET    /api/v1/projects/{project_id}/clips   -> Page[ClipResponse]
    GET    /api/v1/clips/{id}                     -> ClipDetailResponse
    PUT    /api/v1/clips/{id}                     -> ClipResponse
    POST   /api/v1/clips/{id}/rerender            -> 202
    GET    /api/v1/clips/{id}/download            -> ClipDownloadResponse
    DELETE /api/v1/clips/{id}                     -> 204

Every handler depends on ``get_current_user`` and every lookup enforces the
owning user. Handlers do no heavy work - re-render is enqueued to the worker.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.clip import (
    ClipDetailResponse,
    ClipDownloadResponse,
    ClipResponse,
    ClipUpdateRequest,
)
from app.schemas.common import Page, PaginationParams
from app.services import clip_service

logger = logging.getLogger("segmently.routers.clips")

router = APIRouter(tags=["clips"])


@router.get("/projects/{project_id}/clips", response_model=Page[ClipResponse])
async def list_project_clips(
    project_id: int,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Page[ClipResponse]:
    """List the clips generated for a project the caller owns."""
    params = PaginationParams(page=page, size=size)
    return clip_service.list_for_project(db, project_id, current_user.id, params)


@router.get("/clips/{clip_id}", response_model=ClipDetailResponse)
async def get_clip(
    clip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClipDetailResponse:
    """Return full detail for a clip, including caption segments."""
    return clip_service.get_for_user(db, clip_id, current_user.id)


@router.put("/clips/{clip_id}", response_model=ClipResponse)
async def update_clip(
    clip_id: int,
    payload: ClipUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClipResponse:
    """Update title, trim points, caption text or caption style.

    Trim / caption edits move the clip back to ``queued``; call the rerender
    endpoint to regenerate the MP4.
    """
    return await clip_service.update_for_user(db, clip_id, current_user.id, payload)


@router.post(
    "/clips/{clip_id}/rerender",
    status_code=status.HTTP_202_ACCEPTED,
)
async def rerender_clip(
    clip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Queue a re-render of the clip after edits."""
    await clip_service.rerender_for_user(db, clip_id, current_user.id)
    return {"status": "queued", "message": "Re-render has been queued"}


@router.get("/clips/{clip_id}/download", response_model=ClipDownloadResponse)
async def download_clip(
    clip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClipDownloadResponse:
    """Return a short-lived signed URL for the rendered MP4 (409 if not ready)."""
    return clip_service.download_url_for_user(db, clip_id, current_user.id)


@router.delete("/clips/{clip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clip(
    clip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a clip and its stored media."""
    clip_service.delete_for_user(db, clip_id, current_user.id)
