"""
Audit log schemas — request/response contracts for /api/v1/audit-log.
"""

import uuid
from datetime import datetime
from typing import Any

from app.schemas.common import BaseSchema


class AuditLogResponse(BaseSchema):
    """Full response for a single audit log entry."""
    id: uuid.UUID
    workspace_id: uuid.UUID
    actor_user_id: uuid.UUID | None
    actor_email: str
    action: str
    resource_type: str | None
    resource_id: str | None
    detail: dict[str, Any] | None
    ip_address: str | None
    created_at: datetime
    updated_at: datetime


class AuditLogListResponse(BaseSchema):
    """Paginated list response for audit log entries."""
    items: list[AuditLogResponse]
    total: int
    page: int
    pages: int
