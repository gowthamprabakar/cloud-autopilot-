"""
Notification schemas — request/response contracts for /api/v1/notifications.
"""

import uuid
from datetime import datetime
from typing import Any

from app.schemas.common import BaseSchema


class NotificationResponse(BaseSchema):
    """Full response for a single notification."""
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID | None
    type: str
    title: str
    body: str
    is_read: bool
    metadata_: dict[str, Any] | None = None
    link_path: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True, "from_attributes": True}


class NotificationListResponse(BaseSchema):
    """List response for notifications with unread count."""
    items: list[NotificationResponse]
    unread_count: int
