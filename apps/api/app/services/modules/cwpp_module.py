"""
CWPPModule — Cloud Workload Protection Platform simulation.

Sprint 33: Simulates workload security:
1. CVE correlation for VM/container/serverless
2. Malware pattern detection
3. SBOM analysis
4. Runtime security assessment
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.canonical_finding import CanonicalFinding


# ── Workload type classification keywords ──────────────────────────────────

_VM_KEYWORDS = ("ec2", "instance", "ami", "ebs", "vm", "virtual machine", "ssm")
_CONTAINER_KEYWORDS = ("ecs", "eks", "container", "docker", "kubernetes", "k8s", "fargate", "ecr", "pod")
_SERVERLESS_KEYWORDS = ("lambda", "serverless", "function", "api gateway", "step function")

# CVE regex
_CVE_RE = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)

# ── Known malware / threat patterns (simplified simulation) ────────────────

_MALWARE_INDICATORS = [
    {"pattern": "crypto", "family": "CryptoMiner", "risk": "high"},
    {"pattern": "reverse shell", "family": "ReverseShell", "risk": "critical"},
    {"pattern": "backdoor", "family": "Backdoor", "risk": "critical"},
    {"pattern": "rootkit", "family": "Rootkit", "risk": "critical"},
    {"pattern": "ransomware", "family": "Ransomware", "risk": "critical"},
    {"pattern": "botnet", "family": "Botnet", "risk": "high"},
    {"pattern": "trojan", "family": "Trojan", "risk": "high"},
    {"pattern": "privilege escalation", "family": "PrivEsc", "risk": "high"},
    {"pattern": "lateral movement", "family": "LateralMovement", "risk": "high"},
    {"pattern": "exfiltration", "family": "DataExfil", "risk": "critical"},
]


def _classify_workload(title: str) -> str:
    """Classify a finding into a workload type based on title keywords."""
    lower = title.lower()
    if any(k in lower for k in _CONTAINER_KEYWORDS):
        return "container"
    if any(k in lower for k in _SERVERLESS_KEYWORDS):
        return "serverless"
    if any(k in lower for k in _VM_KEYWORDS):
        return "vm"
    return "other"


class CWPPModule:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def assess_workloads(self, workspace_id: uuid.UUID) -> dict:
        """Assess workload security posture across VM, container, and serverless."""
        result = await self.db.execute(
            select(CanonicalFinding).where(
                CanonicalFinding.workspace_id == workspace_id,
            )
        )
        findings = list(result.scalars().all())

        workloads: dict[str, dict[str, Any]] = {
            "vm": {
                "total_findings": 0,
                "open_findings": 0,
                "cves": [],
                "severity_breakdown": {"critical": 0, "high": 0, "medium": 0, "low": 0, "informational": 0},
                "malware_detections": [],
                "top_findings": [],
            },
            "container": {
                "total_findings": 0,
                "open_findings": 0,
                "cves": [],
                "severity_breakdown": {"critical": 0, "high": 0, "medium": 0, "low": 0, "informational": 0},
                "malware_detections": [],
                "top_findings": [],
            },
            "serverless": {
                "total_findings": 0,
                "open_findings": 0,
                "cves": [],
                "severity_breakdown": {"critical": 0, "high": 0, "medium": 0, "low": 0, "informational": 0},
                "malware_detections": [],
                "top_findings": [],
            },
        }

        all_cves: set[str] = set()

        for f in findings:
            wtype = _classify_workload(f.title or "")
            if wtype not in workloads:
                continue

            bucket = workloads[wtype]
            bucket["total_findings"] += 1
            if f.status == "open":
                bucket["open_findings"] += 1

            sev = (f.severity or "medium").lower()
            if sev in bucket["severity_breakdown"]:
                bucket["severity_breakdown"][sev] += 1

            # Extract CVEs from title + description
            text = f"{f.title or ''} {f.description or ''}"
            cves = _CVE_RE.findall(text)
            for cve in cves:
                cve_upper = cve.upper()
                if cve_upper not in all_cves:
                    all_cves.add(cve_upper)
                    bucket["cves"].append(cve_upper)

            # Check for malware indicators
            text_lower = text.lower()
            for indicator in _MALWARE_INDICATORS:
                if indicator["pattern"] in text_lower:
                    bucket["malware_detections"].append({
                        "finding_id": str(f.id),
                        "family": indicator["family"],
                        "risk": indicator["risk"],
                        "resource_arn": str(f.resource_arn or ""),
                    })

            # Collect top findings (limit to 5 per type)
            if len(bucket["top_findings"]) < 5 and f.status == "open":
                bucket["top_findings"].append({
                    "id": str(f.id),
                    "title": f.title,
                    "severity": f.severity,
                    "resource_arn": str(f.resource_arn or ""),
                })

        # De-duplicate malware detections per workload type
        for wtype in workloads:
            seen_families: set[str] = set()
            deduped: list[dict] = []
            for det in workloads[wtype]["malware_detections"]:
                key = f"{det['finding_id']}:{det['family']}"
                if key not in seen_families:
                    seen_families.add(key)
                    deduped.append(det)
            workloads[wtype]["malware_detections"] = deduped[:10]

        # Calculate overall workload protection score
        total_open = sum(w["open_findings"] for w in workloads.values())
        total_all = sum(w["total_findings"] for w in workloads.values())
        protection_score = round((1 - total_open / total_all) * 100, 1) if total_all > 0 else 100.0

        return {
            "workloads": workloads,
            "total_cves": len(all_cves),
            "total_malware_detections": sum(
                len(w["malware_detections"]) for w in workloads.values()
            ),
            "protection_score": protection_score,
            "total_findings": total_all,
            "total_open": total_open,
        }

    async def sbom_analysis(self, workspace_id: uuid.UUID) -> dict:
        """Analyze software bill of materials across workloads."""
        result = await self.db.execute(
            select(CanonicalFinding).where(
                CanonicalFinding.workspace_id == workspace_id,
            )
        )
        findings = list(result.scalars().all())

        # Aggregate CVE data and map to workload types
        cve_map: dict[str, dict[str, Any]] = {}
        dependency_risks: dict[str, list[str]] = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
        }

        for f in findings:
            text = f"{f.title or ''} {f.description or ''}"
            cves = _CVE_RE.findall(text)
            wtype = _classify_workload(f.title or "")

            for cve in cves:
                cve_upper = cve.upper()
                if cve_upper not in cve_map:
                    cve_map[cve_upper] = {
                        "cve_id": cve_upper,
                        "workload_types": set(),
                        "affected_resources": [],
                        "severity": f.severity,
                        "finding_count": 0,
                    }
                entry = cve_map[cve_upper]
                entry["workload_types"].add(wtype)
                entry["finding_count"] += 1
                if f.resource_arn and len(entry["affected_resources"]) < 10:
                    entry["affected_resources"].append(str(f.resource_arn))

                # Categorize by severity
                sev = (f.severity or "medium").lower()
                if sev in dependency_risks and cve_upper not in dependency_risks[sev]:
                    dependency_risks[sev].append(cve_upper)

        # Convert sets to lists for JSON serialization
        cve_list = []
        for cve_id, info in cve_map.items():
            cve_list.append({
                "cve_id": info["cve_id"],
                "workload_types": sorted(info["workload_types"]),
                "affected_resources": info["affected_resources"],
                "severity": info["severity"],
                "finding_count": info["finding_count"],
            })

        # Sort by finding_count descending
        cve_list.sort(key=lambda x: x["finding_count"], reverse=True)

        # Identify critical dependencies (CVEs appearing in multiple workload types)
        cross_workload_cves = [
            c for c in cve_list if len(c["workload_types"]) > 1
        ]

        return {
            "total_cves": len(cve_list),
            "cves": cve_list[:50],  # Limit response size
            "cross_workload_cves": cross_workload_cves[:20],
            "dependency_risks": {
                k: v[:20] for k, v in dependency_risks.items()
            },
            "risk_summary": {
                "critical_cves": len(dependency_risks["critical"]),
                "high_cves": len(dependency_risks["high"]),
                "medium_cves": len(dependency_risks["medium"]),
                "low_cves": len(dependency_risks["low"]),
            },
        }

    async def runtime_assessment(self, workspace_id: uuid.UUID) -> dict:
        """Assess runtime security posture for containers and serverless."""
        result = await self.db.execute(
            select(CanonicalFinding).where(
                CanonicalFinding.workspace_id == workspace_id,
                CanonicalFinding.status == "open",
            )
        )
        findings = list(result.scalars().all())

        # Runtime security checks organized by domain
        runtime_checks = {
            "container_image_security": {
                "description": "Container image signing, vulnerability scanning, base image currency",
                "total_checks": 45,
                "passed": 0,
                "failed": 0,
                "issues": [],
            },
            "container_runtime": {
                "description": "Syscall policies, privilege escalation, namespace isolation",
                "total_checks": 38,
                "passed": 0,
                "failed": 0,
                "issues": [],
            },
            "serverless_config": {
                "description": "Function permissions, timeout settings, environment variables",
                "total_checks": 30,
                "passed": 0,
                "failed": 0,
                "issues": [],
            },
            "network_segmentation": {
                "description": "East-west traffic controls, service mesh policies",
                "total_checks": 25,
                "passed": 0,
                "failed": 0,
                "issues": [],
            },
            "secrets_management": {
                "description": "Hardcoded secrets, rotation policies, vault integration",
                "total_checks": 20,
                "passed": 0,
                "failed": 0,
                "issues": [],
            },
        }

        # Classify open findings into runtime check categories
        for f in findings:
            title_lower = (f.title or "").lower()
            desc_lower = (f.description or "").lower()
            combined = f"{title_lower} {desc_lower}"

            issue_entry = {
                "id": str(f.id),
                "title": f.title,
                "severity": f.severity,
                "resource_arn": str(f.resource_arn or ""),
            }

            if any(k in combined for k in ("image", "ecr", "registry", "base image", "scan")):
                cat = "container_image_security"
            elif any(k in combined for k in ("syscall", "privilege", "namespace", "seccomp", "apparmor", "capabilities")):
                cat = "container_runtime"
            elif any(k in combined for k in ("lambda", "function", "serverless", "timeout", "concurrency")):
                cat = "serverless_config"
            elif any(k in combined for k in ("network", "segmentation", "service mesh", "east-west", "vpc")):
                cat = "network_segmentation"
            elif any(k in combined for k in ("secret", "credential", "password", "token", "key rotation", "vault")):
                cat = "secrets_management"
            else:
                continue

            runtime_checks[cat]["failed"] += 1
            if len(runtime_checks[cat]["issues"]) < 10:
                runtime_checks[cat]["issues"].append(issue_entry)

        # Calculate passed for each category
        for check in runtime_checks.values():
            check["passed"] = max(0, check["total_checks"] - check["failed"])
            check["pass_rate"] = round(
                check["passed"] / check["total_checks"] * 100, 1
            ) if check["total_checks"] > 0 else 100.0

        total_checks = sum(c["total_checks"] for c in runtime_checks.values())
        total_failed = sum(c["failed"] for c in runtime_checks.values())
        total_passed = total_checks - total_failed

        return {
            "runtime_checks": runtime_checks,
            "total_checks": total_checks,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "runtime_score": round(total_passed / total_checks * 100, 1) if total_checks > 0 else 100.0,
        }
