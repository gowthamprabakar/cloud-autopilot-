from pydantic import BaseModel, field_validator
from typing import Optional
import json


class ReportScheduleResponse(BaseModel):
    id: str
    workspace_id: str
    enabled: bool
    frequency: str
    day_of_week: int
    recipients: list[str]
    last_sent_at: Optional[str] = None

    @classmethod
    def from_orm_model(cls, m) -> "ReportScheduleResponse":
        recipients = []
        if m.recipients:
            try:
                recipients = json.loads(m.recipients)
            except Exception:
                recipients = []
        return cls(
            id=m.id,
            workspace_id=m.workspace_id,
            enabled=m.enabled,
            frequency=m.frequency,
            day_of_week=m.day_of_week,
            recipients=recipients,
            last_sent_at=m.last_sent_at.isoformat() if m.last_sent_at else None,
        )


class ReportScheduleUpdate(BaseModel):
    enabled: Optional[bool] = None
    frequency: Optional[str] = None  # weekly | monthly
    day_of_week: Optional[int] = None  # 1-7
    recipients: Optional[list[str]] = None

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, v):
        if v is not None and v not in ("weekly", "monthly"):
            raise ValueError("frequency must be 'weekly' or 'monthly'")
        return v

    @field_validator("day_of_week")
    @classmethod
    def validate_day(cls, v):
        if v is not None and not (1 <= v <= 7):
            raise ValueError("day_of_week must be 1-7")
        return v


class SendNowResponse(BaseModel):
    sent: int
    workspace_id: str
    recipients: list[str]
