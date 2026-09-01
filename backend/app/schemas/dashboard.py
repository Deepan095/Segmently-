"""Pydantic schemas for the analytics dashboard module (Module 4)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

UsageRange = Literal["7d", "30d", "90d"]


class SummaryResponse(BaseModel):
    """Lifetime totals for the current user, shown as dashboard stat cards."""

    minutes_uploaded: float = Field(
        ge=0, description="Sum of Project.duration_seconds / 60 across the user's projects"
    )
    projects_total: int = Field(ge=0)
    projects_completed: int = Field(ge=0)
    clips_generated: int = Field(ge=0)
    clips_downloaded: int = Field(
        ge=0,
        description="Proxy: count of clips with status 'ready' (no download-event table in MVP)",
    )


class UsagePoint(BaseModel):
    """One calendar day of activity."""

    date: date
    minutes_processed: float = Field(ge=0)
    clips_generated: int = Field(ge=0)


class UsageResponse(BaseModel):
    """Daily time series over the requested range (gaps filled with zeros)."""

    range: UsageRange
    points: list[UsagePoint]


class TopClip(BaseModel):
    """A high-scoring clip for the "Top Clips" panel."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    score: int = Field(ge=0, le=100)
    project_id: int
    thumbnail_url: str | None = None


class SettingsResponse(BaseModel):
    """Minimal settings view.

    Profile writes are delegated to ``PUT /api/v1/auth/me`` (Auth module owns the
    ``User`` write path); this schema only echoes the current display name.
    """

    model_config = ConfigDict(from_attributes=True)

    full_name: str | None = None


class SettingsUpdateRequest(BaseModel):
    """Placeholder request body.

    The dashboard router does not expose a settings write endpoint; the frontend
    Settings page should call ``PUT /api/v1/auth/me`` instead. Kept here so the
    frontend can share one type.
    """

    full_name: str | None = Field(default=None, max_length=100)
