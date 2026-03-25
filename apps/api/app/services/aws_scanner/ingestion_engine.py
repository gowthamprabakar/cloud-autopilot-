"""
IngestionEngine — orchestrates all 5 AWS scanners for a workspace.

Flow:
  1. Create ScanJob (status=running)
  2. Fetch all active AWS accounts for the workspace
  3. For each account, build boto3 clients (LocalStack or real AWS)
  4. Run all 5 scanners concurrently with asyncio.gather
  5. Deduplicate via fingerprint upsert into canonical_findings
  6. Update ScanJob (status=completed, counts)
  7. Return ScanJobResult

Deduplication key: fingerprint column (SHA256 of source:external_id).
Seeded demo findings have fingerprint='' — they are never matched and never overwritten.
"""

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

import boto3
from botocore.config import Config as BotoConfig
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.canonical_finding import CanonicalFinding
from app.models.scan_job import ScanJob
from app.models.aws_account import AwsAccount
from app.services.aws_scanner.security_hub_scanner import SecurityHubScanner
from app.services.aws_scanner.guardduty_scanner import GuardDutyScanner
from app.services.aws_scanner.inspector_scanner import InspectorScanner
from app.services.aws_scanner.config_scanner import ConfigScanner
from app.services.aws_scanner.iam_access_analyzer_scanner import IAMAccessAnalyzerScanner

logger = logging.getLogger(__name__)

# LocalStack endpoint — set LOCALSTACK_ENDPOINT=http://localhost:4566 in .env
LOCALSTACK_ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT")
BOTO_CONFIG = BotoConfig(retries={"max_attempts": 2, "mode": "standard"})


@dataclass
class ScanJobResult:
    job_id: str
    status: str
    findings_added: int = 0
    findings_updated: int = 0
    findings_total: int = 0
    sources_scanned: list[str] = field(default_factory=list)
    sources_failed: list[str] = field(default_factory=list)
    error_message: str | None = None
    duration_seconds: float = 0.0


class IngestionEngine:
    """Coordinates all 5 AWS scanners for a workspace."""

    def __init__(
        self,
        db: AsyncSession,
        workspace_id: str,
        aws_account_id: str | None = None,
    ) -> None:
        self.db = db
        self.workspace_id = workspace_id
        self.aws_account_id = aws_account_id  # None = scan all accounts

    # ── Public entry point ──────────────────────────────────────────────────

    async def run_full_scan(self, triggered_by: str = "manual") -> ScanJobResult:
        started_at = datetime.now(UTC)
        job = await self._create_scan_job(triggered_by, started_at)

        try:
            accounts = await self._fetch_accounts()
            if not accounts:
                return await self._finish_job(
                    job, started_at,
                    status="failed",
                    error="No active AWS accounts found for workspace",
                )

            all_findings: list[dict] = []
            sources_scanned: list[str] = []
            sources_failed: list[str] = []

            for account in accounts:
                account_findings, s_ok, s_fail = await self._scan_account(account)
                all_findings.extend(account_findings)
                for s in s_ok:
                    if s not in sources_scanned:
                        sources_scanned.append(s)
                for s in s_fail:
                    if s not in sources_failed:
                        sources_failed.append(s)

            added, updated = await self._upsert_all(all_findings)

            status = "completed" if not sources_failed else "partial"
            return await self._finish_job(
                job, started_at,
                status=status,
                findings_added=added,
                findings_updated=updated,
                findings_total=len(all_findings),
                sources_scanned=sources_scanned,
                sources_failed=sources_failed,
            )

        except Exception as exc:
            logger.exception("IngestionEngine fatal error for workspace=%s", self.workspace_id)
            return await self._finish_job(
                job, started_at,
                status="failed",
                error=str(exc),
            )

    # ── Account scanning ────────────────────────────────────────────────────

    async def _scan_account(
        self, account: AwsAccount
    ) -> tuple[list[dict], list[str], list[str]]:
        """Run all 5 scanners for one AWS account concurrently."""
        account_id_str = account.account_id
        # enabled_regions is a list — use the first one (default: us-east-1)
        regions = account.enabled_regions or ["us-east-1"]
        region = regions[0] if regions else "us-east-1"
        workspace_id = str(account.workspace_id)
        aws_account_uuid = str(account.id)

        # Build scanner instances
        scanners = {
            "security_hub": SecurityHubScanner(
                self._make_client("securityhub", region),
                account_id_str, region, workspace_id, aws_account_uuid,
            ),
            "guard_duty": GuardDutyScanner(
                self._make_client("guardduty", region),
                account_id_str, region, workspace_id, aws_account_uuid,
            ),
            "inspector": InspectorScanner(
                self._make_client("inspector2", region),
                account_id_str, region, workspace_id, aws_account_uuid,
            ),
            "config": ConfigScanner(
                self._make_client("config", region),
                account_id_str, region, workspace_id, aws_account_uuid,
            ),
            "iam_access_analyzer": IAMAccessAnalyzerScanner(
                self._make_client("accessanalyzer", region),
                account_id_str, region, workspace_id, aws_account_uuid,
            ),
        }

        # Run all concurrently — safe_scan never raises
        tasks = {
            source: scanner.safe_scan()
            for source, scanner in scanners.items()
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=False)

        all_findings: list[dict] = []
        sources_ok: list[str] = []
        sources_fail: list[str] = []

        for source, (findings, error) in zip(tasks.keys(), results):
            if error:
                sources_fail.append(source)
                logger.warning("Scanner %s failed: %s", source, error)
            else:
                sources_ok.append(source)
                all_findings.extend(findings)

        logger.info(
            "Account %s: %d findings from %s (failed: %s)",
            account_id_str, len(all_findings), sources_ok, sources_fail,
        )
        return all_findings, sources_ok, sources_fail

    # ── Upsert logic ────────────────────────────────────────────────────────

    async def _upsert_all(self, findings: list[dict]) -> tuple[int, int]:
        """
        Fingerprint-based upsert.
        - fingerprint != '' → check for existing → insert or update last_seen_at
        - fingerprint == '' → skip (seeded demo data)
        Returns (added, updated).
        """
        added = 0
        updated = 0

        # Collect all non-empty fingerprints
        fp_map: dict[str, dict] = {
            f["fingerprint"]: f for f in findings if f.get("fingerprint")
        }
        if not fp_map:
            return 0, 0

        # Fetch existing by fingerprints in bulk
        result = await self.db.execute(
            select(CanonicalFinding.id, CanonicalFinding.fingerprint)
            .where(CanonicalFinding.fingerprint.in_(list(fp_map.keys())))
        )
        existing = {row.fingerprint: row.id for row in result}

        now_iso = datetime.now(UTC).isoformat()

        for fp, finding_dict in fp_map.items():
            if fp in existing:
                # Update last_seen_at only
                await self.db.execute(
                    update(CanonicalFinding)
                    .where(CanonicalFinding.fingerprint == fp)
                    .values(last_seen_at=now_iso, updated_at=datetime.now(UTC))
                )
                updated += 1
            else:
                # Insert new finding
                new_id = str(uuid.uuid4()).replace("-", "")
                cf = CanonicalFinding(
                    id=uuid.UUID(new_id[:8] + "-" + new_id[8:12] + "-" + new_id[12:16] + "-" + new_id[16:20] + "-" + new_id[20:]),
                    workspace_id=uuid.UUID(finding_dict["workspace_id"]) if isinstance(finding_dict["workspace_id"], str) else finding_dict["workspace_id"],
                    aws_account_id=uuid.UUID(finding_dict["aws_account_id"]) if isinstance(finding_dict["aws_account_id"], str) else finding_dict["aws_account_id"],
                    fingerprint=fp,
                    primary_source=finding_dict["primary_source"],
                    severity=finding_dict["severity"],
                    status="open",
                    title=finding_dict["title"],
                    description=finding_dict.get("description"),
                    remediation=finding_dict.get("remediation"),
                    resource_arn=finding_dict.get("resource_arn"),
                    resource_type=finding_dict.get("resource_type"),
                    region=finding_dict.get("region"),
                    compliance_frameworks=finding_dict.get("compliance_frameworks", []),
                    tags=finding_dict.get("tags", {}),
                    first_seen_at=finding_dict.get("first_seen_at", now_iso),
                    last_seen_at=finding_dict.get("last_seen_at", now_iso),
                    resolved_at=None,
                    risk_score=None,
                )
                self.db.add(cf)
                added += 1

        await self.db.flush()
        return added, updated

    # ── boto3 client factory ─────────────────────────────────────────────────

    def _make_client(self, service: str, region: str) -> Any:
        """
        Create a boto3 client.
        - If LOCALSTACK_ENDPOINT is set: use LocalStack (test credentials).
        - Otherwise: use real AWS credentials (role assumption via STS in future).
        """
        kwargs: dict = {
            "region_name": region,
            "config": BOTO_CONFIG,
        }
        if LOCALSTACK_ENDPOINT:
            kwargs["endpoint_url"] = LOCALSTACK_ENDPOINT
            kwargs["aws_access_key_id"] = "test"
            kwargs["aws_secret_access_key"] = "test"

        return boto3.client(service, **kwargs)

    # ── DB helpers ──────────────────────────────────────────────────────────

    async def _fetch_accounts(self) -> list[AwsAccount]:
        q = select(AwsAccount).where(
            AwsAccount.workspace_id == uuid.UUID(self.workspace_id)
            if isinstance(self.workspace_id, str) else AwsAccount.workspace_id == self.workspace_id
        )
        if self.aws_account_id:
            q = q.where(AwsAccount.id == uuid.UUID(self.aws_account_id)
                        if isinstance(self.aws_account_id, str) else AwsAccount.id == self.aws_account_id)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def _create_scan_job(self, triggered_by: str, started_at: datetime) -> ScanJob:
        job = ScanJob(
            workspace_id=uuid.UUID(self.workspace_id) if isinstance(self.workspace_id, str) else self.workspace_id,
            aws_account_id=uuid.UUID(self.aws_account_id) if self.aws_account_id and isinstance(self.aws_account_id, str) else (uuid.UUID(str(self.aws_account_id)) if self.aws_account_id else None),
            status="running",
            triggered_by=triggered_by,
            started_at=started_at,
            findings_added=0,
            findings_updated=0,
            findings_total=0,
            sources_scanned=[],
            sources_failed=[],
        )
        self.db.add(job)
        await self.db.flush()
        return job

    async def _finish_job(
        self,
        job: ScanJob,
        started_at: datetime,
        status: str,
        findings_added: int = 0,
        findings_updated: int = 0,
        findings_total: int = 0,
        sources_scanned: list[str] | None = None,
        sources_failed: list[str] | None = None,
        error: str | None = None,
    ) -> ScanJobResult:
        completed_at = datetime.now(UTC)
        duration = (completed_at - started_at).total_seconds()

        job.status = status
        job.completed_at = completed_at
        job.findings_added = findings_added
        job.findings_updated = findings_updated
        job.findings_total = findings_total
        job.sources_scanned = sources_scanned or []
        job.sources_failed = sources_failed or []
        job.error_message = error
        job.duration_seconds = duration

        await self.db.commit()

        return ScanJobResult(
            job_id=str(job.id),
            status=status,
            findings_added=findings_added,
            findings_updated=findings_updated,
            findings_total=findings_total,
            sources_scanned=sources_scanned or [],
            sources_failed=sources_failed or [],
            error_message=error,
            duration_seconds=duration,
        )
