"""
RAGPriorityService — Red / Amber / Green priority scoring and action generation.

Market-standard implementation aligned with Wiz-parity:

RAG Level Logic (multi-condition, not a single threshold):
- RED:   composite > 0.55  OR  critical + any public exposure  OR  critical + toxic combo
         OR  critical + data store  OR  blast_nodes > 2  OR  high/critical open > 5 days
- AMBER: composite > 0.40  OR  high + blast_nodes >= 1  OR  iam_score > 0.6
         OR  medium open > 30 days
- GREEN: everything else

Remediation actions cover:
- S3, IAM, Security Groups, EC2, RDS (original)
- Lambda, KMS, SecretsManager, CloudTrail (new)
- Infrastructure-as-Code (Terraform/CDK) for critical/high (new)
- SCP / Organizations Guardrail prevention actions (new)

SLA is severity-adjusted:
- RED + critical → 1 day
- RED + high     → 3 days
- AMBER + critical → 7 days
- AMBER + high     → 14 days
- GREEN → 30-90 days based on severity

Stakeholders are context-aware:
- RED + IAM     → CISO, IAM Team, Security Team
- RED + network → Security Team, Network Team, DevOps
- RED + data    → CISO, Data Protection Officer, Security Team
- AMBER         → Security Team, DevOps
- GREEN         → Security Team

Design principles:
- Synchronous (no DB / network calls) — safe to call multiple times.
- Fully deterministic given the same inputs.
- All method signatures remain compatible with the rest of the codebase.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.models.canonical_finding import CanonicalFinding
from app.services.causal_engine import CausalAnalysis, CausalFactor

logger = logging.getLogger(__name__)


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class PrioritizedAction:
    """A single remediation action with effort/impact ratings and optional CLI command."""

    title: str
    description: str
    effort: str         # "LOW" | "MEDIUM" | "HIGH"
    impact: str         # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    cli_command: str | None
    console_url: str | None
    rag_color: str      # "RED" | "AMBER" | "GREEN"

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "effort": self.effort,
            "impact": self.impact,
            "cli_command": self.cli_command,
            "console_url": self.console_url,
            "rag_color": self.rag_color,
        }


@dataclass
class RAGScore:
    """Complete RAG priority score with remediation actions and governance metadata."""

    level: str                              # "RED" | "AMBER" | "GREEN"
    composite_score: float
    primary_reason: str
    immediate_actions: list[PrioritizedAction]
    sprint_actions: list[PrioritizedAction]
    quarterly_actions: list[PrioritizedAction]
    sla_days: int
    escalation_required: bool
    stakeholders: list[str]


# ── Service ───────────────────────────────────────────────────────────────────

class RAGPriorityService:
    """
    Computes RAG priority level and generates prioritised remediation actions.

    Synchronous — no I/O dependencies. Safe to call in tight loops.

    Public API:
        rag = RAGPriorityService()
        score = rag.compute(finding, causal)
    """

    def compute(
        self,
        finding: CanonicalFinding,
        causal: CausalAnalysis,
    ) -> RAGScore:
        """
        Compute RAG priority score and generate remediation actions.

        Args:
            finding: The canonical finding being scored.
            causal: CausalAnalysis output from CausalEngine.analyze().

        Returns:
            RAGScore with level, actions, SLA, stakeholders, and escalation flag.
        """
        level, reason = self._determine_rag_level(
            causal.composite_score, finding, causal
        )
        immediate = self._generate_immediate_actions(finding, causal)
        sprint = self._generate_sprint_actions(finding, causal)
        quarterly = self._generate_quarterly_actions(finding, causal)
        sla = self._compute_sla(level, finding)
        escalation = level == "RED"
        stakeholders = self._get_stakeholders(level, finding, causal)

        return RAGScore(
            level=level,
            composite_score=round(causal.composite_score, 4),
            primary_reason=reason,
            immediate_actions=immediate,
            sprint_actions=sprint,
            quarterly_actions=quarterly,
            sla_days=sla,
            escalation_required=escalation,
            stakeholders=stakeholders,
        )

    # ── RAG level determination ───────────────────────────────────────────────

    def _determine_rag_level(
        self,
        composite: float,
        finding: CanonicalFinding,
        causal: CausalAnalysis,
    ) -> tuple[str, str]:
        """
        Multi-condition RAG determination with corrected thresholds.

        RED conditions (any one is sufficient):
        1. composite > 0.55 (lowered from 0.65 — 0.65 was never triggered in practice)
        2. critical severity + net_score > 0.2 (critical+public is always RED)
        3. critical severity + any toxic combo detected
        4. critical severity + data_score > 0.3 (critical + data store = RED)
        5. blast_nodes > 2 (lowered from 3)
        6. high/critical open > 5 days (lowered from 7)

        AMBER conditions:
        1. composite > 0.40 (raised from 0.35 to reduce noise)
        2. high severity + blast_nodes >= 1
        3. iam_score > 0.6
        4. medium open > 30 days

        Returns (level, primary_reason).
        """
        severity = str(finding.severity or "").lower()
        factor_map = {f.name: f for f in causal.factors}
        net_score = factor_map.get("network_exposure", CausalFactor("", 0, [], [], 0)).score
        iam_score = factor_map.get("iam_risk", CausalFactor("", 0, [], [], 0)).score
        data_score = factor_map.get("data_sensitivity", CausalFactor("", 0, [], [], 0)).score
        blast_nodes = len(
            factor_map.get("blast_radius", CausalFactor("", 0, [], [], 0)).contributing_nodes
        )
        has_toxic = len(causal.toxic_combinations) > 0

        days_open = self._days_open(finding)

        # ── RED conditions ────────────────────────────────────────────────────

        if composite > 0.55:
            return "RED", (
                f"Composite risk score {composite:.2f} exceeds RED threshold (0.55)"
            )

        # Critical + any public exposure — must be RED regardless of composite
        # Fixes: S3 critical finding with "publicly accessible" was getting GREEN
        if severity == "critical" and net_score > 0.2:
            return "RED", (
                f"Critical severity finding with network exposure score {net_score:.2f} "
                "— critical findings with any public signal are always RED"
            )

        if severity == "critical" and has_toxic:
            combo_names = ", ".join(c.name for c in causal.toxic_combinations[:2])
            return "RED", (
                f"Critical severity finding with toxic combination(s): {combo_names}"
            )

        # Critical + data store is always RED — data breach risk is immediate
        if severity == "critical" and data_score > 0.3:
            return "RED", (
                f"Critical severity finding on a sensitive data resource "
                f"(data_score={data_score:.2f}) — data breach risk is immediate"
            )

        if blast_nodes > 2:
            return "RED", (
                f"Blast radius spans {blast_nodes} sensitive downstream nodes — "
                "immediate containment required"
            )

        if has_toxic and data_score > 0.6:
            combo_names = ", ".join(c.name for c in causal.toxic_combinations[:2])
            return "RED", (
                f"Toxic combinations detected ({combo_names}) on sensitive data resource"
            )

        # Lowered from 7 days to 5 days for critical/high
        if days_open > 5 and severity in ("critical", "high"):
            return "RED", (
                f"High/critical finding unresolved for {days_open} days — "
                "exceeds acceptable SLA (threshold: 5 days)"
            )

        # ── AMBER conditions ──────────────────────────────────────────────────

        if composite > 0.40:
            return "AMBER", (
                f"Composite risk score {composite:.2f} is in AMBER range (0.40–0.55)"
            )

        if severity == "high" and blast_nodes >= 1:
            return "AMBER", (
                "High severity with at least one downstream sensitive resource at risk"
            )

        if iam_score > 0.6:
            return "AMBER", (
                f"IAM risk score {iam_score:.2f} indicates potential lateral movement path"
            )

        if days_open > 30 and severity == "medium":
            return "AMBER", (
                f"Medium severity finding open for {days_open} days — "
                "approaching drift threshold"
            )

        # ── GREEN ─────────────────────────────────────────────────────────────
        return "GREEN", (
            "Low composite risk score with no active attack path — "
            "schedule for quarterly remediation"
        )

    # ── Action generators ─────────────────────────────────────────────────────

    def _generate_immediate_actions(
        self,
        finding: CanonicalFinding,
        causal: CausalAnalysis,
    ) -> list[PrioritizedAction]:
        """
        Generate immediate (break-glass, same-day) remediation actions.

        Covers: S3, IAM, Security Groups, EC2, RDS, Lambda, KMS, SecretsManager, CloudTrail.
        Falls back to a generic review action if no specific match.
        """
        resource_type = (finding.resource_type or "").lower()
        cause = causal.primary_root_cause
        actions: list[PrioritizedAction] = []

        # Extract resource identifiers from ARN
        bucket_name = self._extract_s3_bucket(finding.resource_arn)
        instance_id = self._extract_ec2_instance(finding.resource_arn)
        user_name = self._extract_iam_user(finding.resource_arn)
        role_name = self._extract_iam_role(finding.resource_arn)
        db_id = self._extract_rds_identifier(finding.resource_arn)
        fn_name = self._extract_lambda_function(finding.resource_arn)
        key_id = self._extract_kms_key_id(finding.resource_arn)
        secret_arn = self._extract_secretsmanager_arn(finding.resource_arn)
        trail_name = self._extract_cloudtrail_name(finding.resource_arn)
        region = finding.region or "us-east-1"

        # ── S3 ────────────────────────────────────────────────────────────────
        if "s3" in resource_type and cause in (
            "network_misconfiguration", "governance_gap", "missing_guardrail"
        ):
            bn = bucket_name or "{bucket-name}"
            actions.append(PrioritizedAction(
                title="Block all public access on S3 bucket",
                description=(
                    f"Immediately block all public access on bucket '{bn}' "
                    "to prevent unauthorised data exposure."
                ),
                effort="LOW",
                impact="CRITICAL",
                cli_command=(
                    f"aws s3api put-public-access-block --bucket {bn} "
                    "--public-access-block-configuration "
                    "BlockPublicAcls=true,IgnorePublicAcls=true,"
                    "BlockPublicPolicy=true,RestrictPublicBuckets=true"
                ),
                console_url=(
                    f"https://s3.console.aws.amazon.com/s3/buckets/{bn}?tab=permissions"
                ),
                rag_color="RED",
            ))
            actions.append(PrioritizedAction(
                title="Audit and remove public bucket policies",
                description=(
                    "Remove any bucket policies that grant public (Principal: *) "
                    "read/write access."
                ),
                effort="LOW",
                impact="CRITICAL",
                cli_command=f"aws s3api get-bucket-policy --bucket {bn}",
                console_url=None,
                rag_color="RED",
            ))

        # ── IAM ───────────────────────────────────────────────────────────────
        if "iam" in resource_type and cause in ("iam_misconfiguration", "missing_guardrail"):
            if user_name:
                actions.append(PrioritizedAction(
                    title="Enforce MFA for IAM user",
                    description=(
                        f"Immediately enforce MFA for user '{user_name}'. "
                        "Deactivate console access until MFA is configured."
                    ),
                    effort="LOW",
                    impact="CRITICAL",
                    cli_command=(
                        f"aws iam create-virtual-mfa-device "
                        f"--virtual-mfa-device-name {user_name}-mfa "
                        f"--outfile /tmp/{user_name}-mfa.png --bootstrap-method QRCodePNG && "
                        f"aws iam enable-mfa-device --user-name {user_name} "
                        "--authentication-code1 <CODE1> --authentication-code2 <CODE2> "
                        "--serial-number arn:aws:iam::ACCOUNT:mfa/{user_name}-mfa"
                    ),
                    console_url=(
                        f"https://console.aws.amazon.com/iam/home#/users/{user_name}"
                    ),
                    rag_color="RED",
                ))
            actions.append(PrioritizedAction(
                title="Remove wildcard IAM permissions immediately",
                description=(
                    "Identify and remove any Action: '*' or Resource: '*' from policies. "
                    "Replace with least-privilege policy scoped to required actions only."
                ),
                effort="MEDIUM",
                impact="CRITICAL",
                cli_command=(
                    "aws iam list-policies --scope Local --query "
                    "\"Policies[?contains(PolicyName, '')].[PolicyName,Arn]\" --output table"
                ),
                console_url="https://console.aws.amazon.com/iam/home#/policies",
                rag_color="RED",
            ))

        # ── Security Group / Network ──────────────────────────────────────────
        if any(kw in resource_type for kw in ["securitygroup", "security_group"]) and cause in (
            "network_misconfiguration",
        ):
            sg_id = self._extract_sg_id(finding.resource_arn) or "{sg-id}"
            actions.append(PrioritizedAction(
                title="Remove unrestricted inbound rules (0.0.0.0/0)",
                description=(
                    f"Remove all inbound rules that allow 0.0.0.0/0 or ::/0 from "
                    f"security group '{sg_id}'. Replace with specific CIDR ranges."
                ),
                effort="LOW",
                impact="CRITICAL",
                cli_command=(
                    f"aws ec2 describe-security-groups --group-ids {sg_id} "
                    "--query \"SecurityGroups[0].IpPermissions\" && "
                    f"aws ec2 revoke-security-group-ingress --group-id {sg_id} "
                    "--protocol tcp --port 0-65535 --cidr 0.0.0.0/0"
                ),
                console_url=(
                    f"https://{region}.console.aws.amazon.com/ec2/v2/home?region={region}"
                    f"#SecurityGroups:groupId={sg_id}"
                ),
                rag_color="RED",
            ))

        # ── RDS ───────────────────────────────────────────────────────────────
        if "rds" in resource_type and cause in (
            "network_misconfiguration", "governance_gap", "encryption_gap"
        ):
            di = db_id or "{db-identifier}"
            actions.append(PrioritizedAction(
                title="Disable public accessibility on RDS instance",
                description=(
                    f"Set PubliclyAccessible=false on RDS instance '{di}' "
                    "to remove it from internet routing."
                ),
                effort="LOW",
                impact="CRITICAL",
                cli_command=(
                    f"aws rds modify-db-instance --db-instance-identifier {di} "
                    "--no-publicly-accessible --apply-immediately"
                ),
                console_url=(
                    f"https://{region}.console.aws.amazon.com/rds/home?region={region}"
                    f"#database:id={di}"
                ),
                rag_color="RED",
            ))

        # ── EC2 ───────────────────────────────────────────────────────────────
        if "ec2" in resource_type and cause == "network_misconfiguration" and instance_id:
            actions.append(PrioritizedAction(
                title="Disassociate public IP from EC2 instance",
                description=(
                    f"Remove the public IP address from instance '{instance_id}' "
                    "or move it behind a load balancer / NAT gateway."
                ),
                effort="MEDIUM",
                impact="HIGH",
                cli_command=(
                    f"aws ec2 describe-instances --instance-ids {instance_id} "
                    "--query \"Reservations[0].Instances[0].PublicIpAddress\""
                ),
                console_url=(
                    f"https://{region}.console.aws.amazon.com/ec2/v2/home?region={region}"
                    f"#Instances:instanceId={instance_id}"
                ),
                rag_color="RED",
            ))

        # ── Lambda ────────────────────────────────────────────────────────────
        if "lambda" in resource_type:
            fn = fn_name or "{function-name}"
            actions.append(PrioritizedAction(
                title="Remove public resource-based policy from Lambda function",
                description=(
                    f"Remove the AllowPublicAccess statement from Lambda function '{fn}'. "
                    "Public Lambda invocation policies expose the function to any AWS principal."
                ),
                effort="LOW",
                impact="CRITICAL",
                cli_command=(
                    f"aws lambda remove-permission --function-name {fn} "
                    "--statement-id AllowPublicAccess"
                ),
                console_url=(
                    f"https://{region}.console.aws.amazon.com/lambda/home?region={region}"
                    f"#/functions/{fn}"
                ),
                rag_color="RED",
            ))

        # ── KMS ───────────────────────────────────────────────────────────────
        if "kms" in resource_type:
            kid = key_id or "{key-id}"
            actions.append(PrioritizedAction(
                title="Enable automatic key rotation for KMS key",
                description=(
                    f"Enable automatic annual rotation for KMS key '{kid}'. "
                    "Keys without rotation create long-term exposure if a key is compromised."
                ),
                effort="LOW",
                impact="HIGH",
                cli_command=(
                    f"aws kms enable-key-rotation --key-id {kid}"
                ),
                console_url=(
                    f"https://{region}.console.aws.amazon.com/kms/home?region={region}"
                    f"#/kms/keys/{kid}"
                ),
                rag_color="RED",
            ))

        # ── SecretsManager ────────────────────────────────────────────────────
        if "secretsmanager" in resource_type or "secrets_manager" in resource_type:
            sarn = secret_arn or "{secret-arn}"
            actions.append(PrioritizedAction(
                title="Rotate secret immediately in AWS Secrets Manager",
                description=(
                    f"Trigger immediate rotation for secret '{sarn}'. "
                    "Unrotated secrets create persistent exposure if credentials are leaked."
                ),
                effort="LOW",
                impact="CRITICAL",
                cli_command=(
                    f"aws secretsmanager rotate-secret --secret-id {sarn}"
                ),
                console_url=(
                    f"https://{region}.console.aws.amazon.com/secretsmanager/home"
                    f"?region={region}#!/secret?name={sarn}"
                ),
                rag_color="RED",
            ))

        # ── CloudTrail ────────────────────────────────────────────────────────
        if "cloudtrail" in resource_type:
            trail = trail_name or "{trail-name}"
            actions.append(PrioritizedAction(
                title="Re-enable CloudTrail logging immediately",
                description=(
                    f"Start logging on CloudTrail trail '{trail}'. "
                    "Disabled CloudTrail means no audit trail — attacks go undetected."
                ),
                effort="LOW",
                impact="CRITICAL",
                cli_command=(
                    f"aws cloudtrail start-logging --name {trail}"
                ),
                console_url=(
                    f"https://{region}.console.aws.amazon.com/cloudtrail/home"
                    f"?region={region}#/trails/{trail}"
                ),
                rag_color="RED",
            ))

        # Generic fallback if no specific actions generated
        if not actions:
            actions.append(PrioritizedAction(
                title="Immediate review of affected resource",
                description=(
                    f"Review the configuration of the affected resource "
                    f"({finding.resource_arn or finding.resource_type}) "
                    "and restrict access to the minimum required."
                ),
                effort="LOW",
                impact="HIGH",
                cli_command=None,
                console_url="https://console.aws.amazon.com/",
                rag_color="RED",
            ))

        return actions

    def _generate_sprint_actions(
        self,
        finding: CanonicalFinding,
        causal: CausalAnalysis,
    ) -> list[PrioritizedAction]:
        """
        Generate sprint-cycle (1–2 week) remediation actions.

        Covers: S3, IAM, Network/SG hardening, Config drift, Lambda, KMS, CloudTrail.
        Always includes a CI/CD compliance check integration action.
        """
        resource_type = (finding.resource_type or "").lower()
        cause = causal.primary_root_cause
        actions: list[PrioritizedAction] = []

        bucket_name = self._extract_s3_bucket(finding.resource_arn) or "{bucket-name}"
        fn_name = self._extract_lambda_function(finding.resource_arn) or "{function-name}"
        key_id = self._extract_kms_key_id(finding.resource_arn) or "{key-id}"
        secret_arn = self._extract_secretsmanager_arn(finding.resource_arn) or "{secret-arn}"
        trail_name = self._extract_cloudtrail_name(finding.resource_arn) or "{trail-name}"
        region = finding.region or "us-east-1"

        # ── S3 ────────────────────────────────────────────────────────────────
        if "s3" in resource_type:
            actions.append(PrioritizedAction(
                title="Enable default server-side encryption on S3 bucket",
                description=(
                    f"Enable AES-256 or SSE-KMS encryption on bucket '{bucket_name}' "
                    "to protect data at rest."
                ),
                effort="LOW",
                impact="HIGH",
                cli_command=(
                    f"aws s3api put-bucket-encryption --bucket {bucket_name} "
                    "--server-side-encryption-configuration "
                    "'{\"Rules\":[{\"ApplyServerSideEncryptionByDefault\":"
                    "{\"SSEAlgorithm\":\"AES256\"}}]}'"
                ),
                console_url=(
                    f"https://s3.console.aws.amazon.com/s3/buckets/{bucket_name}?tab=properties"
                ),
                rag_color="AMBER",
            ))
            actions.append(PrioritizedAction(
                title="Enable S3 versioning and MFA delete",
                description=(
                    "Enable versioning to protect against accidental deletion and ransomware."
                ),
                effort="LOW",
                impact="MEDIUM",
                cli_command=(
                    f"aws s3api put-bucket-versioning --bucket {bucket_name} "
                    "--versioning-configuration Status=Enabled"
                ),
                console_url=None,
                rag_color="AMBER",
            ))

        # ── IAM ───────────────────────────────────────────────────────────────
        if "iam" in resource_type or cause == "iam_misconfiguration":
            actions.append(PrioritizedAction(
                title="Apply IAM permission boundaries",
                description=(
                    "Add permission boundaries to all IAM roles to restrict the maximum "
                    "permissions that can be granted, limiting blast radius."
                ),
                effort="MEDIUM",
                impact="HIGH",
                cli_command=(
                    "aws iam create-policy --policy-name PermissionBoundary "
                    "--policy-document file://permission_boundary.json"
                ),
                console_url="https://console.aws.amazon.com/iam/home#/policies",
                rag_color="AMBER",
            ))
            actions.append(PrioritizedAction(
                title="Enable IAM Access Analyzer",
                description=(
                    "Enable IAM Access Analyzer to continuously monitor for "
                    "resources shared with external principals."
                ),
                effort="LOW",
                impact="HIGH",
                cli_command=(
                    f"aws accessanalyzer create-analyzer --analyzer-name SecurityAnalyzer "
                    f"--type ACCOUNT --region {region}"
                ),
                console_url=(
                    f"https://{region}.console.aws.amazon.com/access-analyzer/home"
                    f"?region={region}"
                ),
                rag_color="AMBER",
            ))

        # ── Network / Security Group ──────────────────────────────────────────
        if cause == "network_misconfiguration":
            actions.append(PrioritizedAction(
                title="Review and tighten all security group rules",
                description=(
                    "Audit all security groups in the affected VPC and replace "
                    "any 0.0.0.0/0 rules with specific CIDR ranges or security group references."
                ),
                effort="MEDIUM",
                impact="HIGH",
                cli_command=(
                    "aws ec2 describe-security-groups "
                    "--filters Name=ip-permission.cidr,Values=0.0.0.0/0 "
                    "--query \"SecurityGroups[*].[GroupId,GroupName]\" --output table"
                ),
                console_url=None,
                rag_color="AMBER",
            ))

        # ── Config drift ──────────────────────────────────────────────────────
        if cause == "config_drift":
            actions.append(PrioritizedAction(
                title="Update IaC templates to encode secure configuration",
                description=(
                    "Update Terraform/CloudFormation templates to define the secure "
                    "configuration and prevent drift recurrence via automated deployment."
                ),
                effort="MEDIUM",
                impact="HIGH",
                cli_command=None,
                console_url=None,
                rag_color="AMBER",
            ))

        # ── Lambda ────────────────────────────────────────────────────────────
        if "lambda" in resource_type:
            actions.append(PrioritizedAction(
                title="Configure Lambda retry and error handling",
                description=(
                    f"Limit retry attempts on Lambda function '{fn_name}' to reduce "
                    "error amplification and ensure failures are surfaced quickly."
                ),
                effort="LOW",
                impact="MEDIUM",
                cli_command=(
                    f"aws lambda put-function-event-invoke-config "
                    f"--function-name {fn_name} --maximum-retry-attempts 1"
                ),
                console_url=(
                    f"https://{region}.console.aws.amazon.com/lambda/home?region={region}"
                    f"#/functions/{fn_name}/configuration"
                ),
                rag_color="AMBER",
            ))

        # ── KMS ───────────────────────────────────────────────────────────────
        if "kms" in resource_type:
            actions.append(PrioritizedAction(
                title="Audit KMS key policy for overly permissive principals",
                description=(
                    f"Review the key policy for KMS key '{key_id}' and remove any "
                    "Principal: '*' statements or cross-account access that is not required."
                ),
                effort="LOW",
                impact="HIGH",
                cli_command=(
                    f"aws kms get-key-policy --key-id {key_id} --policy-name default"
                ),
                console_url=None,
                rag_color="AMBER",
            ))

        # ── SecretsManager ────────────────────────────────────────────────────
        if "secretsmanager" in resource_type or "secrets_manager" in resource_type:
            actions.append(PrioritizedAction(
                title="Configure automatic rotation for Secrets Manager secret",
                description=(
                    f"Enable automatic rotation for secret '{secret_arn}' using a "
                    "Lambda rotation function to eliminate long-lived credentials."
                ),
                effort="MEDIUM",
                impact="HIGH",
                cli_command=(
                    f"aws secretsmanager rotate-secret --secret-id {secret_arn}"
                ),
                console_url=None,
                rag_color="AMBER",
            ))

        # ── CloudTrail ────────────────────────────────────────────────────────
        if "cloudtrail" in resource_type:
            actions.append(PrioritizedAction(
                title="Enable CloudTrail log file validation",
                description=(
                    f"Enable log file validation on trail '{trail_name}' to detect "
                    "tampering with audit logs using SHA-256 digest files."
                ),
                effort="LOW",
                impact="HIGH",
                cli_command=(
                    f"aws cloudtrail update-trail --name {trail_name} "
                    "--enable-log-file-validation"
                ),
                console_url=None,
                rag_color="AMBER",
            ))

        # Generic CI/CD integration action (always included)
        actions.append(PrioritizedAction(
            title="Add automated compliance check to CI/CD pipeline",
            description=(
                "Integrate AWS Config Rules or a checkov/tfsec scan step into your "
                "CI/CD pipeline to catch this class of misconfiguration before deployment."
            ),
            effort="MEDIUM",
            impact="HIGH",
            cli_command="aws configservice put-config-rule --config-rule file://config_rule.json",
            console_url="https://console.aws.amazon.com/config/",
            rag_color="AMBER",
        ))

        return actions

    def _generate_quarterly_actions(
        self,
        finding: CanonicalFinding,
        causal: CausalAnalysis,
    ) -> list[PrioritizedAction]:
        """
        Generate quarterly (governance / architecture-level) remediation actions.

        Always includes:
        - AWS Security Hub + CIS Benchmark
        - AWS Config continuous compliance
        - IAM quarterly access reviews

        For critical/high findings:
        - Infrastructure-as-Code (Terraform) remediation hint
        - SCP / Organizations Guardrail prevention

        For S3 findings:
        - S3 access logging
        """
        resource_type = (finding.resource_type or "").lower()
        severity = str(finding.severity or "").lower()
        bucket_name = self._extract_s3_bucket(finding.resource_arn) or "{bucket-name}"
        region = finding.region or "us-east-1"

        actions: list[PrioritizedAction] = [
            PrioritizedAction(
                title="Enable AWS Security Hub with CIS Benchmark standard",
                description=(
                    "Activate AWS Security Hub and enable the CIS AWS Foundations Benchmark "
                    "standard for continuous, automated compliance monitoring."
                ),
                effort="LOW",
                impact="HIGH",
                cli_command=(
                    f"aws securityhub enable-security-hub --region {region} "
                    "--enable-default-standards"
                ),
                console_url=(
                    f"https://{region}.console.aws.amazon.com/securityhub/home"
                    f"?region={region}"
                ),
                rag_color="GREEN",
            ),
            PrioritizedAction(
                title="Implement AWS Config continuous compliance",
                description=(
                    "Deploy AWS Config with managed rules that continuously evaluate "
                    "your resources against security best practices."
                ),
                effort="MEDIUM",
                impact="HIGH",
                cli_command=(
                    "aws configservice put-configuration-recorder "
                    "--configuration-recorder name=default,roleARN=<config-role-arn>"
                ),
                console_url="https://console.aws.amazon.com/config/",
                rag_color="GREEN",
            ),
        ]

        if "s3" in resource_type:
            actions.append(PrioritizedAction(
                title="Enable S3 access logging",
                description=(
                    f"Enable server access logging on bucket '{bucket_name}' "
                    "to maintain an audit trail of all object-level requests."
                ),
                effort="LOW",
                impact="MEDIUM",
                cli_command=(
                    f"aws s3api put-bucket-logging --bucket {bucket_name} "
                    "--bucket-logging-status "
                    "{\"LoggingEnabled\":{\"TargetBucket\":\""
                    + bucket_name
                    + "-logs\",\"TargetPrefix\":\"access-logs/\"}}"
                ),
                console_url=(
                    f"https://s3.console.aws.amazon.com/s3/buckets/{bucket_name}?tab=properties"
                ),
                rag_color="GREEN",
            ))

        # IaC remediation hint for critical/high findings
        if severity in ("critical", "high"):
            actions.append(PrioritizedAction(
                title="Encode secure configuration in Terraform / CDK",
                description=(
                    "Add the secure configuration for this resource type to your "
                    "Terraform modules or CDK constructs so future deployments are "
                    "secure by default. Use checkov or tfsec to enforce the policy in CI. "
                    "Example: aws_s3_bucket_public_access_block, "
                    "aws_iam_policy with explicit deny, aws_security_group with specific CIDRs."
                ),
                effort="MEDIUM",
                impact="HIGH",
                cli_command=(
                    "# Scan IaC for this issue:\n"
                    "checkov -d . --check CKV_AWS_53,CKV_AWS_18,CKV_AWS_20\n"
                    "tfsec . --minimum-severity HIGH"
                ),
                console_url=None,
                rag_color="GREEN",
            ))

            # SCP / Guardrail prevention for governance findings
            actions.append(PrioritizedAction(
                title="Apply AWS Organizations SCP to prevent recurrence",
                description=(
                    "Create a Service Control Policy (SCP) at the AWS Organizations level "
                    "that denies the misconfigured API calls (e.g., s3:PutBucketAcl with "
                    "public grants, ec2:AuthorizeSecurityGroupIngress with 0.0.0.0/0). "
                    "SCPs enforce preventive guardrails across all accounts in the OU, "
                    "blocking the same issue from re-occurring in any account."
                ),
                effort="HIGH",
                impact="CRITICAL",
                cli_command=(
                    "aws organizations create-policy "
                    "--name PreventPublicS3 "
                    "--type SERVICE_CONTROL_POLICY "
                    "--description 'Prevent public S3 buckets and open security groups' "
                    "--content file://scp_prevent_public_access.json"
                ),
                console_url=(
                    "https://console.aws.amazon.com/organizations/v2/home/policies/"
                    "service-control-policy"
                ),
                rag_color="GREEN",
            ))

        actions.append(PrioritizedAction(
            title="Conduct quarterly IAM access reviews",
            description=(
                "Schedule quarterly access reviews using IAM Access Analyzer and "
                "AWS Organizations Service Control Policies to enforce least privilege at scale."
            ),
            effort="HIGH",
            impact="HIGH",
            cli_command=None,
            console_url="https://console.aws.amazon.com/iam/home#/access_analyzer",
            rag_color="GREEN",
        ))

        return actions

    # ── SLA and stakeholder helpers ───────────────────────────────────────────

    def _compute_sla(self, rag_level: str, finding: CanonicalFinding) -> int:
        """
        Compute SLA in days, adjusted by both RAG level and severity.

        SLA matrix:
        - RED + critical → 1 day  (critical breaches require same-day response)
        - RED + high     → 3 days
        - RED + other    → 3 days  (all RED findings must be resolved fast)
        - AMBER + critical → 7 days
        - AMBER + high     → 14 days
        - AMBER + other    → 14 days
        - GREEN + low/info → 90 days
        - GREEN + other    → 30 days
        """
        severity = str(finding.severity or "").lower()

        if rag_level == "RED":
            if severity == "critical":
                return 1
            return 3  # high or unknown RED

        if rag_level == "AMBER":
            if severity == "critical":
                return 7
            if severity == "high":
                return 14
            return 14  # medium AMBER

        # GREEN
        if severity in ("low", "info"):
            return 90
        return 30

    def _get_stakeholders(
        self,
        rag_level: str,
        finding: CanonicalFinding,
        causal: CausalAnalysis,
    ) -> list[str]:
        """
        Return context-aware stakeholder list based on RAG level and root cause.

        RED stakeholders are specialised by root cause type:
        - IAM issues → CISO, IAM Team, Security Team
        - Network issues → Security Team, Network Team, DevOps
        - Data issues → CISO, Data Protection Officer, Security Team
        - Default RED → Security Team, CISO, DevOps
        """
        cause = causal.primary_root_cause

        if rag_level == "RED":
            if cause == "iam_misconfiguration":
                return ["CISO", "IAM Team", "Security Team"]
            if cause == "network_misconfiguration":
                return ["Security Team", "Network Team", "DevOps"]
            if cause in ("governance_gap", "encryption_gap"):
                return ["CISO", "Data Protection Officer", "Security Team"]
            return ["Security Team", "CISO", "DevOps"]

        if rag_level == "AMBER":
            return ["Security Team", "DevOps"]

        return ["Security Team"]

    # ── ARN parsing helpers ───────────────────────────────────────────────────

    @staticmethod
    def _extract_s3_bucket(resource_arn: str | None) -> str | None:
        """Extract S3 bucket name from ARN: arn:aws:s3:::bucket-name"""
        if not resource_arn:
            return None
        m = re.search(r"arn:aws:s3:::([^/\s]+)", resource_arn)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _extract_ec2_instance(resource_arn: str | None) -> str | None:
        """Extract EC2 instance ID from ARN: .../instance/i-xxxx"""
        if not resource_arn:
            return None
        m = re.search(r"instance/(i-[a-f0-9]+)", resource_arn, re.IGNORECASE)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _extract_iam_user(resource_arn: str | None) -> str | None:
        """Extract IAM user name from ARN: arn:aws:iam::account:user/name"""
        if not resource_arn:
            return None
        m = re.search(r":user/([^/\s]+)", resource_arn)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _extract_iam_role(resource_arn: str | None) -> str | None:
        """Extract IAM role name from ARN: arn:aws:iam::account:role/name"""
        if not resource_arn:
            return None
        m = re.search(r":role/([^/\s]+)", resource_arn)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _extract_rds_identifier(resource_arn: str | None) -> str | None:
        """Extract RDS DB identifier from ARN: arn:aws:rds:region:account:db:identifier"""
        if not resource_arn:
            return None
        m = re.search(r":db:([^/\s:]+)", resource_arn)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _extract_sg_id(resource_arn: str | None) -> str | None:
        """Extract Security Group ID from ARN or resource ID: sg-xxxx"""
        if not resource_arn:
            return None
        m = re.search(r"(sg-[a-f0-9]+)", resource_arn, re.IGNORECASE)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _extract_lambda_function(resource_arn: str | None) -> str | None:
        """
        Extract Lambda function name from ARN.

        Formats:
        - arn:aws:lambda:region:account:function:function-name
        - arn:aws:lambda:region:account:function:function-name:qualifier
        """
        if not resource_arn:
            return None
        m = re.search(r":function:([^:/\s]+)", resource_arn, re.IGNORECASE)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _extract_kms_key_id(resource_arn: str | None) -> str | None:
        """
        Extract KMS key ID from ARN.

        Format: arn:aws:kms:region:account:key/key-id
        """
        if not resource_arn:
            return None
        m = re.search(r":key/([a-f0-9\-]+)", resource_arn, re.IGNORECASE)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _extract_secretsmanager_arn(resource_arn: str | None) -> str | None:
        """
        Extract SecretsManager secret name or return the full ARN.

        Format: arn:aws:secretsmanager:region:account:secret:name-suffix
        Returns the secret name portion (before the random suffix), or the full ARN.
        """
        if not resource_arn:
            return None
        # arn:aws:secretsmanager:region:account:secret:secret-name-xxxxxx
        m = re.search(r":secret:([^/\s]+)", resource_arn, re.IGNORECASE)
        if m:
            # Strip the 6-char random suffix AWS appends (e.g., "MySecret-AbCdEf")
            name_with_suffix = m.group(1)
            # Return the name without suffix if it matches the pattern
            clean = re.sub(r"-[A-Za-z0-9]{6}$", "", name_with_suffix)
            return clean or name_with_suffix
        # Fall back to the full ARN if it contains secretsmanager
        if "secretsmanager" in resource_arn.lower():
            return resource_arn
        return None

    @staticmethod
    def _extract_cloudtrail_name(resource_arn: str | None) -> str | None:
        """
        Extract CloudTrail trail name from ARN.

        Format: arn:aws:cloudtrail:region:account:trail/trail-name
        """
        if not resource_arn:
            return None
        m = re.search(r":trail/([^/\s]+)", resource_arn, re.IGNORECASE)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _days_open(finding: CanonicalFinding) -> int:
        """Compute how many days the finding has been open since first_seen_at."""
        if not finding.first_seen_at:
            return 0
        try:
            first = datetime.fromisoformat(str(finding.first_seen_at))
            if first.tzinfo is None:
                first = first.replace(tzinfo=UTC)
            return max(0, (datetime.now(UTC) - first).days)
        except (ValueError, TypeError):
            return 0
