"""
Onboarding wizard schemas — request/response contracts.
"""
import uuid
from datetime import datetime

from pydantic import computed_field

from app.schemas.common import BaseSchema


class OnboardingResponse(BaseSchema):
    workspace_id: uuid.UUID
    step_workspace_created: bool
    step_aws_account_connected: bool
    step_first_sync_complete: bool
    step_team_member_invited: bool
    step_sla_configured: bool
    completed_at: datetime | None
    dismissed: bool

    @computed_field
    @property
    def all_complete(self) -> bool:
        return all([
            self.step_workspace_created,
            self.step_aws_account_connected,
            self.step_first_sync_complete,
            self.step_team_member_invited,
            self.step_sla_configured,
        ])

    @computed_field
    @property
    def completion_percentage(self) -> int:
        steps = [
            self.step_workspace_created,
            self.step_aws_account_connected,
            self.step_first_sync_complete,
            self.step_team_member_invited,
            self.step_sla_configured,
        ]
        return int(sum(steps) / len(steps) * 100)
