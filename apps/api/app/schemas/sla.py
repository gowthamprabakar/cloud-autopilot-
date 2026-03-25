"""
SLA schemas — request/response contracts for SLA tracking endpoints.
"""

import uuid

from app.schemas.common import BaseSchema


class SlaFindingResponse(BaseSchema):
    id: uuid.UUID
    title: str
    severity: str
    resource_type: str | None
    resource_arn: str | None
    first_seen_at: str | None
    risk_score: float | None
    sla_status: str       # "on_track" | "at_risk" | "breached" | "resolved"
    sla_due_date: str | None
    sla_days_remaining: int | None
    sla_days_total: int | None


class SlaSummaryResponse(BaseSchema):
    total_open: int
    breached: int
    at_risk: int
    on_track: int
