"""
OnboardingProgress — tracks workspace setup completion.
One row per workspace. Steps complete themselves automatically
as the user performs actions (e.g. connecting an AWS account completes step 2).
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import UUIDPKMixin, TimestampMixin


class OnboardingProgress(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "onboarding_progress"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        unique=True, nullable=False,
    )
    step_workspace_created: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)   # always True
    step_aws_account_connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    step_first_sync_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    step_team_member_invited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    step_sla_configured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<OnboardingProgress workspace_id={self.workspace_id}>"
