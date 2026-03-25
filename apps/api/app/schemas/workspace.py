import uuid
from datetime import datetime

from pydantic import ConfigDict, Field, field_validator

from app.models.enums import WorkspaceStatus
from app.schemas.common import BaseSchema, IDSchema, TimestampSchema


class WorkspaceCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
    )

    @field_validator("slug")
    @classmethod
    def slug_lowercase(cls, v: str) -> str:
        return v.lower()


class WorkspaceRead(IDSchema, TimestampSchema):
    tenant_id: uuid.UUID
    name: str
    slug: str
    status: WorkspaceStatus
    is_active: bool


class WorkspaceUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=255)


# Sprint 7 schemas

class WorkspaceResponse(BaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    slug: str
    status: WorkspaceStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UpdateWorkspaceRequest(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=255)
