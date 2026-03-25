import uuid
from datetime import datetime

from pydantic import ConfigDict, EmailStr, Field

from app.models.enums import UserRole
from app.schemas.common import BaseSchema, IDSchema, TimestampSchema


class UserRead(IDSchema, TimestampSchema):
    email: str
    full_name: str
    role: UserRole
    tenant_id: uuid.UUID
    workspace_id: uuid.UUID | None
    is_active: bool
    last_login_at: datetime | None


class UserInvite(BaseSchema):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole = UserRole.ANALYST
    workspace_id: uuid.UUID | None = None


class UserUpdate(BaseSchema):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None
    workspace_id: uuid.UUID | None = None
    is_active: bool | None = None


# Sprint 7 schemas

class UserResponse(BaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    tenant_id: uuid.UUID
    workspace_id: uuid.UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class InviteUserRequest(BaseSchema):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole = UserRole.ANALYST
    password: str = Field(min_length=8, max_length=128)


class UpdateUserRoleRequest(BaseSchema):
    role: UserRole


class UserListResponse(BaseSchema):
    items: list[UserResponse]
    total: int
