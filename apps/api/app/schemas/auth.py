"""
Auth schemas — request/response contracts for the auth domain.

POST /auth/register → RegisterRequest → RegisterResponse
POST /auth/login    → LoginRequest    → TokenResponse
GET  /auth/me       →                 → UserProfileResponse
"""

import uuid

from pydantic import EmailStr, Field, field_validator

from app.models.enums import TenantPlan, UserRole
from app.schemas.common import BaseSchema, TimestampSchema


# ── Register ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseSchema):
    """Creates a new tenant + default workspace + first super_admin user."""

    # Tenant
    tenant_name: str = Field(min_length=2, max_length=255)
    tenant_slug: str = Field(
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
        description="URL-safe lowercase slug, e.g. 'acme-corp'",
    )
    plan: TenantPlan = TenantPlan.BASELINE

    # First workspace
    workspace_name: str = Field(default="Default", min_length=1, max_length=255)

    # First user (super_admin)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)

    @field_validator("tenant_slug")
    @classmethod
    def slug_lowercase(cls, v: str) -> str:
        return v.lower()


class RegisterResponse(BaseSchema):
    tenant_id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    access_token: str
    token_type: str = "bearer"


# ── Login ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseSchema):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ── Current User ──────────────────────────────────────────────────────────────

class UserProfileResponse(TimestampSchema):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    tenant_id: uuid.UUID
    workspace_id: uuid.UUID | None
    is_active: bool
