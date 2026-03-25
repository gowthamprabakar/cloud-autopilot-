"""
Jira integration schemas — request/response contracts.
"""
import uuid

from app.schemas.common import BaseSchema


class JiraTicketRequest(BaseSchema):
    finding_id: uuid.UUID


class JiraTicketResponse(BaseSchema):
    finding_id: uuid.UUID
    jira_key: str | None = None
    jira_url: str | None = None
    error: str | None = None
    success: bool


class JiraConnectionTestResponse(BaseSchema):
    ok: bool
    message: str
