"""Pydantic schemas for the Admin Panel module (Module 5).

All of these back ``/api/v1/admin/*`` endpoints, which are gated by
``get_current_admin`` (requires ``User.is_admin``).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdminUserResponse(BaseModel):
    """Admin-facing view of a user account, with owned-resource counts."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str  # output only; validated on input, see UserResponse
    full_name: str | None
    is_active: bool
    is_verified: bool
    is_admin: bool
    oauth_provider: str | None
    created_at: datetime
    projects_count: int
    clips_count: int


class AdminUserUpdateRequest(BaseModel):
    """Partial update for a user account. Only provided fields are applied."""

    is_active: bool | None = None
    is_admin: bool | None = None
    is_verified: bool | None = None


class PlatformStats(BaseModel):
    """Aggregate platform metrics for the admin dashboard.

    ``storage_bytes_estimate`` is the SUM of ``Project.file_size_bytes`` across
    every project. It is an *estimate*: it only counts uploaded source media
    that reported a size, and does not include rendered clip or thumbnail
    objects in object storage.
    """

    users_total: int
    users_active: int
    projects_total: int
    clips_total: int
    storage_bytes_estimate: int
    jobs_failed: int


class AdminJobResponse(BaseModel):
    """Admin-facing view of a single processing job."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    job_type: str
    status: str
    progress_pct: int
    error_message: str | None
    created_at: datetime
