"""
Jira Integration router — create and manage Jira tickets from findings.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep, require_roles
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.enums import UserRole
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.repositories.jira_ticket_repository import JiraTicketRepository
from app.repositories.workspace_settings_repository import WorkspaceSettingsRepository
from app.schemas.jira import JiraConnectionTestResponse, JiraTicketRequest, JiraTicketResponse
from app.services.jira_service import JiraService

router = APIRouter(prefix="/integrations/jira", tags=["jira"])


def _resolve_workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("User has no workspace assigned")
    return current_user.workspace_id


def _get_jira_service(settings, decrypted_token: str | None = None) -> JiraService | None:
    """Build a JiraService from workspace settings, or return None if not configured."""
    if not all([settings.jira_base_url, settings.jira_email, settings.jira_api_token, settings.jira_project_key]):
        return None
    return JiraService(
        base_url=settings.jira_base_url,
        email=settings.jira_email,
        api_token=decrypted_token or settings.jira_api_token,
        project_key=settings.jira_project_key,
        issue_type=settings.jira_issue_type or "Task",
    )


@router.post(
    "/test-connection",
    response_model=JiraConnectionTestResponse,
    dependencies=[require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)],
)
async def test_jira_connection(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> JiraConnectionTestResponse:
    """Test Jira credentials stored in workspace_settings. Admin only."""
    workspace_id = _resolve_workspace_id(current_user)
    settings_repo = WorkspaceSettingsRepository(db)
    ws_settings = await settings_repo.get_or_create(workspace_id)
    decrypted_token = await settings_repo.get_jira_token_decrypted(workspace_id)
    svc = _get_jira_service(ws_settings, decrypted_token)
    if svc is None:
        raise BadRequestError("Jira not configured")
    result = await svc.test_connection()
    return JiraConnectionTestResponse(ok=result["ok"], message=result["message"])


@router.post(
    "/tickets",
    response_model=JiraTicketResponse,
    dependencies=[require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.ANALYST)],
)
async def create_jira_ticket(
    req: JiraTicketRequest,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> JiraTicketResponse:
    """Create a Jira ticket for a finding. Admin/Analyst only."""
    workspace_id = _resolve_workspace_id(current_user)
    settings_repo = WorkspaceSettingsRepository(db)
    ws_settings = await settings_repo.get_or_create(workspace_id)
    decrypted_token = await settings_repo.get_jira_token_decrypted(workspace_id)
    svc = _get_jira_service(ws_settings, decrypted_token)
    if svc is None:
        return JiraTicketResponse(
            finding_id=req.finding_id,
            error="Jira not configured",
            success=False,
        )

    # Check if ticket already exists
    ticket_repo = JiraTicketRepository(db)
    existing = await ticket_repo.get_by_finding(req.finding_id, workspace_id)
    if existing is not None:
        return JiraTicketResponse(
            finding_id=req.finding_id,
            jira_key=existing.jira_key,
            jira_url=existing.jira_url,
            success=True,
        )

    # Load the finding
    finding_repo = CanonicalFindingRepository(db)
    finding = await finding_repo.get_by_id_and_workspace(req.finding_id, workspace_id)
    if finding is None:
        raise NotFoundError(f"Finding {req.finding_id} not found")

    result = await svc.create_issue(finding)
    if "error" in result:
        return JiraTicketResponse(
            finding_id=req.finding_id,
            error=result["error"],
            success=False,
        )

    # Persist ticket record
    ticket = await ticket_repo.create(
        finding_id=req.finding_id,
        workspace_id=workspace_id,
        jira_key=result["key"],
        jira_url=result["url"],
        user_id=current_user.id,
    )
    return JiraTicketResponse(
        finding_id=req.finding_id,
        jira_key=ticket.jira_key,
        jira_url=ticket.jira_url,
        success=True,
    )


@router.get(
    "/tickets/{finding_id}",
    response_model=JiraTicketResponse,
)
async def get_jira_ticket(
    finding_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> JiraTicketResponse:
    """Get the Jira ticket associated with a finding, or 404."""
    workspace_id = _resolve_workspace_id(current_user)
    ticket_repo = JiraTicketRepository(db)
    ticket = await ticket_repo.get_by_finding(finding_id, workspace_id)
    if ticket is None:
        raise NotFoundError(f"No Jira ticket found for finding {finding_id}")
    return JiraTicketResponse(
        finding_id=finding_id,
        jira_key=ticket.jira_key,
        jira_url=ticket.jira_url,
        success=True,
    )
