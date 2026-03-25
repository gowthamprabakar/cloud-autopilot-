"""
JobRun — persistent record of a background job execution.

Inspired by MiroFish's `progress_detail` dict pattern (task.py):
- progress_detail is a freeform JSONB dict for step-level tracking.
- Each job type writes its own structured sub-keys into progress_detail.

Example progress_detail for aws_account_validate:
{
  "steps": {
    "sts_assume_role": "ok",
    "get_caller_identity": "ok",
    "security_hub_check": "pending"
  },
  "assumed_role_arn": "arn:aws:sts::123456789012:assumed-role/...",
  "error": null
}
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin
from app.models.enums import JobRunStatus


def _utcnow() -> datetime:
    from datetime import UTC
    return datetime.now(UTC)


class JobRun(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "job_runs"

    aws_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("aws_accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[JobRunStatus] = mapped_column(
        String(32), nullable=False, default=JobRunStatus.PENDING, index=True
    )
    # MiroFish progress_detail pattern — JSONB on Postgres, JSON on SQLite
    progress_detail: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    aws_account: Mapped["AwsAccount | None"] = relationship(back_populates="job_runs")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<JobRun {self.job_type} status={self.status}>"
