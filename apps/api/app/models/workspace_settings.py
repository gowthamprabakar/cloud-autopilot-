"""
WorkspaceSettings — per-workspace configuration.
One row per workspace (created with sensible defaults on first access).

SLA days define how long a finding of each severity level should remain
open before being considered a breach.
"""
import uuid
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.base import UUIDPKMixin, TimestampMixin


class WorkspaceSettings(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "workspace_settings"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        unique=True, nullable=False, index=True
    )
    # SLA days per severity — how many days before a finding is "breached"
    sla_days_critical: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    sla_days_high: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    sla_days_medium: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    sla_days_low: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    sla_days_info: Mapped[int] = mapped_column(Integer, default=180, nullable=False)
    # Future settings (already columns, values ignored for now)
    finding_auto_close_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # 0 = disabled; >0 = auto-close resolved findings after N days

    # ── Jira Integration ─────────────────────────────────────────
    jira_base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    jira_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    jira_api_token: Mapped[str | None] = mapped_column(String(500), nullable=True)
    jira_project_key: Mapped[str | None] = mapped_column(String(50), nullable=True)
    jira_issue_type: Mapped[str] = mapped_column(String(50), default="Task", nullable=False)

    def __repr__(self) -> str:
        return f"<WorkspaceSettings workspace_id={self.workspace_id}>"
