"""
Inspector Sync Job — ingests active findings from AWS Inspector v2.

Lifecycle:
  1. Assume cross-account role via StsClient
  2. For each enabled region: iterate active Inspector findings
  3. Upsert each finding into source_findings table
  4. Run normalization pass after ingestion completes

Inspector v2 notes:
  - Uses `inspector2` boto3 service (not classic `inspector`)
  - list_findings with findingStatus=ACTIVE, paginated via nextToken
  - AccessDeniedException is treated as "Inspector not enabled" — non-fatal per region
"""

import uuid

from app.integrations.aws.inspector_client import InspectorClient
from app.integrations.aws.sts_client import StsAssumeRoleError, StsClient
from app.jobs.base import BaseJob, JobContext, JobResult, JobStatus, JobType
from app.jobs.registry import register_job
from app.models.enums import FindingSource
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.repositories.source_finding_repository import SourceFindingRepository
from app.services.normalization_service import NormalizationService


@register_job(JobType.INSPECTOR_SYNC)
class InspectorSyncJob(BaseJob):
    """
    Ingests Inspector v2 findings for a given AWS account across all enabled regions.

    ctx.payload expected keys:
      - aws_account_id: str  (UUID of AwsAccount DB record)
      - account_id:     str  (12-digit AWS account number)
      - role_arn:       str
      - external_id:    str | None
      - regions:        list[str]  (default ["us-east-1"])
      - region:         str  (legacy single-region fallback)
    """

    job_type = JobType.INSPECTOR_SYNC

    def __init__(
        self,
        ctx: JobContext,
        source_finding_repo: SourceFindingRepository,
        canonical_finding_repo: CanonicalFindingRepository,
    ) -> None:
        super().__init__(ctx)
        self._source_repo = source_finding_repo
        self._canonical_repo = canonical_finding_repo
        self._normalizer = NormalizationService(source_finding_repo, canonical_finding_repo)

    def _timeout_seconds(self) -> int:
        return 600

    async def run(self) -> JobResult:
        aws_account_db_id: str | None = self.ctx.payload.get("aws_account_id")
        role_arn: str | None = self.ctx.payload.get("role_arn")
        external_id: str | None = self.ctx.payload.get("external_id")

        # Multi-region support: prefer "regions" list, fall back to single "region"
        regions: list[str] = (
            self.ctx.payload.get("regions")
            or [self.ctx.payload.get("region", "us-east-1")]
        )

        if not aws_account_db_id or not role_arn:
            return JobResult(
                status=JobStatus.FAILED,
                error="Missing required payload keys: aws_account_id, role_arn",
            )

        aws_account_uuid = uuid.UUID(aws_account_db_id)

        progress: dict = {
            "regions_processed": [],
            "findings_ingested": 0,
            "findings_skipped": 0,
            "normalization": {},
            "error": None,
        }

        self.emit_progress("Starting Inspector sync: assuming role", pct=5)

        # ── Step 1: Assume Role ─────────────────────────────────────────────
        try:
            sts = StsClient.from_settings()
            session_name = f"CloudPostureInspSync-{str(uuid.uuid4())[:8]}"
            credentials = await sts.assume_role(
                role_arn=role_arn,
                session_name=session_name,
                external_id=external_id,
            )
        except StsAssumeRoleError as exc:
            progress["error"] = str(exc)
            return JobResult(
                status=JobStatus.FAILED,
                error=f"AssumeRole failed: {exc}",
                output=progress,
            )

        self.emit_progress(
            f"Role assumed; scanning {len(regions)} region(s) with Inspector v2", pct=10
        )

        # ── Step 2: Ingest findings per region ─────────────────────────────
        base_pct = 10
        pct_per_region = max(1, 65 // len(regions))

        for idx, region in enumerate(regions):
            self.emit_progress(
                f"Inspector sync: region {region} ({idx + 1}/{len(regions)})",
                pct=base_pct + idx * pct_per_region,
            )
            inspector_client = InspectorClient.from_credentials(credentials, region=region)
            region_ingested = 0

            try:
                async for finding in inspector_client.iter_active_findings():
                    try:
                        await self._source_repo.upsert(
                            aws_account_id=aws_account_uuid,
                            workspace_id=self.ctx.workspace_id,
                            source=FindingSource.INSPECTOR,
                            native_finding_id=finding.native_id,
                            severity=finding.severity,
                            title=finding.title,
                            description=finding.description,
                            raw_payload={
                                **finding.raw_payload,
                                "finding_type": finding.finding_type,
                            },
                            region=finding.region,
                            resource_arn=finding.resource_arn,
                            resource_type=finding.resource_type,
                            first_observed_at=finding.first_observed_at,
                            last_observed_at=finding.last_observed_at,
                        )
                        progress["findings_ingested"] += 1
                        region_ingested += 1

                        if region_ingested % 50 == 0:
                            self.emit_progress(
                                f"Inspector {region}: {region_ingested} findings",
                                pct=min(
                                    base_pct + idx * pct_per_region + 5,
                                    80,
                                ),
                            )

                    except Exception as exc:
                        progress["findings_skipped"] += 1
                        self._log.warning(
                            "inspector_sync.finding_skip",
                            native_id=finding.native_id,
                            region=region,
                            error=str(exc),
                        )

                progress["regions_processed"].append({
                    "region": region,
                    "ingested": region_ingested,
                })
                self._log.info(
                    "inspector_sync.region_done",
                    region=region,
                    ingested=region_ingested,
                )

            except Exception as exc:
                # Per-region failures are non-fatal (Inspector may not be enabled)
                self._log.warning(
                    "inspector_sync.region_error",
                    region=region,
                    error=str(exc),
                )
                progress["regions_processed"].append({
                    "region": region,
                    "ingested": 0,
                    "error": str(exc),
                })

        self.emit_progress(
            f"Ingestion complete: {progress['findings_ingested']} findings; running normalization",
            pct=80,
        )

        # ── Step 3: Normalization pass ──────────────────────────────────────
        try:
            norm_stats = await self._normalizer.normalize_account(
                aws_account_id=aws_account_uuid,
                workspace_id=self.ctx.workspace_id,
            )
            progress["normalization"] = norm_stats
        except Exception as exc:
            self._log.error("inspector_sync.normalization_error", error=str(exc))
            progress["normalization"] = {"error": str(exc)}

        self.emit_progress("Inspector sync complete", pct=100)

        # Fire-and-forget: mark step_first_sync_complete in onboarding
        if progress["findings_ingested"] > 0:
            try:
                from app.repositories.onboarding_repository import OnboardingRepository
                onboarding_repo = OnboardingRepository(self._canonical_repo.db)
                await onboarding_repo.mark_step(self.ctx.workspace_id, "step_first_sync_complete")
            except Exception:
                pass

        return JobResult(
            status=JobStatus.COMPLETED,
            message=(
                f"Inspector sync complete: "
                f"{progress['findings_ingested']} ingested, "
                f"{progress['findings_skipped']} skipped, "
                f"{len(regions)} region(s)"
            ),
            output=progress,
        )
