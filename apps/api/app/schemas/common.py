"""
Shared Pydantic base schemas and response wrappers.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(BaseSchema):
    created_at: datetime
    updated_at: datetime


class IDSchema(BaseSchema):
    id: uuid.UUID


class MessageResponse(BaseSchema):
    message: str


class PaginatedResponse(BaseSchema):
    items: list
    total: int
    page: int
    page_size: int
    has_next: bool
