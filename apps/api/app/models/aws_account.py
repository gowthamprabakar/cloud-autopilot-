"""
AWS Account — cross-account role ARN, validation status, sync state.

Rules:
- account_id is the 12-digit AWS account number (stored as string, validated).
- role_arn format: arn:aws:iam::<account_id>:role/<role_name>
- status lifecycle: PENDING → VALIDATING → ACTIVE | ERROR
- enabled_regions: list of AWS regions to sync (default: ["us-east-1"]).
"""

import re
import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin
from app.models.enums import AwsAccountStatus

_ACCOUNT_ID_RE = re.compile(r"^\d{12}$")
_ROLE_ARN_RE = re.compile(r"^arn:aws:iam::\d{12}:role/.+$")


class AwsAccount(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "aws_accounts"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[str] = mapped_column(String(12), nullable=False)
    account_alias: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role_arn: Mapped[str] = mapped_column(Text, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[AwsAccountStatus] = mapped_column(
        String(32), nullable=False, default=AwsAccountStatus.PENDING
    )
    last_synced_at: Mapped[str | None] = mapped_column(nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # AWS regions to scan during sync jobs. Default: us-east-1.
    # Users can update this list to scan additional regions.
    enabled_regions: Mapped[list] = mapped_column(
        JSON, nullable=False, default=lambda: ["us-east-1"]
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="aws_accounts")  # type: ignore[name-defined]
    job_runs: Mapped[list["JobRun"]] = relationship(  # type: ignore[name-defined]
        back_populates="aws_account", cascade="all, delete-orphan"
    )

    @validates("account_id")
    def validate_account_id(self, key: str, value: str) -> str:
        if not _ACCOUNT_ID_RE.match(value):
            raise ValueError(f"account_id must be 12 digits, got: {value!r}")
        return value

    @validates("role_arn")
    def validate_role_arn(self, key: str, value: str) -> str:
        if not _ROLE_ARN_RE.match(value):
            raise ValueError(f"role_arn must be arn:aws:iam::<12-digits>:role/<name>, got: {value!r}")
        return value

    def __repr__(self) -> str:
        return f"<AwsAccount {self.account_id} status={self.status}>"
