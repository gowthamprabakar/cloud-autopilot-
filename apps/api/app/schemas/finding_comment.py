"""
FindingComment schemas — request/response contracts for finding comment endpoints.
"""
import uuid

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampSchema


class FindingCommentCreate(BaseSchema):
    body: str = Field(min_length=1, max_length=10000)


class FindingCommentResponse(TimestampSchema):
    id: uuid.UUID
    finding_id: uuid.UUID
    user_id: uuid.UUID | None
    author_email: str | None = None  # denormalised from user (populated in service)
    body: str
