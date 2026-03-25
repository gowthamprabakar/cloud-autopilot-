"""
Suppression rule schemas — request/response contracts for /api/v1/suppression-rules.
"""

import uuid

from pydantic import field_validator

from app.models.enums import FindingSeverity
from app.schemas.common import BaseSchema, TimestampSchema


class SuppressionRuleCreate(BaseSchema):
    name: str
    reason: str
    match_title_contains: str | None = None
    match_resource_type: str | None = None
    match_resource_arn_contains: str | None = None
    match_severity: str | None = None  # must be valid FindingSeverity value if set
    expires_at: str | None = None

    @field_validator("match_severity")
    @classmethod
    def validate_severity(cls, v: str | None) -> str | None:
        if v is not None and v not in [s.value for s in FindingSeverity]:
            raise ValueError(f"Invalid severity: {v}")
        return v


class SuppressionRuleResponse(TimestampSchema):
    id: uuid.UUID
    workspace_id: uuid.UUID
    created_by_user_id: uuid.UUID | None
    name: str
    reason: str
    match_title_contains: str | None
    match_resource_type: str | None
    match_resource_arn_contains: str | None
    match_severity: str | None
    is_active: bool
    expires_at: str | None
