"""
JiraTicketRepository — data access for jira_tickets table.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jira_ticket import JiraTicket


class JiraTicketRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        finding_id: uuid.UUID,
        workspace_id: uuid.UUID,
        jira_key: str,
        jira_url: str,
        user_id: uuid.UUID | None,
    ) -> JiraTicket:
        """Create a new jira ticket record."""
        ticket = JiraTicket(
            finding_id=finding_id,
            workspace_id=workspace_id,
            jira_key=jira_key,
            jira_url=jira_url,
            created_by_user_id=user_id,
        )
        self.db.add(ticket)
        await self.db.flush()
        await self.db.refresh(ticket)
        return ticket

    async def get_by_finding(
        self, finding_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> JiraTicket | None:
        """Return the Jira ticket for a given finding within a workspace."""
        result = await self.db.execute(
            select(JiraTicket).where(
                JiraTicket.finding_id == finding_id,
                JiraTicket.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: uuid.UUID) -> list[JiraTicket]:
        """Return all Jira tickets for a workspace."""
        result = await self.db.execute(
            select(JiraTicket).where(JiraTicket.workspace_id == workspace_id)
        )
        return list(result.scalars().all())
