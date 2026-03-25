"""
AWS Account Service — business logic for onboarding and syncing AWS accounts.

Rules:
- One account_id per workspace (12-digit dedup).
- Validation triggers a JobRun immediately after account creation.
- Sync triggers a JobRun that ingests Security Hub findings.
- Status transitions only happen through this service.
- All sync jobs pass enabled_regions from the account record.
"""

import uuid
from datetime import UTC, datetime

import structlog

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.jobs.aws_account_validate_job import AwsAccountValidateJob
from app.jobs.base import JobContext, JobResult, JobStatus, JobType
from app.models.aws_account import AwsAccount
from app.models.enums import AwsAccountStatus, JobRunStatus
from app.models.job_run import JobRun
from app.repositories.aws_account_repository import AwsAccountRepository
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.repositories.job_run_repository import JobRunRepository
from app.repositories.source_finding_repository import SourceFindingRepository
from app.schemas.aws_account import AwsAccountCreate, AwsAccountUpdate

logger = structlog.get_logger(__name__)


class AwsAccountService:
    def __init__(
        self,
        aws_account_repo: AwsAccountRepository,
        job_run_repo: JobRunRepository,
        source_finding_repo: SourceFindingRepository | None = None,
        canonical_finding_repo: CanonicalFindingRepository | None = None,
        audit_log_service=None,
    ) -> None:
        self._accounts = aws_account_repo
        self._job_runs = job_run_repo
        self._source_findings = source_finding_repo
        self._canonical_findings = canonical_finding_repo
        self._audit = audit_log_service

    async def list_accounts(self, workspace_id: uuid.UUID) -> list[AwsAccount]:
        return await self._accounts.list_by_workspace(workspace_id)

    async def get_account(
        self, account_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> AwsAccount:
        account = await self._accounts.get_by_id(account_id)
        if account is None or str(account.workspace_id) != str(workspace_id):
            raise NotFoundError(f"AWS account {account_id} not found")
        return account

    async def create_account(
        self,
        workspace_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: AwsAccountCreate,
        triggered_by: uuid.UUID,
    ) -> tuple[AwsAccount, JobRun]:
        """
        Onboard a new AWS account.
        Returns (account, job_run) where job_run tracks the validation.
        """
        if await self._accounts.account_exists_in_workspace(data.account_id, workspace_id):
            raise ConflictError(
                f"AWS account {data.account_id} already exists in this workspace"
            )

        account = AwsAccount(
            workspace_id=workspace_id,
            account_id=data.account_id,
            account_alias=data.account_alias,
            role_arn=data.role_arn,
            external_id=data.external_id,
            status=AwsAccountStatus.PENDING,
            enabled_regions=data.enabled_regions,
        )
        account = await self._accounts.create(account)
        logger.info("aws_account.created", account_id=account.account_id)

        if self._audit is not None:
            try:
                await self._audit.log(
                    workspace_id=workspace_id,
                    actor_user_id=triggered_by,
                    actor_email="system",
                    action="aws_account.created",
                    resource_type="aws_account",
                    resource_id=account.account_id,
                    detail={"account_alias": account.account_alias},
                )
            except Exception:
                pass

        job_run = JobRun(
            aws_account_id=account.id,
            workspace_id=workspace_id,
            job_type=JobType.AWS_ACCOUNT_VALIDATE,
            status=JobRunStatus.PENDING,
            progress_detail={},
            triggered_by=triggered_by,
        )
        job_run = await self._job_runs.create(job_run)

        await self._run_validation_inline(account, job_run, tenant_id=tenant_id)
        return account, job_run

    async def _run_validation_inline(
        self, account: AwsAccount, job_run: JobRun, *, tenant_id: uuid.UUID
    ) -> None:
        """Run validation in-process (Phase 3 synchronous mode)."""
        await self._accounts.update_status(account.id, AwsAccountStatus.VALIDATING)
        await self._job_runs.mark_running(job_run.id)

        ctx = JobContext(
            tenant_id=tenant_id,
            workspace_id=account.workspace_id,
            job_run_id=job_run.id,
            triggered_by=str(job_run.triggered_by),
            payload={
                "aws_account_id": str(account.id),
                "account_id": account.account_id,
                "role_arn": account.role_arn,
                "external_id": account.external_id,
            },
        )
        job = AwsAccountValidateJob(ctx)
        result = await job.execute()

        if result.status == JobStatus.COMPLETED:
            await self._accounts.update_status(account.id, AwsAccountStatus.ACTIVE)
            await self._job_runs.mark_completed(job_run.id, result.output)
        else:
            await self._accounts.update_status(
                account.id, AwsAccountStatus.ERROR, last_error=result.error
            )
            await self._job_runs.mark_failed(
                job_run.id, result.error or "Unknown error", result.output
            )

    def _require_finding_repos(self) -> None:
        """Raise if finding repositories are not configured."""
        if self._source_findings is None or self._canonical_findings is None:
            raise RuntimeError(
                "AwsAccountService not configured with finding repositories "
                "— pass source_finding_repo and canonical_finding_repo to constructor"
            )

    async def trigger_sync(
        self,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        tenant_id: uuid.UUID,
        triggered_by: uuid.UUID,
    ) -> JobRun:
        """
        Trigger a Security Hub sync job for an account.
        Account must be ACTIVE before syncing. Uses account's enabled_regions.
        """
        account = await self.get_account(account_id, workspace_id)

        if account.status != AwsAccountStatus.ACTIVE:
            raise ConflictError(
                f"Account must be in ACTIVE status to sync "
                f"(current: {account.status})"
            )

        self._require_finding_repos()

        job_run = JobRun(
            aws_account_id=account.id,
            workspace_id=workspace_id,
            job_type=JobType.SECURITY_HUB_SYNC,
            status=JobRunStatus.PENDING,
            progress_detail={},
            triggered_by=triggered_by,
        )
        job_run = await self._job_runs.create(job_run)

        await self._run_sync_inline(
            account=account,
            job_run=job_run,
            tenant_id=tenant_id,
        )
        return job_run

    async def _run_sync_inline(
        self,
        account: AwsAccount,
        job_run: JobRun,
        *,
        tenant_id: uuid.UUID,
    ) -> None:
        """Run Security Hub sync in-process."""
        from app.jobs.security_hub_sync_job import SecurityHubSyncJob

        await self._job_runs.mark_running(job_run.id)

        ctx = JobContext(
            tenant_id=tenant_id,
            workspace_id=account.workspace_id,
            job_run_id=job_run.id,
            triggered_by=str(job_run.triggered_by),
            payload={
                "aws_account_id": str(account.id),
                "account_id": account.account_id,
                "role_arn": account.role_arn,
                "external_id": account.external_id,
                "regions": account.enabled_regions,
            },
        )
        job = SecurityHubSyncJob(
            ctx=ctx,
            source_finding_repo=self._source_findings,
            canonical_finding_repo=self._canonical_findings,
        )
        result = await job.execute()

        if result.status == JobStatus.COMPLETED:
            await self._accounts.update_fields(
                account.id, last_synced_at=datetime.now(UTC).isoformat()
            )
            await self._job_runs.mark_completed(job_run.id, result.output)
        else:
            await self._job_runs.mark_failed(
                job_run.id, result.error or "Sync failed", result.output
            )

    async def trigger_config_sync(
        self,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        tenant_id: uuid.UUID,
        triggered_by: uuid.UUID,
    ) -> JobRun:
        """
        Trigger an AWS Config sync job for an account.
        Account must be ACTIVE before syncing. Uses account's enabled_regions.
        """
        account = await self.get_account(account_id, workspace_id)

        if account.status != AwsAccountStatus.ACTIVE:
            raise ConflictError(
                f"Account must be in ACTIVE status to sync "
                f"(current: {account.status})"
            )

        self._require_finding_repos()

        job_run = JobRun(
            aws_account_id=account.id,
            workspace_id=workspace_id,
            job_type=JobType.CONFIG_SYNC,
            status=JobRunStatus.PENDING,
            progress_detail={},
            triggered_by=triggered_by,
        )
        job_run = await self._job_runs.create(job_run)

        await self._run_config_sync_inline(
            account=account,
            job_run=job_run,
            tenant_id=tenant_id,
        )
        return job_run

    async def _run_config_sync_inline(
        self,
        account: AwsAccount,
        job_run: JobRun,
        *,
        tenant_id: uuid.UUID,
    ) -> None:
        """Run AWS Config sync in-process."""
        from app.jobs.config_sync_job import ConfigSyncJob

        await self._job_runs.mark_running(job_run.id)

        ctx = JobContext(
            tenant_id=tenant_id,
            workspace_id=account.workspace_id,
            job_run_id=job_run.id,
            triggered_by=str(job_run.triggered_by),
            payload={
                "aws_account_id": str(account.id),
                "account_id": account.account_id,
                "role_arn": account.role_arn,
                "external_id": account.external_id,
                "regions": account.enabled_regions,
            },
        )
        job = ConfigSyncJob(
            ctx=ctx,
            source_finding_repo=self._source_findings,
            canonical_finding_repo=self._canonical_findings,
        )
        result = await job.execute()

        if result.status == JobStatus.COMPLETED:
            await self._accounts.update_fields(
                account.id, last_synced_at=datetime.now(UTC).isoformat()
            )
            await self._job_runs.mark_completed(job_run.id, result.output)
        else:
            await self._job_runs.mark_failed(
                job_run.id, result.error or "Config sync failed", result.output
            )

    async def trigger_guardduty_sync(
        self,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        tenant_id: uuid.UUID,
        triggered_by: uuid.UUID,
    ) -> JobRun:
        """
        Trigger a GuardDuty sync job for an account.
        Account must be ACTIVE before syncing. Uses account's enabled_regions.
        """
        account = await self.get_account(account_id, workspace_id)

        if account.status != AwsAccountStatus.ACTIVE:
            raise ConflictError(
                f"Account must be in ACTIVE status to sync "
                f"(current: {account.status})"
            )

        self._require_finding_repos()

        job_run = JobRun(
            aws_account_id=account.id,
            workspace_id=workspace_id,
            job_type=JobType.GUARDDUTY_SYNC,
            status=JobRunStatus.PENDING,
            progress_detail={},
            triggered_by=triggered_by,
        )
        job_run = await self._job_runs.create(job_run)

        await self._run_guardduty_sync_inline(
            account=account,
            job_run=job_run,
            tenant_id=tenant_id,
        )
        return job_run

    async def _run_guardduty_sync_inline(
        self,
        account: AwsAccount,
        job_run: JobRun,
        *,
        tenant_id: uuid.UUID,
    ) -> None:
        """Run GuardDuty sync in-process."""
        from app.jobs.guardduty_sync_job import GuardDutySyncJob

        await self._job_runs.mark_running(job_run.id)

        ctx = JobContext(
            tenant_id=tenant_id,
            workspace_id=account.workspace_id,
            job_run_id=job_run.id,
            triggered_by=str(job_run.triggered_by),
            payload={
                "aws_account_id": str(account.id),
                "account_id": account.account_id,
                "role_arn": account.role_arn,
                "external_id": account.external_id,
                "regions": account.enabled_regions,
            },
        )
        job = GuardDutySyncJob(
            ctx=ctx,
            source_finding_repo=self._source_findings,
            canonical_finding_repo=self._canonical_findings,
        )
        result = await job.execute()

        if result.status == JobStatus.COMPLETED:
            await self._accounts.update_fields(
                account.id, last_synced_at=datetime.now(UTC).isoformat()
            )
            await self._job_runs.mark_completed(job_run.id, result.output)
        else:
            await self._job_runs.mark_failed(
                job_run.id, result.error or "GuardDuty sync failed", result.output
            )

    async def trigger_inspector_sync(
        self,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        tenant_id: uuid.UUID,
        triggered_by: uuid.UUID,
    ) -> JobRun:
        """
        Trigger an Inspector v2 sync job for an account.
        Account must be ACTIVE before syncing. Uses account's enabled_regions.
        """
        account = await self.get_account(account_id, workspace_id)

        if account.status != AwsAccountStatus.ACTIVE:
            raise ConflictError(
                f"Account must be in ACTIVE status to sync "
                f"(current: {account.status})"
            )

        self._require_finding_repos()

        job_run = JobRun(
            aws_account_id=account.id,
            workspace_id=workspace_id,
            job_type=JobType.INSPECTOR_SYNC,
            status=JobRunStatus.PENDING,
            progress_detail={},
            triggered_by=triggered_by,
        )
        job_run = await self._job_runs.create(job_run)

        await self._run_inspector_sync_inline(
            account=account,
            job_run=job_run,
            tenant_id=tenant_id,
        )
        return job_run

    async def _run_inspector_sync_inline(
        self,
        account: AwsAccount,
        job_run: JobRun,
        *,
        tenant_id: uuid.UUID,
    ) -> None:
        """Run Inspector v2 sync in-process."""
        from app.jobs.inspector_sync_job import InspectorSyncJob

        await self._job_runs.mark_running(job_run.id)

        ctx = JobContext(
            tenant_id=tenant_id,
            workspace_id=account.workspace_id,
            job_run_id=job_run.id,
            triggered_by=str(job_run.triggered_by),
            payload={
                "aws_account_id": str(account.id),
                "account_id": account.account_id,
                "role_arn": account.role_arn,
                "external_id": account.external_id,
                "regions": account.enabled_regions,
            },
        )
        job = InspectorSyncJob(
            ctx=ctx,
            source_finding_repo=self._source_findings,
            canonical_finding_repo=self._canonical_findings,
        )
        result = await job.execute()

        if result.status == JobStatus.COMPLETED:
            await self._accounts.update_fields(
                account.id, last_synced_at=datetime.now(UTC).isoformat()
            )
            await self._job_runs.mark_completed(job_run.id, result.output)
        else:
            await self._job_runs.mark_failed(
                job_run.id, result.error or "Inspector sync failed", result.output
            )

    async def update_account(
        self,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        data: AwsAccountUpdate,
    ) -> AwsAccount:
        account = await self.get_account(account_id, workspace_id)
        fields = data.model_dump(exclude_unset=True)
        if not fields:
            return account
        return await self._accounts.update_fields(account.id, **fields)

    async def delete_account(
        self, account_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> None:
        account = await self.get_account(account_id, workspace_id)
        await self._accounts.delete(account.id)
        logger.info("aws_account.deleted", account_id=str(account_id))

        if self._audit is not None:
            try:
                await self._audit.log(
                    workspace_id=workspace_id,
                    actor_user_id=None,
                    actor_email="system",
                    action="aws_account.deleted",
                    resource_type="aws_account",
                    resource_id=str(account_id),
                    detail={"account_id": str(account_id)},
                )
            except Exception:
                pass

    async def list_job_runs(
        self, account_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> list[JobRun]:
        await self.get_account(account_id, workspace_id)
        return await self._job_runs.list_by_aws_account(account_id)
