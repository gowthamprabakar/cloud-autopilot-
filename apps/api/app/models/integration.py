"""
Integration configuration model — external service connectors.

Sprint 32: Stores connection details for Slack, Jira, PagerDuty, SIEM,
GitHub, and GitLab integrations.  Config payloads are stored as encrypted
JSON (encryption handled at the service layer before persistence).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, TIMESTAMP, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class Integration(Base, UUIDPKMixin, TimestampMixin):
    """
    External service connector record.

    Supported integration_type values:
      - slack:      {webhook_url, channel, bot_token}
      - jira:       {base_url, project_key, api_token, email}
      - pagerduty:  {api_key, service_id, escalation_policy_id}
      - siem:       {endpoint_url, api_key, format: "cef"|"leef"|"json"}
      - github:     {token, org, repo}
      - gitlab:     {token, project_id}
    """

    __tablename__ = "integrations"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # "slack" | "jira" | "pagerduty" | "siem" | "github" | "gitlab"
    integration_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )
    # User-friendly display name
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Encrypted JSON blob with connection details (see docstring above)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON list of event types this integration should receive
    # e.g. ["simulation.completed", "gate.failed", "finding.critical"]
    event_filter: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_integrations_ws_type", "workspace_id", "integration_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<Integration id={self.id} type={self.integration_type} "
            f"name={self.name!r} enabled={self.is_enabled}>"
        )
