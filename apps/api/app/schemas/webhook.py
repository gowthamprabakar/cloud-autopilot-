"""
Webhook schemas — request/response contracts for /api/v1/webhooks.
"""
import uuid

from pydantic import Field, field_validator

from app.schemas.common import BaseSchema, TimestampSchema

VALID_EVENTS = {"finding.created", "finding.critical", "finding.status_changed", "finding.resolved"}


class WebhookCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=10, max_length=2000)
    events: list[str] = Field(default_factory=lambda: ["finding.created"])

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[str]) -> list[str]:
        invalid = set(v) - VALID_EVENTS
        if invalid:
            raise ValueError(f"Invalid event types: {invalid}. Valid: {VALID_EVENTS}")
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class WebhookResponse(TimestampSchema):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    url: str
    events: list[str]
    is_active: bool
    # NOTE: secret is NOT included in list/get responses — security best practice


class WebhookCreatedResponse(WebhookResponse):
    secret: str  # shown ONCE on create for HMAC signature verification
