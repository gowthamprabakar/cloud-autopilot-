"""
Assignment schemas — request/response contracts for finding assignment endpoints.
"""
import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampSchema


class AssignFindingRequest(BaseSchema):
    assignee_user_id: uuid.UUID
    due_date: datetime | None = None
    note: str | None = Field(default=None, max_length=1000)


class AssignmentResponse(TimestampSchema):
    id: uuid.UUID
    finding_id: uuid.UUID
    workspace_id: uuid.UUID
    assignee_user_id: uuid.UUID
    assignee_email: str | None = None       # denormalised — populated in service
    assigned_by_user_id: uuid.UUID | None
    assigned_by_email: str | None = None    # denormalised
    due_date: datetime | None
    is_active: bool
    note: str | None
    finding_title: str | None = None        # denormalised — populated in service
