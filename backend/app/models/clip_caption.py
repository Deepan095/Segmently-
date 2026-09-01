"""ClipCaption model - editable timed caption segments for a clip."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.clip import Clip


class ClipCaption(Base):
    __tablename__ = "clip_captions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    clip_id: Mapped[int] = mapped_column(
        ForeignKey("clips.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    # [{ "start": float, "end": float, "text": str }, ...]
    segments: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    clip: Mapped["Clip"] = relationship(back_populates="caption")
