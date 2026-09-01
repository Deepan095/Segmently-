"""Pydantic schemas for the Projects / Uploads module."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.ssrf import validate_public_url


class ProjectCreateFromUrl(BaseModel):
    """Payload for ``POST /projects`` - create a project from a pasted URL."""

    url: str = Field(min_length=8, max_length=2048)
    title: str | None = Field(default=None, max_length=255)

    @field_validator("url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        # SSRF guard runs before we ever persist or fetch the URL.
        return validate_public_url(value)


class UploadInitRequest(BaseModel):
    """Payload for ``POST /projects/upload`` when requesting a presigned PUT."""

    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=3, max_length=128)
    file_size_bytes: int = Field(gt=0)
    title: str | None = Field(default=None, max_length=255)


class UploadInitResponse(BaseModel):
    """Presigned direct-to-storage upload instructions."""

    project_id: int
    upload_url: str
    storage_key: str
    expires_in: int
    method: Literal["PUT"] = "PUT"


class JobResponse(BaseModel):
    """A single pipeline-stage job."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    job_type: str
    status: str
    progress_pct: int
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime


class ProjectResponse(BaseModel):
    """List/summary representation of a project."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source_type: str
    source_url: str | None = None
    status: str
    duration_seconds: float | None = None
    file_size_bytes: int | None = None
    error_message: str | None = None
    thumbnail_url: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class ProjectDetailResponse(ProjectResponse):
    """Detail representation: adds pipeline jobs and a clip count."""

    jobs: list[JobResponse] = Field(default_factory=list)
    clips_count: int = 0
    has_transcript: bool = False


class TranscriptResponse(BaseModel):
    """Full transcript payload."""

    model_config = ConfigDict(from_attributes=True)

    project_id: int
    language: str | None = None
    full_text: str
    segments: list[dict[str, Any]] | None = None
    created_at: datetime
