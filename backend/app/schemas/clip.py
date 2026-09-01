"""Pydantic schemas for the Clips module."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CaptionSegment(BaseModel):
    """A single timed caption line, relative to the clip start."""

    start: float = Field(ge=0, description="Seconds from clip start")
    end: float = Field(ge=0, description="Seconds from clip start")
    text: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def _end_after_start(self) -> "CaptionSegment":
        if self.end < self.start:
            raise ValueError("caption segment end must be >= start")
        return self


class ClipResponse(BaseModel):
    """Summary view of a clip (list rows, update result)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    aspect_ratio: str
    status: str
    score: int
    score_reason: str | None = None
    thumbnail_url: str | None = None
    created_at: datetime


class ClipDetailResponse(ClipResponse):
    """Full view of a clip including caption segments and a download hint."""

    caption_segments: list[CaptionSegment] = Field(default_factory=list)
    caption_style: dict[str, Any] | None = None
    caption_edited: bool = False
    download_available: bool = False
    download_hint: str


class ClipUpdateRequest(BaseModel):
    """Editable fields on a clip. All optional - only provided fields change."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    start_seconds: float | None = Field(default=None, ge=0)
    end_seconds: float | None = Field(default=None, ge=0)
    caption_segments: list[CaptionSegment] | None = None
    caption_style: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _trim_consistent(self) -> "ClipUpdateRequest":
        if (
            self.start_seconds is not None
            and self.end_seconds is not None
            and self.end_seconds <= self.start_seconds
        ):
            raise ValueError("end_seconds must be greater than start_seconds")
        return self


class ClipDownloadResponse(BaseModel):
    """A short-lived signed URL for downloading the rendered MP4."""

    url: str
    expires_at: datetime
