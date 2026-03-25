"""
AWS Account Validate Job — verifies cross-account role access via real STS.

Lifecycle:
  1. STS AssumeRole with provided role_arn + optional external_id
  2. GetCallerIdentity to confirm the assumed account matches account_id
  3. Check Security Hub is accessible (optional — access-denied is non-fatal)
  5. Write progress_detail at each step (MiroFish pattern)

Returns COMPLETED if STS succeeds. Returns FAILED if AssumeRole is denied.
Security Hub check failure is logged but does not fail the job (it may not
be enabled yet in the account).
"""

import uuid

import aiobotocore.session as aio_session

from app.integrations.aws.sts_client import StsAssumeRoleError, StsClient
from app.jobs.base import BaseJob, JobContext, JobResult, JobStatus, JobType
from app.jobs.registry import register_job


@register_job(JobType.AWS_ACCOUNT_VALIDATE)
class AwsAccountValidateJob(BaseJob):
    """
    Validates that the platform can assume the configured role in the target
    AWS account. Uses bootstrap credentials from settings (or env IRSA in prod).

    ctx.payload expected keys:
      - aws_account_id: str (UUID of AwsAccount record)
      - account_id: str (12-digit AWS account number — used for identity check)
      - role_arn: str
      - external_id: str | None
    """

    job_type = JobType.AWS_ACCOUNT_VALIDATE

    def _timeout_seconds(self) -> int:
        return 120

    async def run(self) -> JobResult:
        role_arn: str | None = self.ctx.payload.get("role_arn")
        account_id: str | None = self.ctx.payload.get("account_id")
        external_id: str | None = self.ctx.payload.get("external_id")

        if not role_arn:
            return JobResult(
                status=JobStatus.FAILED,
                error="Missing required payload key: role_arn",
            )

        progress: dict = {
            "steps": {
                "sts_assume_role": "pending",
                "get_caller_identity": "pending",
                "account_id_match": "pending",
                "security_hub_check": "skipped",
            },
            "assumed_role_arn": None,
            "verified_account_id": None,
            "error": None,
        }

        session_name = f"CloudPosture-{str(uuid.uuid4())[:8]}"
        self.emit_progress("Starting STS AssumeRole", pct=10)

        # ── Step 1: STS AssumeRole ──────────────────────────────
        try:
            sts = StsClient.from_settings()
            credentials = await sts.assume_role(
                role_arn=role_arn,
                session_name=session_name,
                external_id=external_id,
            )
            progress["steps"]["sts_assume_role"] = "ok"
            progress["assumed_role_arn"] = credentials.assumed_role_arn
            self.emit_progress("AssumeRole succeeded", pct=40)
        except StsAssumeRoleError as exc:
            progress["steps"]["sts_assume_role"] = "failed"
            progress["error"] = str(exc)
            return JobResult(
                status=JobStatus.FAILED,
                error=f"STS AssumeRole failed: {exc}",
                output=progress,
            )
        except Exception as exc:
            progress["steps"]["sts_assume_role"] = "failed"
            progress["error"] = str(exc)
            return JobResult(
                status=JobStatus.FAILED,
                error=f"Unexpected error during AssumeRole: {exc}",
                output=progress,
            )

        # ── Step 2: GetCallerIdentity ───────────────────────────
        self.emit_progress("Verifying caller identity", pct=60)
        try:
            identity = await sts.get_caller_identity(credentials)
            progress["steps"]["get_caller_identity"] = "ok"
            progress["verified_account_id"] = identity["Account"]
            self.emit_progress("GetCallerIdentity confirmed", pct=75)
        except StsAssumeRoleError as exc:
            progress["steps"]["get_caller_identity"] = "failed"
            progress["error"] = str(exc)
            return JobResult(
                status=JobStatus.FAILED,
                error=f"GetCallerIdentity failed: {exc}",
                output=progress,
            )

        # ── Step 3: Verify account_id matches ──────────────────
        if account_id and identity["Account"] != account_id:
            progress["steps"]["account_id_match"] = "failed"
            progress["error"] = (
                f"Role ARN belongs to account {identity['Account']}, "
                f"expected {account_id}"
            )
            return JobResult(
                status=JobStatus.FAILED,
                error=progress["error"],
                output=progress,
            )
        progress["steps"]["account_id_match"] = "ok"
        self.emit_progress("Account identity verified", pct=90)

        # ── Step 4: Security Hub check (non-fatal) ──────────────
        try:
            session = aio_session.get_session()
            async with session.create_client(
                "securityhub",
                region_name="us-east-1",
                aws_access_key_id=credentials.access_key_id,
                aws_secret_access_key=credentials.secret_access_key,
                aws_session_token=credentials.session_token,
            ) as hub_client:
                await hub_client.describe_hub()
            progress["steps"]["security_hub_check"] = "ok"
        except Exception as exc:
            # Access denied or not enabled — non-fatal
            progress["steps"]["security_hub_check"] = f"warn:{type(exc).__name__}"

        self.emit_progress("Validation complete", pct=100)
        return JobResult(
            status=JobStatus.COMPLETED,
            message="AWS account access validated successfully",
            output=progress,
        )
