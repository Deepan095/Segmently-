"""Business logic for the analytics dashboard (Module 4).

All queries are aggregate queries scoped to a single user - no per-row Python
loops over ORM rows, no N+1. The only Python-side iteration is over the small,
fixed set of calendar days in the requested range when zero-filling the usage
series.

Proxies / assumptions
---------------------
* "minutes uploaded" and "minutes processed" derive from
  ``Project.duration_seconds / 60``.
* ``clips_downloaded`` has no backing column in the MVP schema. We use the count
  of clips in status ``ready`` as a proxy. A dedicated ``ClipDownload`` event
  table is post-MVP.
* ``TopClip.thumbnail_url`` is left ``None`` here: turning a private
  ``Clip.thumbnail_key`` into a signed, expiring URL is the Clips module's
  responsibility and needs the storage client that is not wired up yet.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.clip import Clip, ClipStatus
from app.models.project import Project, ProjectStatus
from app.schemas.dashboard import (
    SummaryResponse,
    TopClip,
    UsagePoint,
    UsageResponse,
    UsageRange,
)

logger = logging.getLogger("segmently.services.dashboard")

# ``get_usage`` takes a param literally named ``range`` (per the module spec),
# which shadows the builtin inside that function - keep a reference here.
_range = range

_RANGE_DAYS: dict[str, int] = {"7d": 7, "30d": 30, "90d": 90}
_SECONDS_PER_MINUTE = 60.0


def get_summary(db: Session, user_id: int) -> SummaryResponse:
    """Return lifetime totals for ``user_id`` in a handful of aggregate queries."""
    projects_total, total_duration_seconds, projects_completed = db.execute(
        select(
            func.count(Project.id),
            func.coalesce(func.sum(Project.duration_seconds), 0.0),
            func.count(Project.id).filter(
                Project.status == ProjectStatus.completed
            ),
        ).where(Project.user_id == user_id)
    ).one()

    clips_generated, clips_ready = db.execute(
        select(
            func.count(Clip.id),
            func.count(Clip.id).filter(Clip.status == ClipStatus.ready),
        ).where(Clip.user_id == user_id)
    ).one()

    return SummaryResponse(
        minutes_uploaded=round(
            float(total_duration_seconds or 0.0) / _SECONDS_PER_MINUTE, 2
        ),
        projects_total=int(projects_total or 0),
        projects_completed=int(projects_completed or 0),
        clips_generated=int(clips_generated or 0),
        clips_downloaded=int(clips_ready or 0),
    )


def _coerce_day(value: object) -> date:
    """Normalise a ``func.date(...)`` result (date on PG, str on SQLite)."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value)[:10])


def get_usage(db: Session, user_id: int, range: UsageRange = "30d") -> UsageResponse:
    """Daily minutes-processed + clips-generated for the trailing window.

    Two grouped aggregate queries (one over projects, one over clips) are merged
    by date and zero-filled so the chart always has one point per day.
    """
    days = _RANGE_DAYS.get(range, 30)
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days - 1)
    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)

    project_day = func.date(Project.created_at)
    project_rows = db.execute(
        select(
            project_day,
            func.coalesce(func.sum(Project.duration_seconds), 0.0),
        )
        .where(Project.user_id == user_id, Project.created_at >= start_dt)
        .group_by(project_day)
    ).all()

    clip_day = func.date(Clip.created_at)
    clip_rows = db.execute(
        select(clip_day, func.count(Clip.id))
        .where(Clip.user_id == user_id, Clip.created_at >= start_dt)
        .group_by(clip_day)
    ).all()

    minutes_by_day: dict[date, float] = {
        _coerce_day(day): float(secs or 0.0) / _SECONDS_PER_MINUTE
        for day, secs in project_rows
    }
    clips_by_day: dict[date, int] = {
        _coerce_day(day): int(count or 0) for day, count in clip_rows
    }

    points = [
        UsagePoint(
            date=(day := start_date + timedelta(days=offset)),
            minutes_processed=round(minutes_by_day.get(day, 0.0), 2),
            clips_generated=clips_by_day.get(day, 0),
        )
        for offset in _range(days)
    ]
    return UsageResponse(range=range, points=points)


def get_top_clips(db: Session, user_id: int, limit: int = 5) -> list[TopClip]:
    """Highest-scoring clips for the user, newest first as a tie-breaker."""
    rows = db.execute(
        select(Clip.id, Clip.title, Clip.score, Clip.project_id)
        .where(Clip.user_id == user_id)
        .order_by(Clip.score.desc(), Clip.created_at.desc())
        .limit(limit)
    ).all()
    return [
        TopClip(
            id=row.id,
            title=row.title,
            score=int(row.score or 0),
            project_id=row.project_id,
            thumbnail_url=None,
        )
        for row in rows
    ]
