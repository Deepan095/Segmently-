"""Analytics dashboard endpoints (Module 4).

All endpoints are scoped to the authenticated user via ``get_current_user`` and
delegate to :mod:`app.services.dashboard_service`, which uses aggregate queries
only (no N+1).

Settings note
-------------
The frontend Settings page reads the display name from ``GET /auth/me`` and
writes it with ``PUT /auth/me`` (Auth module owns the ``User`` write path). This
router therefore exposes no settings write endpoint - see
``app.schemas.dashboard.SettingsUpdateRequest`` for the shared type.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.dashboard import SummaryResponse, TopClip, UsageResponse
from app.services import dashboard_service

logger = logging.getLogger("segmently.routers.dashboard")

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SummaryResponse:
    """Lifetime totals for the current user (stat cards)."""
    return dashboard_service.get_summary(db, current_user.id)


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    window: str = Query(
        default="30d", alias="range", pattern="^(7d|30d|90d)$"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UsageResponse:
    """Daily minutes-processed + clips-generated over the requested window."""
    return dashboard_service.get_usage(db, current_user.id, range=window)  # type: ignore[arg-type]


@router.get("/top-clips", response_model=list[TopClip])
async def get_top_clips(
    limit: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TopClip]:
    """The current user's highest-scoring clips."""
    return dashboard_service.get_top_clips(db, current_user.id, limit=limit)
