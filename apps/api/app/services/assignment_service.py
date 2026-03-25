"""
AssignmentService — business logic for finding assignments.

Rules:
- One active assignment per finding per workspace at a time.
- Reassigning deactivates previous assignment (soft-replace).
- Notifications are created silently (failure never propagates).
"""
import uuid
from typing import TYPE_CHECKING

from app.core.exceptions import NotFoundError
from app.models.notification import Notification
from app.models.user import User
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.repositories.finding_assignment_repository import FindingAssignmentRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.assignment import AssignFindingRequest, AssignmentResponse

if TYPE_CHECKING:
    from app.services.email_service import EmailService


class AssignmentService:
    def __init__(
        self,
        assignment_repo: FindingAssignmentRepository,
        canonical_repo: CanonicalFindingRepository,
        user_repo: UserRepository,
        notification_repo: NotificationRepository | None = None,
        email_service: "EmailService | None" = None,
    ) -> None:
        self._assignment_repo = assignment_repo
        self._canonical_repo = canonical_repo
        self._user_repo = user_repo
        self._notification_repo = notification_repo
        self._email_service = email_service

    async def assign_finding(
        self,
        finding_id: uuid.UUID,
        workspace_id: uuid.UUID,
        req: AssignFindingRequest,
        actor: User,
    ) -> AssignmentResponse:
        # 1. Verify finding belongs to workspace
        finding = await self._canonical_repo.get_by_id_and_workspace(finding_id, workspace_id)
        if not finding:
            raise NotFoundError("Finding not found")

        # 2. Verify assignee belongs to same workspace
        assignee = await self._user_repo.get_by_id(req.assignee_user_id)
        if not assignee or assignee.workspace_id != workspace_id:
            raise NotFoundError("Assignee not found in workspace")

        # 3. Create assignment (deactivates previous)
        record = await self._assignment_repo.assign(
            finding_id=finding_id,
            workspace_id=workspace_id,
            assignee_user_id=req.assignee_user_id,
            assigned_by_user_id=actor.id,
            due_date=req.due_date,
            note=req.note,
        )

        # 4. Create in-app notification for assignee (silently fail if error)
        if self._notification_repo and req.assignee_user_id != actor.id:
            try:
                notif = Notification(
                    workspace_id=workspace_id,
                    user_id=req.assignee_user_id,
                    type="finding_assigned",
                    title="Finding assigned to you",
                    body=f"You have been assigned finding: {finding.title[:80]}",
                    link_path=f"/dashboard/findings/{finding_id}",
                )
                self._notification_repo.db.add(notif)
                await self._notification_repo.db.flush()
            except Exception:
                pass

        # 4c. Fire webhook (fire-and-forget)
        try:
            from app.services.webhook_service import WebhookService
            from app.repositories.webhook_repository import WebhookRepository
            webhook_svc = WebhookService(repo=WebhookRepository(self._assignment_repo.db))
            await webhook_svc.dispatch(
                workspace_id=workspace_id,
                event_name="finding.assigned",
                payload={
                    "finding_id": str(finding_id),
                    "assignee_email": assignee.email,
                }
            )
        except Exception:
            pass

        # 4b. Send email notification to assignee (fire-and-forget)
        if self._email_service and req.assignee_user_id != actor.id:
            try:
                from app.services.email_templates import finding_assigned_email
                due_str = record.due_date.strftime("%B %d, %Y") if record.due_date else None
                subject, html, text = finding_assigned_email(
                    assignee_name=assignee.full_name or assignee.email,
                    finding_title=finding.title,
                    finding_severity=str(finding.severity),
                    assigned_by=actor.email,
                    due_date=due_str,
                    note=record.note,
                    finding_url=f"/dashboard/findings/{finding_id}",
                )
                await self._email_service.send(assignee.email, subject, html, text)
            except Exception:
                pass

        # 5. Build response with denormalised emails and title
        return AssignmentResponse(
            **{k: v for k, v in record.__dict__.items() if not k.startswith("_")},
            assignee_email=assignee.email,
            assigned_by_email=actor.email,
            finding_title=finding.title,
        )

    async def get_assignment(
        self,
        finding_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> AssignmentResponse | None:
        record = await self._assignment_repo.get_active(finding_id, workspace_id)
        if not record:
            return None

        # Enrich with emails and finding title
        assignee = await self._user_repo.get_by_id(record.assignee_user_id)
        assigned_by = None
        if record.assigned_by_user_id:
            assigned_by = await self._user_repo.get_by_id(record.assigned_by_user_id)
        finding = await self._canonical_repo.get_by_id_and_workspace(finding_id, workspace_id)

        return AssignmentResponse(
            **{k: v for k, v in record.__dict__.items() if not k.startswith("_")},
            assignee_email=assignee.email if assignee else None,
            assigned_by_email=assigned_by.email if assigned_by else None,
            finding_title=finding.title if finding else None,
        )

    async def unassign_finding(
        self,
        finding_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> bool:
        return await self._assignment_repo.unassign(finding_id, workspace_id)

    async def list_my_assignments(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> list[AssignmentResponse]:
        records = await self._assignment_repo.list_assigned_to_user(user_id, workspace_id)

        # Enrich each with emails and finding title
        results = []
        actor = await self._user_repo.get_by_id(user_id)
        for record in records:
            assigned_by = None
            if record.assigned_by_user_id:
                assigned_by = await self._user_repo.get_by_id(record.assigned_by_user_id)
            finding = await self._canonical_repo.get_by_id_and_workspace(
                record.finding_id, workspace_id
            )
            results.append(
                AssignmentResponse(
                    **{k: v for k, v in record.__dict__.items() if not k.startswith("_")},
                    assignee_email=actor.email if actor else None,
                    assigned_by_email=assigned_by.email if assigned_by else None,
                    finding_title=finding.title if finding else None,
                )
            )
        return results
