"""
ScanJob — tracks each AWS scanner ingestion run.

Rules:
- workspace_id scopes the job to a tenant's workspace.
- aws_account_id is None when scanning all accounts for a workspace.
- status lifecycle: running → completed | failed | partial
- triggered_by: "manual" | "scheduler" | "api"
- findings_added: net new canonical_findings created.
- findings_updated: existing findings refreshed (last_seen_at bumped).
- findings_total: total findings processed (added + updated).
- sources_scanned: JSON list of source names that completed successfully.
- sources_failed: JSON list of source names that raised errors.
"""

import uuid
from datetime import datetime

from sqlalchemy import Index, String, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class ScanJob(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "scan_jobs"

    workspace_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    aws_account_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    # "running" | "completed" | "failed" | "partial"
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running", index=True)
    # "manual" | "scheduler" | "api"
    triggered_by: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    findings_added: Mapped[int] = mapped_column(nullable=False, default=0)
    findings_updated: Mapped[int] = mapped_column(nullable=False, default=0)
    findings_total: Mapped[int] = mapped_column(nullable=False, default=0)
    # JSON list — ["security_hub", "guard_duty", ...]
    sources_scanned: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # JSON list — ["inspector"] if service unavailable
    sources_failed: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("ix_scan_jobs_started_at", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<ScanJob {self.status} workspace={self.workspace_id} added={self.findings_added}>"
