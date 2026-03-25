"""
FindingCommentRepository — data access for finding_comments table.
"""
import uuid

from sqlalchemy import select

from app.models.finding_comment import FindingComment
from app.repositories.base import BaseRepository


class FindingCommentRepository(BaseRepository[FindingComment]):
    model = FindingComment

    async def add(
        self,
        finding_id: uuid.UUID,
        user_id: uuid.UUID | None,
        workspace_id: uuid.UUID,
        body: str,
    ) -> FindingComment:
        comment = FindingComment(
            finding_id=finding_id,
            user_id=user_id,
            workspace_id=workspace_id,
            body=body,
        )
        self.db.add(comment)
        await self.db.flush()
        await self.db.refresh(comment)
        return comment

    async def list_by_finding(
        self, finding_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> list[FindingComment]:
        result = await self.db.execute(
            select(FindingComment)
            .where(
                FindingComment.finding_id == finding_id,
                FindingComment.workspace_id == workspace_id,
            )
            .order_by(FindingComment.created_at.asc())
        )
        return list(result.scalars().all())

    async def delete(
        self,
        comment_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Only the comment owner can delete their comment."""
        result = await self.db.execute(
            select(FindingComment).where(
                FindingComment.id == comment_id,
                FindingComment.workspace_id == workspace_id,
                FindingComment.user_id == user_id,
            )
        )
        comment = result.scalar_one_or_none()
        if comment is None:
            return False
        await self.db.delete(comment)
        await self.db.flush()
        return True
