"""
FindingNormalizer — maps raw AWS API responses to canonical_finding fields.

Rules:
- severity enum: "critical" | "high" | "medium" | "low" | "info"
- status for new findings: always "open"
- fingerprint = SHA256(f"{source}:{external_id}") for deduplication
- compliance_frameworks stored as Python list (JSON in SQLite via JSON column)
- resource_arn, region, resource_type extracted where available
"""

import hashlib
import json
import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

_SEVERITY_MAP: dict[str, str] = {
    # AWS standard
    "CRITICAL": "critical",
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
    "INFORMATIONAL": "info",
    "INFORMATION": "info",
    "INFO": "info",
    # GuardDuty numeric labels
    "9": "critical",
    "8": "critical",
    "7": "high",
    "6": "high",
    "5": "medium",
    "4": "medium",
    "3": "low",
    "2": "low",
    "1": "info",
    "0": "info",
}


class FindingNormalizer:
    """Maps raw AWS API responses to canonical_finding insertion dicts."""

    # ── Severity mapping ───────────────────────────────────────────────────

    def _severity_map(self, raw: str | float | None) -> str:
        """Map any AWS severity representation to our enum values."""
        if raw is None:
            return "info"
        raw_str = str(raw).upper().strip()
        # Handle float/numeric severity (GuardDuty uses 0.0–10.0)
        try:
            val = float(raw_str)
            if val >= 9.0:
                return "critical"
            elif val >= 7.0:
                return "high"
            elif val >= 4.0:
                return "medium"
            elif val >= 1.0:
                return "low"
            else:
                return "info"
        except ValueError:
            pass
        return _SEVERITY_MAP.get(raw_str, "info")

    # ── Fingerprint ─────────────────────────────────────────────────────────

    def _generate_fingerprint(self, source: str, external_id: str) -> str:
        """SHA256 hash of source+external_id for deduplication."""
        raw = f"{source}:{external_id}".encode()
        return hashlib.sha256(raw).hexdigest()

    # ── Timestamp helpers ───────────────────────────────────────────────────

    def _iso(self, dt) -> str | None:
        """Convert datetime or ISO string to ISO string, or None."""
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt.isoformat()
        return str(dt)

    def _now_iso(self) -> str:
        return datetime.now(UTC).isoformat()

    # ── Security Hub ───────────────────────────────────────────────────────

    def from_security_hub(
        self, finding: dict, workspace_id: str, aws_account_uuid: str
    ) -> dict:
        """Map an ASFF-format Security Hub finding to canonical fields."""
        external_id = finding.get("Id", "")
        fingerprint = self._generate_fingerprint("security_hub", external_id)

        # Severity — Security Hub uses Normalized (0-100) or Label
        sev_label = (
            finding.get("Severity", {}).get("Label")
            or finding.get("Severity", {}).get("Original")
        )
        sev_normalized = finding.get("Severity", {}).get("Normalized", 0)
        if sev_label:
            severity = self._severity_map(sev_label)
        else:
            # Normalize 0-100 to our scale
            if sev_normalized >= 90:
                severity = "critical"
            elif sev_normalized >= 70:
                severity = "high"
            elif sev_normalized >= 40:
                severity = "medium"
            elif sev_normalized >= 1:
                severity = "low"
            else:
                severity = "info"

        # Resources
        resources = finding.get("Resources", [{}])
        first_resource = resources[0] if resources else {}
        resource_arn = first_resource.get("Id") or finding.get("ProductArn")
        resource_type = first_resource.get("Type")
        region = finding.get("Region") or first_resource.get("Region")

        # Compliance frameworks from standards subscriptions
        compliance_info = finding.get("Compliance", {})
        related_reqs = compliance_info.get("RelatedRequirements", [])
        compliance_frameworks = _dedupe_list(related_reqs)

        # Remediation
        remediation = None
        remediation_info = finding.get("Remediation", {})
        if remediation_info:
            rec = remediation_info.get("Recommendation", {})
            remediation = rec.get("Text") or rec.get("Url")

        title = finding.get("Title", "Security Hub Finding")
        description = finding.get("Description")

        return {
            "workspace_id": workspace_id,
            "aws_account_id": aws_account_uuid,
            "fingerprint": fingerprint,
            "primary_source": "security_hub",
            "severity": severity,
            "status": "open",
            "title": title,
            "description": description,
            "remediation": remediation,
            "resource_arn": resource_arn,
            "resource_type": resource_type,
            "region": region,
            "compliance_frameworks": compliance_frameworks,
            "tags": {},
            "first_seen_at": self._iso(finding.get("FirstObservedAt")) or self._now_iso(),
            "last_seen_at": self._iso(finding.get("LastObservedAt")) or self._now_iso(),
            "resolved_at": None,
        }

    # ── GuardDuty ──────────────────────────────────────────────────────────

    def from_guard_duty(
        self, finding: dict, workspace_id: str, aws_account_uuid: str
    ) -> dict:
        """Map a GuardDuty finding to canonical fields."""
        external_id = finding.get("Id", "")
        fingerprint = self._generate_fingerprint("guard_duty", external_id)

        severity_raw = finding.get("Severity", 0)
        severity = self._severity_map(severity_raw)

        title = finding.get("Title", "GuardDuty Finding")
        description = finding.get("Description")

        # Resource info — GuardDuty finding resource varies by type
        resource = finding.get("Resource", {})
        resource_type = resource.get("ResourceType")
        region = finding.get("Region")
        resource_arn = _extract_gd_resource_arn(resource)

        # GuardDuty maps to threat detection — no standard compliance frameworks
        compliance_frameworks: list = []
        # Map known GuardDuty finding types to compliance tags
        finding_type = finding.get("Type", "")
        if "IAM" in finding_type or "Policy" in finding_type:
            compliance_frameworks = ["CIS_AWS_1.4"]
        elif "S3" in finding_type:
            compliance_frameworks = ["CIS_AWS_2.1"]

        created_at = self._iso(finding.get("CreatedAt")) or self._now_iso()
        updated_at = self._iso(finding.get("UpdatedAt")) or created_at

        return {
            "workspace_id": workspace_id,
            "aws_account_id": aws_account_uuid,
            "fingerprint": fingerprint,
            "primary_source": "guard_duty",
            "severity": severity,
            "status": "open",
            "title": title,
            "description": description,
            "remediation": None,
            "resource_arn": resource_arn,
            "resource_type": resource_type,
            "region": region,
            "compliance_frameworks": compliance_frameworks,
            "tags": {"finding_type": finding_type},
            "first_seen_at": created_at,
            "last_seen_at": updated_at,
            "resolved_at": None,
        }

    # ── Inspector v2 ───────────────────────────────────────────────────────

    def from_inspector(
        self, finding: dict, workspace_id: str, aws_account_uuid: str
    ) -> dict:
        """Map an Inspector v2 finding to canonical fields."""
        external_id = finding.get("findingArn", "")
        fingerprint = self._generate_fingerprint("inspector", external_id)

        severity_raw = finding.get("severity", "INFORMATIONAL")
        severity = self._severity_map(severity_raw)

        title = finding.get("title", "Inspector Finding")
        description = finding.get("description")

        resource_list = finding.get("resources", [{}])
        first_resource = resource_list[0] if resource_list else {}
        resource_arn = first_resource.get("id") or external_id
        resource_type = first_resource.get("type")
        region = finding.get("awsRegion") or first_resource.get("region")

        # Extract CVE/compliance data
        compliance_frameworks = []
        package_vuln = finding.get("packageVulnerabilityDetails", {})
        cve_ids = package_vuln.get("cvssScores", [])
        vuln_id = package_vuln.get("vulnerabilityId")
        if vuln_id:
            compliance_frameworks.append(f"CVE:{vuln_id}")

        remediation_info = finding.get("remediation", {})
        remediation = (
            remediation_info.get("recommendation", {}).get("text")
            if remediation_info
            else None
        )

        first_seen = self._iso(finding.get("firstObservedAt")) or self._now_iso()
        last_seen = self._iso(finding.get("lastObservedAt")) or first_seen

        return {
            "workspace_id": workspace_id,
            "aws_account_id": aws_account_uuid,
            "fingerprint": fingerprint,
            "primary_source": "inspector",
            "severity": severity,
            "status": "open",
            "title": title,
            "description": description,
            "remediation": remediation,
            "resource_arn": resource_arn,
            "resource_type": resource_type,
            "region": region,
            "compliance_frameworks": compliance_frameworks,
            "tags": {},
            "first_seen_at": first_seen,
            "last_seen_at": last_seen,
            "resolved_at": None,
        }

    # ── Config ─────────────────────────────────────────────────────────────

    def from_config(
        self, evaluation: dict, workspace_id: str, aws_account_uuid: str
    ) -> dict:
        """Map a Config rule non-compliance evaluation to canonical fields."""
        rule_name = evaluation.get("ConfigRuleName", "")
        resource_id = evaluation.get("ResourceId", "")
        resource_type = evaluation.get("ResourceType", "")
        external_id = f"{rule_name}:{resource_id}"
        fingerprint = self._generate_fingerprint("config", external_id)

        annotation = evaluation.get("Annotation", "")
        title = f"Config: {rule_name} — {resource_type} non-compliant"
        description = annotation or f"Resource {resource_id} violates rule {rule_name}"

        # Config rules map to CIS/PCI/NIST — use rule name hints
        compliance_frameworks = _config_rule_to_frameworks(rule_name)

        # Severity heuristic — Config doesn't provide severity directly
        severity = _config_severity_heuristic(rule_name)

        ordering_ts = self._iso(evaluation.get("OrderingTimestamp")) or self._now_iso()

        return {
            "workspace_id": workspace_id,
            "aws_account_id": aws_account_uuid,
            "fingerprint": fingerprint,
            "primary_source": "config",
            "severity": severity,
            "status": "open",
            "title": title,
            "description": description,
            "remediation": f"Remediate Config rule: {rule_name}",
            "resource_arn": resource_id,
            "resource_type": resource_type,
            "region": None,
            "compliance_frameworks": compliance_frameworks,
            "tags": {"config_rule": rule_name},
            "first_seen_at": ordering_ts,
            "last_seen_at": ordering_ts,
            "resolved_at": None,
        }

    # ── IAM Access Analyzer ────────────────────────────────────────────────

    def from_iam_access_analyzer(
        self, finding: dict, workspace_id: str, aws_account_uuid: str
    ) -> dict:
        """Map an IAM Access Analyzer finding to canonical fields."""
        external_id = finding.get("id", "")
        fingerprint = self._generate_fingerprint("iam_access_analyzer", external_id)

        finding_type = finding.get("findingType") or finding.get("type", "")
        resource = finding.get("resource", "")
        resource_type = finding.get("resourceType", "")

        # Severity based on finding type
        if "ExternalAccess" in finding_type:
            severity = "high"
            title = f"IAM: External access to {resource_type}"
        elif "UnusedAccess" in finding_type or "UnusedPermission" in finding_type:
            severity = "medium"
            title = f"IAM: Unused access in {resource_type}"
        elif "UnusedIAMRole" in finding_type:
            severity = "low"
            title = f"IAM: Unused IAM role"
        else:
            severity = "medium"
            title = f"IAM Access Analyzer: {finding_type or 'Policy finding'}"

        principal = finding.get("principal", {})
        description = (
            f"IAM Access Analyzer detected {finding_type} on resource: {resource}. "
            f"Principal: {json.dumps(principal) if principal else 'unknown'}"
        )

        compliance_frameworks = ["CIS_AWS_1.4", "SOC2"]

        created_at = self._iso(finding.get("createdAt")) or self._now_iso()
        updated_at = self._iso(finding.get("updatedAt")) or created_at

        return {
            "workspace_id": workspace_id,
            "aws_account_id": aws_account_uuid,
            "fingerprint": fingerprint,
            "primary_source": "iam_access_analyzer",
            "severity": severity,
            "status": "open",
            "title": title,
            "description": description,
            "remediation": "Review and revoke unnecessary access permissions.",
            "resource_arn": resource,
            "resource_type": resource_type,
            "region": finding.get("region"),
            "compliance_frameworks": compliance_frameworks,
            "tags": {"finding_type": finding_type},
            "first_seen_at": created_at,
            "last_seen_at": updated_at,
            "resolved_at": None,
        }


# ── Helpers ────────────────────────────────────────────────────────────────

def _dedupe_list(items: list) -> list:
    seen: set = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _extract_gd_resource_arn(resource: dict) -> str | None:
    """Extract a resource ARN from a GuardDuty resource dict."""
    for key in ("instanceDetails", "s3BucketDetails", "accessKeyDetails", "rdsDbInstanceDetails"):
        details = resource.get(key, {})
        if isinstance(details, list) and details:
            details = details[0]
        if isinstance(details, dict):
            arn = details.get("arn") or details.get("instanceArn")
            if arn:
                return arn
    return None


def _config_rule_to_frameworks(rule_name: str) -> list[str]:
    """Map AWS Config managed rule names to compliance framework IDs."""
    rule_upper = rule_name.upper()
    frameworks = []
    if any(k in rule_upper for k in ("IAM", "ROOT", "MFA", "PASSWORD")):
        frameworks.append("CIS_AWS_1.4")
    if any(k in rule_upper for k in ("S3", "BUCKET")):
        frameworks.append("CIS_AWS_2.1")
    if any(k in rule_upper for k in ("ENCRYPTED", "KMS", "CMK")):
        frameworks.append("PCI_DSS_3.2.1")
    if any(k in rule_upper for k in ("CLOUDTRAIL", "LOG", "FLOW")):
        frameworks.append("SOC2")
    if not frameworks:
        frameworks.append("AWS_BEST_PRACTICES")
    return frameworks


def _config_severity_heuristic(rule_name: str) -> str:
    """Heuristic severity for Config rules based on rule name patterns."""
    rule_upper = rule_name.upper()
    if any(k in rule_upper for k in ("ROOT", "MFA", "PUBLIC", "OPEN", "UNRESTRICTED")):
        return "high"
    if any(k in rule_upper for k in ("ENCRYPTED", "KMS", "SSL", "TLS")):
        return "medium"
    if any(k in rule_upper for k in ("CLOUDTRAIL", "LOG", "BACKUP")):
        return "medium"
    return "low"
