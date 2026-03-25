"""
CanonicalFinding — normalized, deduplicated finding.

OpenViking hierarchy mapping:
  L1 / OVERVIEW — authoritative normalized view for UI, scoring, and workflows.

Rules:
- risk_score is set ONLY by backend services (never frontend, never AI).
- severity is set ONLY by backend services from source data.
- compliance_frameworks is a list of compliance IDs (e.g., ["CIS_AWS_1.4", "PCI_DSS_3.2.1"]).
"""

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin
from app.models.enums import FindingSeverity, FindingSource, FindingStatus


class CanonicalFinding(Base, UUIDPKMixin, TimestampMixin):
    """
    L1 / OVERVIEW — normalized finding, the authoritative record for the UI.
    Multiple source_findings may map to one canonical finding (dedup).
    """
    __tablename__ = "canonical_findings"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    aws_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("aws_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Fingerprint for deduplication across sources/syncs
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    primary_source: Mapped[FindingSource] = mapped_column(String(64), nullable=False)
    severity: Mapped[FindingSeverity] = mapped_column(
        String(16), nullable=False, index=True
    )
    status: Mapped[FindingStatus] = mapped_column(
        String(32), nullable=False, default=FindingStatus.OPEN, index=True
    )
    # risk_score: 0.0–10.0, set by backend scoring service ONLY
    risk_score: Mapped[float | None] = mapped_column(nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_arn: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    region: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # compliance_frameworks: list of framework IDs — e.g. ["CIS_AWS_1.4"]
    compliance_frameworks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # tags: freeform k/v for grouping/filtering
    tags: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    first_seen_at: Mapped[str | None] = mapped_column(nullable=True)
    last_seen_at: Mapped[str | None] = mapped_column(nullable=True)
    resolved_at: Mapped[str | None] = mapped_column(nullable=True)

    # Relationships
    source_findings: Mapped[list["SourceFinding"]] = relationship(  # type: ignore[name-defined]
        back_populates="canonical_finding"
    )
    aws_account: Mapped["AwsAccount"] = relationship()  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<CanonicalFinding {self.severity} {self.title[:40]}>"
