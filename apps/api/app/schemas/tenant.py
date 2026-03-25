import uuid

from pydantic import Field, field_validator

from app.models.enums import TenantPlan, TenantStatus
from app.schemas.common import BaseSchema, IDSchema, TimestampSchema


class TenantRead(IDSchema, TimestampSchema):
    name: str
    slug: str
    plan: TenantPlan
    status: TenantStatus
    is_active: bool


class TenantUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    plan: TenantPlan | None = None
