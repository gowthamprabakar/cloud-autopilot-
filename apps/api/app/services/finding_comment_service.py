"""
FindingCommentService — business logic for finding comments.
"""
import uuid

from app.core.exceptions import NotFoundError
from app.repositories.finding_comment_repository import FindingCommentRepository
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.repositories.user_repository import UserRepository
from app.schemas.finding_comment import FindingCommentCreate, FindingCommentResponse


class FindingCommentService:
    def __init__(
        self,
        comment_repo: FindingCommentRepository,
        canonical_repo: CanonicalFindingRepository,
        user_repo: UserRepository,
    ) -> None:
        self.comment_repo = comment_repo
        self.canonical_repo = canonical_repo
        self.user_repo = user_repo

    async def add_comment(
        self,
        finding_id: uuid.UUID,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        req: FindingCommentCreate,
    ) -> FindingCommentResponse:
        # Verify finding belongs to this workspace
        finding = await self.canonical_repo.get_by_id_and_workspace(
            finding_id, workspace_id
        )
        if finding is None:
            raise NotFoundError(f"Finding {finding_id} not found")

        comment = await self.comment_repo.add(finding_id, user_id, workspace_id, req.body)
        user = await self.user_repo.get_by_id(user_id)
        return FindingCommentResponse(
            id=comment.id,
            finding_id=comment.finding_id,
            user_id=comment.user_id,
            body=comment.body,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            author_email=user.email if user else None,
        )

    async def list_comments(
        self,
        finding_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> list[FindingCommentResponse]:
        # Verify finding belongs to this workspace
        finding = await self.canonical_repo.get_by_id_and_workspace(
            finding_id, workspace_id
        )
        if finding is None:
            raise NotFoundError(f"Finding {finding_id} not found")

        comments = await self.comment_repo.list_by_finding(finding_id, workspace_id)
        return [
            FindingCommentResponse(
                id=c.id,
                finding_id=c.finding_id,
                user_id=c.user_id,
                body=c.body,
                created_at=c.created_at,
                updated_at=c.updated_at,
                author_email=None,  # Not enriched in list for performance
            )
            for c in comments
        ]

    async def delete_comment(
        self,
        comment_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        return await self.comment_repo.delete(comment_id, workspace_id, user_id)
