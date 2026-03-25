"""
WorkspaceSettings schemas — request/response contracts.
"""

import uuid

from pydantic import Field, field_serializer

from app.schemas.common import BaseSchema, TimestampSchema


class WorkspaceSettingsResponse(TimestampSchema):
    id: uuid.UUID
    workspace_id: uuid.UUID
    sla_days_critical: int
    sla_days_high: int
    sla_days_medium: int
    sla_days_low: int
    sla_days_info: int
    finding_auto_close_days: int
    # Jira integration fields
    jira_base_url: str | None = None
    jira_email: str | None = None
    jira_api_token: str | None = None   # will be masked in response
    jira_project_key: str | None = None
    jira_issue_type: str = "Task"

    @field_serializer('jira_api_token')
    def mask_jira_token(self, v: str | None) -> str | None:
        """Never expose the Jira API token in API responses."""
        if v:
            return "••••••••"
        return None


class WorkspaceSettingsUpdate(BaseSchema):
    sla_days_critical: int | None = Field(default=None, ge=1, le=365)
    sla_days_high: int | None = Field(default=None, ge=1, le=365)
    sla_days_medium: int | None = Field(default=None, ge=1, le=365)
    sla_days_low: int | None = Field(default=None, ge=1, le=365)
    sla_days_info: int | None = Field(default=None, ge=1, le=365)
    finding_auto_close_days: int | None = Field(default=None, ge=0, le=365)
    # Jira integration fields
    jira_base_url: str | None = None
    jira_email: str | None = None
    jira_api_token: str | None = None
    jira_project_key: str | None = None
    jira_issue_type: str | None = None
