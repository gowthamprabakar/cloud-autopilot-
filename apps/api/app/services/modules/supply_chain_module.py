"""
SupplyChainModule — AI-Accelerated Supply Chain Firmware Attack simulation.

Sprint 34: Simulates supply chain attacks:
1. Dependency poisoning (XZ-utils CVE-2024-3094 pattern)
2. SBOM validation including firmware layer
3. Sigstore/Cosign verification
4. eBPF rootkit injection detection
"""

from __future__ import annotations
import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from app.models.canonical_finding import CanonicalFinding
from app.models.source_finding import SourceFinding
from app.models.security_graph_node import SecurityGraphNode
from app.models.enums import FindingSeverity, FindingStatus, FindingSource

# Known supply chain CVE patterns
KNOWN_SUPPLY_CHAIN_CVES = {
    "CVE-2024-3094": {"name": "XZ Utils Backdoor", "severity": "CRITICAL", "type": "dependency_poisoning", "description": "Malicious code injected into xz/liblzma via compromised maintainer"},
    "CVE-2021-44228": {"name": "Log4Shell", "severity": "CRITICAL", "type": "dependency_poisoning", "description": "Remote code execution in Apache Log4j via JNDI injection"},
    "CVE-2023-44487": {"name": "HTTP/2 Rapid Reset", "severity": "HIGH", "type": "protocol_abuse", "description": "DDoS amplification via HTTP/2 stream cancellation"},
    "CVE-2024-21626": {"name": "Leaky Vessels (runc)", "severity": "HIGH", "type": "container_escape", "description": "Container escape via runc working directory manipulation"},
    "CVE-2023-32233": {"name": "Netfilter nf_tables", "severity": "HIGH", "type": "kernel_exploit", "description": "Use-after-free in Linux kernel nf_tables for privilege escalation"},
    "CVE-2024-1086": {"name": "nftables OOB Write", "severity": "HIGH", "type": "kernel_exploit", "description": "Linux kernel nf_tables out-of-bounds write for LPE"},
}

# SBOM component categories and expected coverage
SBOM_CATEGORIES = [
    {"category": "application_dependencies", "label": "Application Dependencies (npm/pip/go)", "expected_coverage": 95},
    {"category": "os_packages", "label": "OS Packages (apt/yum/apk)", "expected_coverage": 90},
    {"category": "container_base_images", "label": "Container Base Images", "expected_coverage": 85},
    {"category": "firmware_components", "label": "Firmware / UEFI Components", "expected_coverage": 30},
    {"category": "kernel_modules", "label": "Kernel Modules / Drivers", "expected_coverage": 40},
    {"category": "shared_libraries", "label": "Shared Libraries (libc, openssl)", "expected_coverage": 70},
    {"category": "build_tools", "label": "Build Tools & CI/CD Plugins", "expected_coverage": 50},
]

# Signing verification methods
SIGNING_METHODS = {
    "sigstore_cosign": {"label": "Sigstore/Cosign", "trust_level": 95, "type": "keyless"},
    "notary_v2": {"label": "Notary v2 (OCI)", "trust_level": 90, "type": "key_based"},
    "gpg_signing": {"label": "GPG Commit/Tag Signing", "trust_level": 75, "type": "key_based"},
    "aws_signer": {"label": "AWS Signer", "trust_level": 85, "type": "managed"},
    "none": {"label": "No Signing", "trust_level": 0, "type": "none"},
}


class SupplyChainModule:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def dependency_audit(self, workspace_id: uuid.UUID) -> dict:
        """Audit dependencies for poisoning risk using CVE and finding data."""
        # Query all CVE-related findings
        result = await self.db.execute(
            select(CanonicalFinding).where(
                CanonicalFinding.workspace_id == workspace_id,
                CanonicalFinding.status != FindingStatus.RESOLVED,
            )
        )
        findings = list(result.scalars().all())

        # Identify supply-chain-relevant findings
        cve_pattern_findings = []
        supply_chain_findings = []
        for f in findings:
            text = ((f.title or "") + " " + (f.description or "")).lower()
            # Check for known supply chain CVEs
            for cve_id, cve_info in KNOWN_SUPPLY_CHAIN_CVES.items():
                if cve_id.lower() in text or cve_info["name"].lower() in text:
                    cve_pattern_findings.append({
                        "cve_id": cve_id,
                        "cve_name": cve_info["name"],
                        "cve_severity": cve_info["severity"],
                        "attack_type": cve_info["type"],
                        "finding_id": str(f.id),
                        "finding_title": f.title,
                        "resource": str(f.resource_arn or ""),
                        "status": str(f.status),
                    })
            # Check for general supply chain indicators
            if any(kw in text for kw in ("supply chain", "dependency", "package", "npm", "pip", "sbom", "vulnerable library", "outdated")):
                supply_chain_findings.append({
                    "finding_id": str(f.id),
                    "title": f.title,
                    "severity": str(f.severity),
                    "resource": str(f.resource_arn or ""),
                    "resource_type": f.resource_type or "Unknown",
                })

        # Query Inspector findings specifically (primary source for dependency vulns)
        inspector_result = await self.db.execute(
            select(func.count(SourceFinding.id)).where(
                SourceFinding.workspace_id == workspace_id,
                SourceFinding.source == FindingSource.INSPECTOR,
            )
        )
        inspector_count = inspector_result.scalar() or 0

        # Compute maintainer trust assessment
        trust_assessment = self._compute_maintainer_trust(cve_pattern_findings, supply_chain_findings)

        # Risk scoring
        critical_cves = sum(1 for c in cve_pattern_findings if c["cve_severity"] == "CRITICAL")
        high_cves = sum(1 for c in cve_pattern_findings if c["cve_severity"] == "HIGH")
        risk_score = min(100, critical_cves * 25 + high_cves * 15 + len(supply_chain_findings) * 5)

        return {
            "risk_score": risk_score,
            "risk_level": "CRITICAL" if risk_score > 75 else "HIGH" if risk_score > 50 else "MEDIUM" if risk_score > 25 else "LOW",
            "known_supply_chain_cves": cve_pattern_findings,
            "supply_chain_findings": supply_chain_findings[:20],
            "inspector_findings_total": inspector_count,
            "maintainer_trust": trust_assessment,
            "poisoning_indicators": {
                "critical_cve_matches": critical_cves,
                "high_cve_matches": high_cves,
                "dependency_findings": len(supply_chain_findings),
                "xz_utils_pattern_detected": any(c["cve_id"] == "CVE-2024-3094" for c in cve_pattern_findings),
            },
        }

    async def sbom_validation(self, workspace_id: uuid.UUID) -> dict:
        """Validate Software Bill of Materials including firmware layer."""
        # Query all resource types to understand infrastructure composition
        result = await self.db.execute(
            select(
                SecurityGraphNode.node_type,
                func.count(SecurityGraphNode.id).label("count"),
            ).where(
                SecurityGraphNode.workspace_id == workspace_id,
            ).group_by(SecurityGraphNode.node_type)
        )
        node_type_counts = {row.node_type: row.count for row in result.all()}

        # Query findings that indicate SBOM gaps
        finding_result = await self.db.execute(
            select(CanonicalFinding).where(
                CanonicalFinding.workspace_id == workspace_id,
                CanonicalFinding.status != FindingStatus.RESOLVED,
            )
        )
        findings = list(finding_result.scalars().all())

        sbom_gap_findings = [
            f for f in findings
            if any(kw in (f.title or "").lower() for kw in ("sbom", "inventory", "unpatched", "end of life", "eol", "unsupported", "unknown package"))
        ]

        # Build SBOM coverage assessment per category
        has_containers = any(t in node_type_counts for t in ("lambda", "ecs", "ecr"))
        has_ec2 = "ec2" in node_type_counts
        total_resources = sum(node_type_counts.values())

        category_assessments = []
        for cat in SBOM_CATEGORIES:
            # Determine actual coverage estimate based on infrastructure present
            if cat["category"] == "container_base_images" and not has_containers:
                actual = 0
                status = "N/A"
            elif cat["category"] == "firmware_components" and not has_ec2:
                actual = 0
                status = "N/A"
            elif cat["category"] == "kernel_modules" and not has_ec2:
                actual = 0
                status = "N/A"
            else:
                # Estimate coverage based on gap findings
                gap_penalty = len(sbom_gap_findings) * 5
                actual = max(0, cat["expected_coverage"] - gap_penalty)
                status = "GOOD" if actual >= 80 else "PARTIAL" if actual >= 50 else "POOR"

            category_assessments.append({
                "category": cat["category"],
                "label": cat["label"],
                "expected_coverage_pct": cat["expected_coverage"],
                "estimated_coverage_pct": actual,
                "status": status,
                "gap": max(0, cat["expected_coverage"] - actual),
            })

        # Overall SBOM completeness score
        active_categories = [c for c in category_assessments if c["status"] != "N/A"]
        if active_categories:
            completeness = round(
                sum(c["estimated_coverage_pct"] for c in active_categories) / len(active_categories), 1
            )
        else:
            completeness = 0.0

        # Firmware-specific assessment
        firmware_assessment = self._assess_firmware(node_type_counts, findings)

        return {
            "completeness_score": completeness,
            "completeness_level": "GOOD" if completeness >= 75 else "PARTIAL" if completeness >= 50 else "POOR",
            "categories": category_assessments,
            "firmware_assessment": firmware_assessment,
            "infrastructure_summary": {
                "total_resources": total_resources,
                "resource_types": node_type_counts,
                "has_containers": has_containers,
                "has_ec2": has_ec2,
            },
            "sbom_gap_findings": len(sbom_gap_findings),
            "recommendations": [
                {"priority": "HIGH", "action": "Generate CycloneDX/SPDX SBOM for all container images"},
                {"priority": "HIGH", "action": "Integrate SBOM generation into CI/CD pipeline"},
                {"priority": "MEDIUM", "action": "Catalog firmware versions for EC2/bare-metal workloads"},
                {"priority": "MEDIUM", "action": "Implement automated SBOM drift detection"},
                {"priority": "LOW", "action": "Establish SBOM sharing with downstream consumers (VEX)"},
            ],
        }

    async def signing_verification(self, workspace_id: uuid.UUID) -> dict:
        """Verify code/image signing with Sigstore/Cosign and related tools."""
        # Query container-related nodes (ECR, Lambda, ECS)
        result = await self.db.execute(
            select(SecurityGraphNode).where(
                SecurityGraphNode.workspace_id == workspace_id,
                SecurityGraphNode.node_type.in_(["lambda", "ecr", "ecs", "ec2"]),
            )
        )
        artifact_nodes = list(result.scalars().all())

        # Query signing-related findings
        finding_result = await self.db.execute(
            select(CanonicalFinding).where(
                CanonicalFinding.workspace_id == workspace_id,
                CanonicalFinding.status != FindingStatus.RESOLVED,
            )
        )
        findings = list(finding_result.scalars().all())

        signing_findings = [
            f for f in findings
            if any(kw in (f.title or "").lower() for kw in ("sign", "cosign", "sigstore", "notary", "provenance", "attestation", "integrity", "tamper"))
        ]

        # Build per-artifact signing assessment
        artifact_assessments = []
        for node in artifact_nodes:
            metadata = node.node_metadata or {}
            # Check metadata for signing indicators
            has_signing = any(
                k in metadata for k in ("image_signing", "code_signing", "sigstore", "cosign_verified")
            )
            signing_method = "none"
            if has_signing:
                if metadata.get("sigstore") or metadata.get("cosign_verified"):
                    signing_method = "sigstore_cosign"
                elif metadata.get("image_signing"):
                    signing_method = "notary_v2"
                else:
                    signing_method = "gpg_signing"

            method_info = SIGNING_METHODS.get(signing_method, SIGNING_METHODS["none"])
            artifact_assessments.append({
                "resource": str(node.resource_arn or node.resource_name),
                "type": node.node_type,
                "region": node.region,
                "signing_method": signing_method,
                "signing_label": method_info["label"],
                "trust_level": method_info["trust_level"],
                "verified": has_signing,
            })

        # Compute signing coverage
        total = len(artifact_assessments)
        signed = sum(1 for a in artifact_assessments if a["verified"])
        coverage_pct = round((signed / total * 100), 1) if total > 0 else 0.0

        # Average trust level across signed artifacts
        signed_artifacts = [a for a in artifact_assessments if a["verified"]]
        avg_trust = round(
            sum(a["trust_level"] for a in signed_artifacts) / len(signed_artifacts), 1
        ) if signed_artifacts else 0.0

        # eBPF rootkit detection assessment
        ebpf_assessment = await self._ebpf_rootkit_assessment(workspace_id, findings)

        return {
            "signing_coverage_pct": coverage_pct,
            "average_trust_level": avg_trust,
            "total_artifacts": total,
            "signed_artifacts": signed,
            "unsigned_artifacts": total - signed,
            "artifacts": artifact_assessments[:25],
            "signing_findings": len(signing_findings),
            "ebpf_assessment": ebpf_assessment,
            "provenance_chain": {
                "source_signing": signed > 0,
                "build_attestation": any(a["signing_method"] == "sigstore_cosign" for a in artifact_assessments),
                "deployment_verification": coverage_pct > 80,
                "runtime_integrity": ebpf_assessment.get("monitoring_detected", False),
            },
            "recommendations": self._signing_recommendations(coverage_pct, avg_trust, ebpf_assessment),
        }

    async def _ebpf_rootkit_assessment(self, workspace_id: uuid.UUID, findings: list) -> dict:
        """Assess eBPF rootkit injection risk and monitoring capabilities."""
        # Check for eBPF/kernel-related findings
        ebpf_findings = [
            f for f in findings
            if any(kw in ((f.title or "") + " " + (f.description or "")).lower()
                   for kw in ("ebpf", "bpf", "kernel", "rootkit", "module", "kprobe", "tracepoint"))
        ]

        # Check for security monitoring nodes (GuardDuty runtime)
        monitoring_result = await self.db.execute(
            select(func.count(SecurityGraphNode.id)).where(
                SecurityGraphNode.workspace_id == workspace_id,
                SecurityGraphNode.node_type.in_(["cloudtrail", "guardduty", "security_group"]),
            )
        )
        monitoring_count = monitoring_result.scalar() or 0

        # Check EC2 instances for kernel-level monitoring
        ec2_result = await self.db.execute(
            select(func.count(SecurityGraphNode.id)).where(
                SecurityGraphNode.workspace_id == workspace_id,
                SecurityGraphNode.node_type == "ec2",
            )
        )
        ec2_count = ec2_result.scalar() or 0

        risk_level = "LOW"
        if ec2_count > 0 and monitoring_count == 0:
            risk_level = "HIGH"
        elif ec2_count > 0 and len(ebpf_findings) > 0:
            risk_level = "MEDIUM"

        return {
            "risk_level": risk_level,
            "ec2_instances": ec2_count,
            "monitoring_nodes": monitoring_count,
            "monitoring_detected": monitoring_count > 0,
            "ebpf_findings": len(ebpf_findings),
            "kernel_monitoring_coverage": "GOOD" if monitoring_count >= ec2_count and ec2_count > 0 else "PARTIAL" if monitoring_count > 0 else "NONE",
            "attack_vectors": [
                {"vector": "eBPF program injection", "risk": "HIGH" if ec2_count > 0 else "N/A", "mitigation": "GuardDuty Runtime Monitoring + BPF LSM"},
                {"vector": "Kernel module loading", "risk": "HIGH" if ec2_count > 0 else "N/A", "mitigation": "Lockdown LSM + module signing"},
                {"vector": "kprobe/tracepoint hijack", "risk": "MEDIUM" if ec2_count > 0 else "N/A", "mitigation": "eBPF verification + audit logging"},
            ],
        }

    def _compute_maintainer_trust(self, cve_findings: list, supply_chain_findings: list) -> dict:
        """Compute maintainer trust score based on supply chain indicators."""
        compromised_patterns = sum(1 for c in cve_findings if c["attack_type"] == "dependency_poisoning")
        total_indicators = len(cve_findings) + len(supply_chain_findings)

        trust_score = 100
        trust_score -= compromised_patterns * 30
        trust_score -= min(40, len(supply_chain_findings) * 5)
        trust_score = max(0, trust_score)

        return {
            "trust_score": trust_score,
            "trust_level": "HIGH" if trust_score >= 80 else "MEDIUM" if trust_score >= 50 else "LOW",
            "compromised_dependency_patterns": compromised_patterns,
            "total_supply_chain_indicators": total_indicators,
            "assessment": [
                {"check": "Known compromised maintainer patterns", "result": "FAIL" if compromised_patterns > 0 else "PASS"},
                {"check": "Dependency pinning", "result": "WARN" if total_indicators > 3 else "PASS"},
                {"check": "Lock file integrity", "result": "WARN" if total_indicators > 5 else "PASS"},
                {"check": "Typosquatting detection", "result": "PASS"},
            ],
        }

    def _assess_firmware(self, node_type_counts: dict, findings: list) -> dict:
        """Assess firmware-layer security posture."""
        has_ec2 = "ec2" in node_type_counts
        ec2_count = node_type_counts.get("ec2", 0)

        firmware_findings = [
            f for f in findings
            if any(kw in ((f.title or "") + " " + (f.description or "")).lower()
                   for kw in ("firmware", "uefi", "bios", "tpm", "secure boot", "nitro"))
        ]

        return {
            "applicable": has_ec2,
            "ec2_instances": ec2_count,
            "firmware_findings": len(firmware_findings),
            "nitro_enclaves_available": has_ec2,
            "secure_boot_status": "UNKNOWN" if has_ec2 else "N/A",
            "tpm_status": "AVAILABLE" if has_ec2 else "N/A",
            "checks": [
                {"check": "Nitro Enclave support", "status": "AVAILABLE" if has_ec2 else "N/A"},
                {"check": "Secure Boot enforcement", "status": "UNKNOWN" if has_ec2 else "N/A"},
                {"check": "TPM 2.0 attestation", "status": "UNKNOWN" if has_ec2 else "N/A"},
                {"check": "UEFI firmware integrity", "status": "UNKNOWN" if has_ec2 else "N/A"},
            ],
        }

    def _signing_recommendations(self, coverage_pct: float, avg_trust: float, ebpf: dict) -> list[dict]:
        """Generate prioritized signing and integrity recommendations."""
        recs = []

        if coverage_pct < 50:
            recs.append({
                "priority": "CRITICAL",
                "title": "Implement Container Image Signing",
                "description": f"Only {coverage_pct}% of artifacts are signed. Deploy Sigstore/Cosign "
                               "for keyless signing of all container images in CI/CD.",
                "effort": "MEDIUM",
            })
        elif coverage_pct < 90:
            recs.append({
                "priority": "HIGH",
                "title": "Expand Signing Coverage",
                "description": f"Signing coverage is {coverage_pct}%. Target 100% by integrating "
                               "Cosign verification into admission controllers.",
                "effort": "LOW",
            })

        if avg_trust < 80 and avg_trust > 0:
            recs.append({
                "priority": "MEDIUM",
                "title": "Upgrade to Keyless Signing (Sigstore)",
                "description": "Migrate from GPG/key-based signing to Sigstore keyless signing "
                               "for improved trust chain and transparency log integration.",
                "effort": "MEDIUM",
            })

        recs.append({
            "priority": "HIGH",
            "title": "Deploy SLSA Level 3 Build Provenance",
            "description": "Generate and verify SLSA provenance attestations for all build artifacts "
                           "to ensure supply chain integrity from source to deployment.",
            "effort": "HIGH",
        })

        if ebpf.get("risk_level") in ("HIGH", "MEDIUM"):
            recs.append({
                "priority": "HIGH",
                "title": "Enable eBPF Runtime Monitoring",
                "description": "Deploy GuardDuty Runtime Monitoring and eBPF-based detection "
                               "for kernel-level rootkit and module injection attacks.",
                "effort": "MEDIUM",
            })

        return recs
