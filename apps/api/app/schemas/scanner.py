"""Pydantic schemas for the scanner API."""

import json
import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, field_validator


class ScanJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    aws_account_id: Optional[str] = None
    status: str
    triggered_by: str
    started_at: str
    completed_at: Optional[str] = None
    findings_added: int = 0
    findings_updated: int = 0
    findings_total: int = 0
    sources_scanned: list = []
    sources_failed: list = []
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None
    created_at: str

    @field_validator("id", "workspace_id", mode="before")
    @classmethod
    def uuid_to_str(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)

    @field_validator("aws_account_id", mode="before")
    @classmethod
    def optional_uuid_to_str(cls, v: Any) -> Optional[str]:
        return str(v) if v is not None else None

    @field_validator("started_at", "completed_at", "created_at", mode="before")
    @classmethod
    def datetime_to_str(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v)

    @field_validator("sources_scanned", "sources_failed", mode="before")
    @classmethod
    def ensure_list(cls, v: Any) -> list:
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                result = json.loads(v)
                return result if isinstance(result, list) else []
            except Exception:
                return []
        return []


class ScanTriggerResponse(BaseModel):
    job_id: Optional[str]
    status: str
    message: str


class ScanStatusResponse(BaseModel):
    latest_job: Optional[ScanJobResponse]
    is_running: bool
    last_sync_message: str


class ScanHistoryResponse(BaseModel):
    items: list[ScanJobResponse]
    total: int
