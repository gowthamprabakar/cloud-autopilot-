"""
CSPMModule — Cloud Security Posture Management simulation.

Sprint 33: Simulates Wiz CSPM capabilities:
1. Configuration rule evaluation (2800+ rules)
2. Compliance framework mapping (CIS, NIST, SOC2, PCI-DSS)
3. Security graph toxic combination detection
4. Auto-remediation IaC generation
5. Posture score calculation
"""

from __future__ import annotations
import uuid, json
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.canonical_finding import CanonicalFinding


class CSPMModule:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate_posture(self, workspace_id: uuid.UUID) -> dict:
        """Run CSPM posture evaluation against all findings."""
        # Query all findings
        result = await self.db.execute(
            select(CanonicalFinding).where(CanonicalFinding.workspace_id == workspace_id)
        )
        findings = list(result.scalars().all())

        # Categorize by rule type
        categories = {
            "network": {"rules": 450, "passed": 0, "failed": 0, "findings": []},
            "identity": {"rules": 380, "passed": 0, "failed": 0, "findings": []},
            "encryption": {"rules": 290, "passed": 0, "failed": 0, "findings": []},
            "logging": {"rules": 210, "passed": 0, "failed": 0, "findings": []},
            "compute": {"rules": 320, "passed": 0, "failed": 0, "findings": []},
            "storage": {"rules": 280, "passed": 0, "failed": 0, "findings": []},
            "database": {"rules": 190, "passed": 0, "failed": 0, "findings": []},
            "container": {"rules": 250, "passed": 0, "failed": 0, "findings": []},
            "serverless": {"rules": 180, "passed": 0, "failed": 0, "findings": []},
            "compliance": {"rules": 250, "passed": 0, "failed": 0, "findings": []},
        }

        # Classify findings into categories
        for f in findings:
            title_lower = (f.title or "").lower()
            if f.status != "open":
                continue

            cat = "compliance"  # default
            if any(k in title_lower for k in ("security group", "network", "vpc", "firewall", "port", "ingress")):
                cat = "network"
            elif any(k in title_lower for k in ("iam", "role", "user", "policy", "mfa", "access key")):
                cat = "identity"
            elif any(k in title_lower for k in ("encrypt", "kms", "ssl", "tls", "certificate")):
                cat = "encryption"
            elif any(k in title_lower for k in ("log", "trail", "monitor", "cloudwatch", "audit")):
                cat = "logging"
            elif any(k in title_lower for k in ("ec2", "instance", "ami", "ebs")):
                cat = "compute"
            elif any(k in title_lower for k in ("s3", "bucket", "storage", "glacier")):
                cat = "storage"
            elif any(k in title_lower for k in ("rds", "database", "dynamodb", "aurora")):
                cat = "database"
            elif any(k in title_lower for k in ("ecs", "eks", "container", "docker", "kubernetes")):
                cat = "container"
            elif any(k in title_lower for k in ("lambda", "serverless", "function")):
                cat = "serverless"

            categories[cat]["failed"] += 1
            categories[cat]["findings"].append({
                "id": str(f.id),
                "title": f.title,
                "severity": f.severity,
                "resource_arn": str(f.resource_arn or ""),
            })

        # Calculate passed = rules - failed (simplified)
        for cat in categories.values():
            cat["passed"] = max(0, cat["rules"] - cat["failed"])
            cat["pass_rate"] = round(cat["passed"] / cat["rules"] * 100, 1) if cat["rules"] > 0 else 100.0
            # Limit findings in response
            cat["findings"] = cat["findings"][:10]

        total_rules = sum(c["rules"] for c in categories.values())
        total_failed = sum(c["failed"] for c in categories.values())
        total_passed = total_rules - total_failed

        # Compliance framework mapping
        frameworks = await self._map_compliance_frameworks(findings)

        return {
            "total_rules": total_rules,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "posture_score": round(total_passed / total_rules * 100, 1) if total_rules > 0 else 100.0,
            "categories": categories,
            "frameworks": frameworks,
            "total_findings": len(findings),
            "open_findings": sum(1 for f in findings if f.status == "open"),
        }

    async def _map_compliance_frameworks(self, findings: list) -> dict:
        """Map findings to compliance frameworks."""
        frameworks = {
            "CIS AWS 3.0": {"total_controls": 120, "passed": 0, "failed": 0},
            "NIST 800-53": {"total_controls": 260, "passed": 0, "failed": 0},
            "SOC 2 Type II": {"total_controls": 80, "passed": 0, "failed": 0},
            "PCI-DSS 4.0": {"total_controls": 64, "passed": 0, "failed": 0},
            "HIPAA": {"total_controls": 45, "passed": 0, "failed": 0},
            "GDPR": {"total_controls": 35, "passed": 0, "failed": 0},
        }

        open_count = sum(1 for f in findings if f.status == "open")
        for fw_name, fw in frameworks.items():
            # Proportional mapping: distribute failures across frameworks
            fw["failed"] = min(fw["total_controls"], int(open_count * 0.3))
            fw["passed"] = fw["total_controls"] - fw["failed"]
            fw["score"] = round(fw["passed"] / fw["total_controls"] * 100, 1)

        return frameworks

    async def generate_remediation(self, workspace_id: uuid.UUID, finding_id: str) -> dict:
        """Generate IaC remediation for a specific finding."""
        finding = await self.db.get(CanonicalFinding, finding_id)
        if not finding:
            return {"error": "Finding not found"}

        title = (finding.title or "").lower()

        # Generate Terraform remediation based on finding type
        terraform = "# Auto-generated remediation\n"
        if "s3" in title and "public" in title:
            terraform += '''resource "aws_s3_bucket_public_access_block" "remediate" {
  bucket                  = "BUCKET_NAME"
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}'''
        elif "encrypt" in title:
            terraform += '''resource "aws_s3_bucket_server_side_encryption_configuration" "remediate" {
  bucket = "BUCKET_NAME"
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}'''
        elif "security group" in title:
            terraform += '''resource "aws_security_group_rule" "remediate" {
  type              = "ingress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["10.0.0.0/8"]  # Restrict to VPC CIDR
  security_group_id = "SECURITY_GROUP_ID"
}'''
        elif "mfa" in title:
            terraform += '''resource "aws_iam_user_policy" "require_mfa" {
  name   = "require-mfa"
  user   = "USER_NAME"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyAllExceptMFA"
      Effect    = "Deny"
      NotAction = ["iam:CreateVirtualMFADevice", "iam:EnableMFADevice"]
      Resource  = "*"
      Condition = { BoolIfExists = { "aws:MultiFactorAuthPresent" = "false" } }
    }]
  })
}'''
        else:
            terraform += f'# TODO: Generate remediation for: {finding.title}'

        return {
            "finding_id": str(finding.id),
            "finding_title": finding.title,
            "severity": finding.severity,
            "terraform": terraform,
            "description": f"Auto-generated IaC remediation for {finding.title}",
        }
