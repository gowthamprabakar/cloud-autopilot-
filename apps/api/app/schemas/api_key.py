"""
Pydantic schemas for API Key endpoints.
"""

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampSchema


class ApiKeyCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    expires_at: datetime | None = None  # ISO datetime string or null


class ApiKeyResponse(TimestampSchema):
    """Returned in list view — never includes the raw key."""

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    key_prefix: str  # e.g. "sk-abc123" — safe to display
    last_used_at: datetime | None
    expires_at: datetime | None
    is_active: bool


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Returned ONCE on creation — includes the raw key."""

    raw_key: str  # "sk-<48chars>" — show to user ONCE, never stored
