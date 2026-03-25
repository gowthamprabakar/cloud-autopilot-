"""
AWS Accounts router — workspace-scoped onboarding, management, and sync.

All endpoints require authentication. workspace_id is scoped to
current_user.workspace_id.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.rate_limit import rate_limit
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.aws_account_repository import AwsAccountRepository
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.repositories.job_run_repository import JobRunRepository
from app.repositories.source_finding_repository import SourceFindingRepository
from app.schemas.aws_account import (
    AwsAccountCreate,
    AwsAccountResponse,
    AwsAccountUpdate,
    JobRunResponse,
)
from app.services.audit_log_service import AuditLogService
from app.services.aws_account_service import AwsAccountService

router = APIRouter(prefix="/aws-accounts", tags=["aws-accounts"])


def _svc(db: AsyncSession = Depends(get_db)) -> AwsAccountService:
    audit_svc = AuditLogService(AuditLogRepository(db))
    return AwsAccountService(
        aws_account_repo=AwsAccountRepository(db),
        job_run_repo=JobRunRepository(db),
        source_finding_repo=SourceFindingRepository(db),
        canonical_finding_repo=CanonicalFindingRepository(db),
        audit_log_service=audit_svc,
    )


def _resolve_workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("User has no workspace assigned")
    return current_user.workspace_id


@router.get("", response_model=list[AwsAccountResponse])
async def list_accounts(
    current_user: CurrentUserDep,
    svc: AwsAccountService = Depends(_svc),
) -> list[AwsAccountResponse]:
    workspace_id = _resolve_workspace_id(current_user)
    return await svc.list_accounts(workspace_id)


@router.post("", response_model=AwsAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    req: AwsAccountCreate,
    current_user: CurrentUserDep,
    svc: AwsAccountService = Depends(_svc),
    db: AsyncSession = Depends(get_db),
) -> AwsAccountResponse:
    workspace_id = _resolve_workspace_id(current_user)
    account, _job_run = await svc.create_account(
        workspace_id=workspace_id,
        tenant_id=current_user.tenant_id,
        data=req,
        triggered_by=current_user.id,
    )
    # Fire-and-forget: mark aws_account_connected step in onboarding
    try:
        from app.repositories.onboarding_repository import OnboardingRepository
        onboarding_repo = OnboardingRepository(db)
        await onboarding_repo.mark_step(workspace_id, "step_aws_account_connected")
    except Exception:
        pass
    return account


@router.get("/{account_id}", response_model=AwsAccountResponse)
async def get_account(
    account_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: AwsAccountService = Depends(_svc),
) -> AwsAccountResponse:
    workspace_id = _resolve_workspace_id(current_user)
    return await svc.get_account(account_id, workspace_id)


@router.patch("/{account_id}", response_model=AwsAccountResponse)
async def update_account(
    account_id: uuid.UUID,
    req: AwsAccountUpdate,
    current_user: CurrentUserDep,
    svc: AwsAccountService = Depends(_svc),
) -> AwsAccountResponse:
    workspace_id = _resolve_workspace_id(current_user)
    return await svc.update_account(account_id, workspace_id, req)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: AwsAccountService = Depends(_svc),
) -> None:
    workspace_id = _resolve_workspace_id(current_user)
    await svc.delete_account(account_id, workspace_id)


@router.post(
    "/{account_id}/sync",
    response_model=JobRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_sync(
    account_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: AwsAccountService = Depends(_svc),
    _: None = Depends(rate_limit(10, 60)),
) -> JobRunResponse:
    """Trigger Security Hub sync job for this account. Uses account's enabled_regions."""
    workspace_id = _resolve_workspace_id(current_user)
    job_run = await svc.trigger_sync(
        account_id=account_id,
        workspace_id=workspace_id,
        tenant_id=current_user.tenant_id,
        triggered_by=current_user.id,
    )
    return job_run


@router.post(
    "/{account_id}/sync/config",
    response_model=JobRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_config_sync(
    account_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: AwsAccountService = Depends(_svc),
    _: None = Depends(rate_limit(10, 60)),
) -> JobRunResponse:
    """Trigger AWS Config sync job for this account. Uses account's enabled_regions."""
    workspace_id = _resolve_workspace_id(current_user)
    job_run = await svc.trigger_config_sync(
        account_id=account_id,
        workspace_id=workspace_id,
        tenant_id=current_user.tenant_id,
        triggered_by=current_user.id,
    )
    return job_run


@router.post(
    "/{account_id}/sync/guardduty",
    response_model=JobRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_guardduty_sync(
    account_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: AwsAccountService = Depends(_svc),
    _: None = Depends(rate_limit(10, 60)),
) -> JobRunResponse:
    """Trigger GuardDuty sync job for this account. Uses account's enabled_regions."""
    workspace_id = _resolve_workspace_id(current_user)
    job_run = await svc.trigger_guardduty_sync(
        account_id=account_id,
        workspace_id=workspace_id,
        tenant_id=current_user.tenant_id,
        triggered_by=current_user.id,
    )
    return job_run


@router.post(
    "/{account_id}/sync/inspector",
    response_model=JobRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_inspector_sync(
    account_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: AwsAccountService = Depends(_svc),
    _: None = Depends(rate_limit(10, 60)),
) -> JobRunResponse:
    """Trigger Inspector v2 sync job for this account. Uses account's enabled_regions."""
    workspace_id = _resolve_workspace_id(current_user)
    job_run = await svc.trigger_inspector_sync(
        account_id=account_id,
        workspace_id=workspace_id,
        tenant_id=current_user.tenant_id,
        triggered_by=current_user.id,
    )
    return job_run


@router.get("/{account_id}/job-runs", response_model=list[JobRunResponse])
async def list_job_runs(
    account_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: AwsAccountService = Depends(_svc),
) -> list[JobRunResponse]:
    workspace_id = _resolve_workspace_id(current_user)
    return await svc.list_job_runs(account_id, workspace_id)
