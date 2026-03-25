"""
Normalization Service — links source_findings → canonical_findings.

OpenViking hierarchy:
  L2 source_findings  → raw, append-only, preserves full ASFF payload
  L1 canonical_findings → deduplicated, normalized, scored

Fingerprint algorithm (deterministic dedup):
  SHA256(workspace_id + aws_account_id + resource_arn_or_title + source_type)[:16]

Rules:
- risk_score is computed here (backend only, never frontend, never AI).
- Severity on canonical_finding comes from source_finding — never overridden.
- compliance_frameworks is mapped from ASFF finding Types[] array.
"""

import hashlib
import uuid
from datetime import UTC, datetime

import structlog

from app.models.canonical_finding import CanonicalFinding
from app.models.enums import FindingSeverity, FindingSource, FindingStatus
from app.models.source_finding import SourceFinding
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.repositories.source_finding_repository import SourceFindingRepository

logger = structlog.get_logger(__name__)

# ── Risk scoring table (deterministic, rule-based) ───────────────────────────
# Keys: (FindingSeverity, is_public_resource: bool)
# is_public_resource = True when resource_arn contains "Public" or resource_type
# is an internet-facing resource type
_RISK_SCORE_TABLE: dict[tuple, float] = {
    (FindingSeverity.CRITICAL, True): 9.8,
    (FindingSeverity.CRITICAL, False): 8.5,
    (FindingSeverity.HIGH, True): 7.5,
    (FindingSeverity.HIGH, False): 6.5,
    (FindingSeverity.MEDIUM, True): 5.0,
    (FindingSeverity.MEDIUM, False): 4.0,
    (FindingSeverity.LOW, True): 2.5,
    (FindingSeverity.LOW, False): 1.5,
    (FindingSeverity.INFO, True): 0.5,
    (FindingSeverity.INFO, False): 0.2,
}

# AWS resource types considered internet-facing for risk scoring
_INTERNET_FACING_RESOURCE_TYPES = {
    "AwsEc2Instance",
    "AwsElbv2LoadBalancer",
    "AwsElbLoadBalancer",
    "AwsS3Bucket",
    "AwsApiGatewayRestApi",
    "AwsApiGatewayV2Api",
    "AwsCloudFrontDistribution",
    "AwsRdsDbInstance",
}

# ASFF Types → compliance framework mapping (subset for Phase 3)
_ASFF_TYPE_TO_FRAMEWORK: dict[str, str] = {
    "Software and Configuration Checks/Industry and Regulatory Standards/CIS AWS Foundations Benchmark": "CIS_AWS_1.4",
    "Software and Configuration Checks/Industry and Regulatory Standards/PCI DSS": "PCI_DSS_3.2.1",
    "Software and Configuration Checks/Industry and Regulatory Standards/NIST SP 800-53": "NIST_CSF",
    "Software and Configuration Checks/Industry and Regulatory Standards/SOC 2": "SOC2",
}


def _compute_fingerprint(
    workspace_id: uuid.UUID,
    aws_account_id: uuid.UUID,
    resource_arn: str | None,
    title: str,
    source: FindingSource,
) -> str:
    """
    Deterministic 16-char hex fingerprint for deduplication.
    Same resource + same finding type in same account always produces the same fingerprint.
    """
    key = f"{workspace_id}:{aws_account_id}:{resource_arn or title}:{source}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _compute_risk_score(
    severity: FindingSeverity,
    resource_type: str | None,
    first_seen_at: str | None = None,
) -> float:
    """
    Risk score v1: base_score × age_weight.

    base_score from _RISK_SCORE_TABLE (severity × is_internet_facing).
    age_weight penalises stale findings — old unresolved = lower urgency.
      first_seen < 7 days:   1.0  (fresh, full score)
      first_seen 7-30 days:  0.9
      first_seen 30-90 days: 0.8
      first_seen > 90 days:  0.7  (long-standing risk, lower urgency)
    """
    is_internet_facing = resource_type in _INTERNET_FACING_RESOURCE_TYPES
    base = _RISK_SCORE_TABLE.get((severity, is_internet_facing), 1.0)

    age_weight = 1.0
    if first_seen_at:
        try:
            # Handle both ISO strings and plain date strings
            ts = datetime.fromisoformat(first_seen_at.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            age_days = (datetime.now(UTC) - ts).days
            if age_days >= 90:
                age_weight = 0.7
            elif age_days >= 30:
                age_weight = 0.8
            elif age_days >= 7:
                age_weight = 0.9
        except (ValueError, TypeError):
            pass  # malformed date → full weight

    return round(base * age_weight, 2)


def _map_compliance_frameworks(raw_payload: dict) -> list[str]:
    """Extract compliance framework IDs from ASFF Types[] array."""
    types = raw_payload.get("Types", [])
    frameworks = []
    for asff_type in types:
        for prefix, framework_id in _ASFF_TYPE_TO_FRAMEWORK.items():
            if asff_type.startswith(prefix) and framework_id not in frameworks:
                frameworks.append(framework_id)
    return frameworks


class NormalizationService:
    """
    Processes source_findings into canonical_findings.

    Called after each SecurityHubSyncJob completes.
    Processes findings in batches; safe to re-run (idempotent by fingerprint).
    """

    def __init__(
        self,
        source_repo: SourceFindingRepository,
        canonical_repo: CanonicalFindingRepository,
    ) -> None:
        self._source = source_repo
        self._canonical = canonical_repo

    async def normalize_account(
        self,
        aws_account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        batch_size: int = 100,
    ) -> dict:
        """
        Normalize all un-linked source findings for an account.
        Returns stats: {created: N, updated: N, total_processed: N}.
        """
        stats = {"created": 0, "updated": 0, "total_processed": 0}
        now_iso = datetime.now(UTC).isoformat()

        findings = await self._source.list_unnormalized(aws_account_id, limit=batch_size)
        logger.info(
            "normalization.start",
            aws_account_id=str(aws_account_id),
            count=len(findings),
        )

        for sf in findings:
            try:
                fingerprint = _compute_fingerprint(
                    workspace_id=workspace_id,
                    aws_account_id=aws_account_id,
                    resource_arn=sf.resource_arn,
                    title=sf.title,
                    source=sf.source,
                )

                existing = await self._canonical.get_by_fingerprint(fingerprint, workspace_id)

                if existing is None:
                    canonical = CanonicalFinding(
                        workspace_id=workspace_id,
                        aws_account_id=aws_account_id,
                        fingerprint=fingerprint,
                        primary_source=sf.source,
                        severity=sf.severity,
                        status=FindingStatus.OPEN,
                        risk_score=_compute_risk_score(sf.severity, sf.resource_type, sf.first_observed_at or now_iso),
                        title=sf.title,
                        description=sf.description,
                        resource_arn=sf.resource_arn,
                        resource_type=sf.resource_type,
                        region=sf.region,
                        compliance_frameworks=_map_compliance_frameworks(sf.raw_payload),
                        tags={},
                        first_seen_at=sf.first_observed_at or now_iso,
                        last_seen_at=sf.last_observed_at or now_iso,
                    )
                    self._canonical.db.add(canonical)
                    await self._canonical.db.flush()
                    await self._canonical.db.refresh(canonical)
                    stats["created"] += 1
                else:
                    # Update last_seen and risk_score (severity may have changed)
                    existing.last_seen_at = sf.last_observed_at or now_iso
                    existing.risk_score = _compute_risk_score(sf.severity, sf.resource_type, existing.first_seen_at)
                    self._canonical.db.add(existing)
                    await self._canonical.db.flush()
                    canonical = existing
                    stats["updated"] += 1

                # Link source_finding to canonical
                sf.canonical_finding_id = canonical.id
                self._source.db.add(sf)
                await self._source.db.flush()
                stats["total_processed"] += 1

            except Exception as exc:
                logger.error(
                    "normalization.finding_error",
                    native_id=sf.native_finding_id,
                    error=str(exc),
                )
                continue

        logger.info("normalization.complete", **stats)
        return stats
