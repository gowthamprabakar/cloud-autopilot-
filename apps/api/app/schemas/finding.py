"""
Finding schemas — request/response contracts for /api/v1/findings.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import field_validator

from app.models.enums import FindingSeverity, FindingSource, FindingStatus
from app.schemas.common import BaseSchema, TimestampSchema

# Risk label thresholds for breakdown widget
_RISK_LABELS = [
    (8.0, "critical-risk"),
    (6.0, "high-risk"),
    (4.0, "medium-risk"),
    (2.0, "low-risk"),
    (0.0, "info"),
]


def _risk_label(severity: str) -> str:
    mapping = {
        "critical": "critical-risk",
        "high": "high-risk",
        "medium": "medium-risk",
        "low": "low-risk",
        "info": "info",
    }
    return mapping.get(severity, "info")


class CanonicalFindingResponse(TimestampSchema):
    """Full response for a single canonical finding."""
    id: uuid.UUID
    workspace_id: uuid.UUID
    aws_account_id: uuid.UUID
    fingerprint: str
    primary_source: FindingSource
    severity: FindingSeverity
    status: FindingStatus
    risk_score: float | None
    title: str
    description: str | None
    remediation: str | None
    resource_arn: str | None
    resource_type: str | None
    region: str | None
    compliance_frameworks: list[str]
    tags: dict[str, Any]
    first_seen_at: str | None
    last_seen_at: str | None
    resolved_at: str | None


class FindingListResponse(BaseSchema):
    """Paginated list response for findings."""
    items: list[CanonicalFindingResponse]
    total: int
    page: int
    page_size: int
    pages: int


class FindingUpdateRequest(BaseSchema):
    """PATCH /findings/{id} — update status and/or tags."""
    status: FindingStatus | None = None
    tags: dict[str, Any] | None = None


class SeverityBreakdownItem(BaseSchema):
    """Single row in the severity breakdown list."""
    severity: str
    count: int
    risk_label: str


class FindingStatsResponse(BaseSchema):
    """Dashboard widget response — finding counts by severity and status."""
    by_severity: dict[str, int]
    by_status: dict[str, int]
    total: int
    breakdown: list[SeverityBreakdownItem]


class BulkFindingUpdateRequest(BaseSchema):
    """PATCH /findings/bulk — update status for multiple findings at once."""
    finding_ids: list[uuid.UUID]
    status: FindingStatus

    @field_validator("finding_ids")
    @classmethod
    def validate_ids(cls, v: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(v) == 0:
            raise ValueError("finding_ids must not be empty")
        if len(v) > 100:
            raise ValueError("Maximum 100 findings per bulk update")
        return v


class BulkFindingUpdateResponse(BaseSchema):
    updated: int
    failed: int
    errors: list[str]
