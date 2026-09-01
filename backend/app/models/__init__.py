"""ORM model package.

Every model is imported here so that ``Base.metadata`` is fully populated
whenever ``app.models`` is imported (required for Alembic autogenerate).
"""

from app.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin
from app.models.clip import Clip, ClipStatus
from app.models.clip_caption import ClipCaption
from app.models.processing_job import JobStatus, JobType, ProcessingJob
from app.models.project import Project, ProjectStatus, SourceType
from app.models.refresh_token import RefreshToken
from app.models.transcript import Transcript
from app.models.user import User

__all__ = [
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    "User",
    "RefreshToken",
    "Project",
    "ProjectStatus",
    "SourceType",
    "Transcript",
    "ProcessingJob",
    "JobType",
    "JobStatus",
    "Clip",
    "ClipStatus",
    "ClipCaption",
]
