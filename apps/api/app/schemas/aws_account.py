"""
AWS Account schemas — request/response contracts for /api/v1/aws-accounts.
"""

import re
import uuid
from datetime import datetime

from pydantic import field_validator

from app.models.enums import AwsAccountStatus
from app.schemas.common import BaseSchema, TimestampSchema

_ACCOUNT_ID_RE = re.compile(r"^\d{12}$")
_ROLE_ARN_RE = re.compile(r"^arn:aws:iam::\d{12}:role/.+$")

_ALL_REGIONS = {
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1",
    "eu-north-1", "eu-south-1",
    "ap-southeast-1", "ap-southeast-2", "ap-northeast-1",
    "ap-northeast-2", "ap-northeast-3", "ap-south-1",
    "sa-east-1", "ca-central-1", "me-south-1", "af-south-1",
}


class AwsAccountCreate(BaseSchema):
    account_id: str
    account_alias: str | None = None
    role_arn: str
    external_id: str | None = None
    enabled_regions: list[str] = ["us-east-1"]

    @field_validator("account_id")
    @classmethod
    def validate_account_id(cls, v: str) -> str:
        if not _ACCOUNT_ID_RE.match(v):
            raise ValueError("account_id must be exactly 12 digits")
        return v

    @field_validator("role_arn")
    @classmethod
    def validate_role_arn(cls, v: str) -> str:
        if not _ROLE_ARN_RE.match(v):
            raise ValueError("role_arn must match arn:aws:iam::<12-digits>:role/<name>")
        return v

    @field_validator("enabled_regions")
    @classmethod
    def validate_regions(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("enabled_regions must contain at least one region")
        invalid = [r for r in v if r not in _ALL_REGIONS]
        if invalid:
            raise ValueError(f"Unknown AWS regions: {invalid}")
        return list(dict.fromkeys(v))  # deduplicate, preserve order


class AwsAccountUpdate(BaseSchema):
    account_alias: str | None = None
    role_arn: str | None = None
    external_id: str | None = None
    enabled_regions: list[str] | None = None

    @field_validator("role_arn")
    @classmethod
    def validate_role_arn(cls, v: str | None) -> str | None:
        if v is not None and not _ROLE_ARN_RE.match(v):
            raise ValueError("role_arn must match arn:aws:iam::<12-digits>:role/<name>")
        return v

    @field_validator("enabled_regions")
    @classmethod
    def validate_regions(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if not v:
            raise ValueError("enabled_regions must contain at least one region")
        invalid = [r for r in v if r not in _ALL_REGIONS]
        if invalid:
            raise ValueError(f"Unknown AWS regions: {invalid}")
        return list(dict.fromkeys(v))


class AwsAccountResponse(TimestampSchema):
    id: uuid.UUID
    workspace_id: uuid.UUID
    account_id: str
    account_alias: str | None
    role_arn: str
    external_id: str | None
    status: AwsAccountStatus
    last_synced_at: str | None
    last_error: str | None
    enabled_regions: list[str]


class JobRunResponse(TimestampSchema):
    """Summary of a job run — returned when triggering a validation or sync."""
    id: uuid.UUID
    aws_account_id: uuid.UUID | None
    workspace_id: uuid.UUID
    job_type: str
    status: str
    progress_detail: dict
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
