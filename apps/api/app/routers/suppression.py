"""
Suppression rules router — workspace-scoped suppression rule management.

All endpoints require authentication. Admin-only operations are guarded by
require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN).
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep, require_roles
from app.core.exceptions import ForbiddenError
from app.models.enums import UserRole
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.repositories.suppression_rule_repository import SuppressionRuleRepository
from app.schemas.suppression_rule import SuppressionRuleCreate, SuppressionRuleResponse
from app.services.suppression_service import SuppressionService

router = APIRouter(prefix="/suppression-rules", tags=["suppression"])


def _svc(db: AsyncSession = Depends(get_db)) -> SuppressionService:
    return SuppressionService(
        repo=SuppressionRuleRepository(db),
        finding_repo=CanonicalFindingRepository(db),
    )


def _resolve_workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    return current_user.workspace_id


@router.get("", response_model=list[SuppressionRuleResponse])
async def list_suppression_rules(
    current_user: CurrentUserDep,
    svc: SuppressionService = Depends(_svc),
) -> list[SuppressionRuleResponse]:
    """List all suppression rules for the current workspace."""
    workspace_id = _resolve_workspace_id(current_user)
    rules = await svc.list_rules(workspace_id)
    return [SuppressionRuleResponse.model_validate(r) for r in rules]


@router.post(
    "",
    response_model=SuppressionRuleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)],
)
async def create_suppression_rule(
    req: SuppressionRuleCreate,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
    svc: SuppressionService = Depends(_svc),
) -> SuppressionRuleResponse:
    """Create a new suppression rule. Admin only."""
    workspace_id = _resolve_workspace_id(current_user)
    rule = await svc.create_rule(
        workspace_id=workspace_id,
        created_by=current_user.id,
        data=req,
    )
    try:
        from app.services.webhook_service import WebhookService
        from app.repositories.webhook_repository import WebhookRepository
        webhook_svc = WebhookService(repo=WebhookRepository(db))
        await webhook_svc.dispatch(
            workspace_id=current_user.workspace_id,
            event_name="suppression.applied",
            payload={"rule_id": str(rule.id), "title": rule.title}
        )
    except Exception:
        pass
    return SuppressionRuleResponse.model_validate(rule)


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)],
)
async def delete_suppression_rule(
    rule_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: SuppressionService = Depends(_svc),
) -> None:
    """Soft-delete a suppression rule. Admin only."""
    workspace_id = _resolve_workspace_id(current_user)
    await svc.delete_rule(rule_id=rule_id, workspace_id=workspace_id)


@router.post(
    "/apply",
    status_code=status.HTTP_200_OK,
    dependencies=[require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)],
)
async def apply_suppression_rules(
    current_user: CurrentUserDep,
    svc: SuppressionService = Depends(_svc),
) -> dict:
    """Apply all active suppression rules to OPEN findings now. Admin only."""
    workspace_id = _resolve_workspace_id(current_user)
    suppressed = await svc.apply_rules_to_workspace(workspace_id)
    return {"suppressed": suppressed}
