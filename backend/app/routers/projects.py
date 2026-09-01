"""Projects / Uploads API.

All endpoints require authentication and enforce per-user ownership.
Heavy work (download, transcribe, segment, render) is always enqueued -
never run in a request handler.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.common import Message, Page, PaginationParams
from app.schemas.project import (
    JobResponse,
    ProjectCreateFromUrl,
    ProjectDetailResponse,
    ProjectResponse,
    TranscriptResponse,
    UploadInitRequest,
    UploadInitResponse,
)
from app.services import project_service

logger = logging.getLogger("segmently.routers.projects")

router = APIRouter(prefix="/projects", tags=["projects"])


def _pagination(page: int = 1, size: int = 20) -> PaginationParams:
    return PaginationParams(page=page, size=size)


@router.get("", response_model=Page[ProjectResponse])
async def list_projects(
    params: PaginationParams = Depends(_pagination),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[ProjectResponse]:
    """List the current user's projects (paginated, newest first)."""
    page = project_service.list_for_user(db, current_user, params)
    return Page[ProjectResponse].create(
        [ProjectResponse(**project_service.to_response_dict(p)) for p in page.items],
        page.total,
        params,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_project_from_url(
    payload: ProjectCreateFromUrl,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    """Create a project from a pasted URL and enqueue the download stage (202)."""
    project = await project_service.create_from_url(
        db, current_user, url=payload.url, title=payload.title
    )
    return ProjectResponse(**project_service.to_response_dict(project))


@router.post(
    "/upload",
    response_model=ProjectResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_project(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    """Create a project via a direct multipart file upload (202).

    For large files prefer ``POST /projects/upload/init`` (presigned PUT).
    """
    data = await file.read()
    project = await project_service.store_uploaded_file(
        db,
        current_user,
        filename=file.filename or "upload.mp4",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        title=title,
    )
    return ProjectResponse(**project_service.to_response_dict(project))


@router.post(
    "/upload/init",
    response_model=UploadInitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def init_presigned_upload(
    payload: UploadInitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UploadInitResponse:
    """Create the project row and return a presigned direct-to-storage PUT URL."""
    project, upload_url, key, expires = project_service.create_from_upload(
        db,
        current_user,
        filename=payload.filename,
        content_type=payload.content_type,
        file_size_bytes=payload.file_size_bytes,
        title=payload.title,
    )
    return UploadInitResponse(
        project_id=project.id,
        upload_url=upload_url,
        storage_key=key,
        expires_in=expires,
    )


@router.post(
    "/{project_id}/upload/complete",
    response_model=ProjectResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def complete_presigned_upload(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    """Signal that a presigned PUT finished; verify the object and start the pipeline."""
    project = await project_service.mark_upload_complete(db, current_user, project_id)
    return ProjectResponse(**project_service.to_response_dict(project))


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectDetailResponse:
    """Project detail including pipeline job progress and clip count."""
    project = project_service.get_detail_for_user(db, current_user, project_id)
    data = project_service.to_response_dict(project)
    return ProjectDetailResponse(
        **data,
        jobs=[JobResponse.model_validate(j) for j in project.jobs],
        clips_count=project_service.clips_count(db, project.id),
        has_transcript=_has_transcript(db, project.id),
    )


def _has_transcript(db: Session, project_id: int) -> bool:
    from sqlalchemy import func, select

    from app.models.transcript import Transcript

    return bool(
        db.scalar(
            select(func.count())
            .select_from(Transcript)
            .where(Transcript.project_id == project_id)
        )
    )


@router.delete("/{project_id}", response_model=Message)
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Message:
    """Delete a project, its clips/transcript/jobs, and all stored media."""
    project_service.delete_for_user(db, current_user, project_id)
    return Message(message="Project deleted")


@router.post(
    "/{project_id}/reprocess",
    response_model=ProjectResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reprocess_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    """Re-run the pipeline for a project (202)."""
    project = await project_service.reprocess(db, current_user, project_id)
    return ProjectResponse(**project_service.to_response_dict(project))


@router.get("/{project_id}/transcript", response_model=TranscriptResponse)
async def get_project_transcript(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TranscriptResponse:
    """Return the project's transcript (404 until transcription completes)."""
    transcript = project_service.get_transcript(db, current_user, project_id)
    return TranscriptResponse.model_validate(transcript)
