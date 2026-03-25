"""
SourceFinding — raw finding record from an AWS security service.

OpenViking hierarchy mapping:
  L2 / DETAIL  → source_findings    (this model — raw, service-native)
  L1 / OVERVIEW → canonical_findings (normalized, deduplicated)
  L0 / ABSTRACT → future: finding_clusters (AI-correlated)

source_findings preserves the original payload intact for auditability.
canonical_findings are the authoritative view for UI and scoring.
"""

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin
from app.models.enums import FindingSeverity, FindingSource


class SourceFinding(Base, UUIDPKMixin, TimestampMixin):
    """
    L2 / DETAIL — raw finding exactly as received from the AWS source service.
    Never modified after ingestion; append-only.
    """
    __tablename__ = "source_findings"
    __table_args__ = (
        # Deduplicate by native ID per account; upsert uses this constraint
        UniqueConstraint("aws_account_id", "native_finding_id", name="uq_source_finding_account_native"),
    )

    aws_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("aws_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[FindingSource] = mapped_column(String(64), nullable=False, index=True)
    # Native identifier from the originating service (e.g., Security Hub finding ID)
    native_finding_id: Mapped[str] = mapped_column(Text, nullable=False)
    # Service-reported severity (stored as-is; never recomputed in frontend)
    severity: Mapped[FindingSeverity] = mapped_column(String(16), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Full raw payload preserved for auditability
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # AWS region where the finding was generated
    region: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Affected resource ARN
    resource_arn: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # ISO8601 string from the source service
    first_observed_at: Mapped[str | None] = mapped_column(nullable=True)
    last_observed_at: Mapped[str | None] = mapped_column(nullable=True)
    # FK to canonical finding (null until normalization pass runs)
    canonical_finding_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("canonical_findings.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Relationships
    aws_account: Mapped["AwsAccount"] = relationship()  # type: ignore[name-defined]
    canonical_finding: Mapped["CanonicalFinding | None"] = relationship(  # type: ignore[name-defined]
        back_populates="source_findings"
    )

    def __repr__(self) -> str:
        return f"<SourceFinding {self.source} {self.native_finding_id[:16]}...>"
