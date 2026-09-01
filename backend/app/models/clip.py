"""Clip model - a rendered vertical short generated from a project."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.clip_caption import ClipCaption
    from app.models.project import Project
    from app.models.user import User


class ClipStatus(str, enum.Enum):
    queued = "queued"
    rendering = "rendering"
    ready = "ready"
    failed = "failed"


class Clip(Base, TimestampMixin):
    __tablename__ = "clips"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    start_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    end_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(
        String(16), default="9:16", nullable=False
    )
    status: Mapped[ClipStatus] = mapped_column(
        Enum(ClipStatus, name="clip_status"),
        default=ClipStatus.queued,
        nullable=False,
        index=True,
    )
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    score_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    thumbnail_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    caption_style: Mapped[Any | None] = mapped_column(JSON, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="clips")
    user: Mapped["User"] = relationship(back_populates="clips")
    caption: Mapped["ClipCaption | None"] = relationship(
        back_populates="clip",
        cascade="all, delete-orphan",
        uselist=False,
    )
