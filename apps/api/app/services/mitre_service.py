"""
MITREService — ATT&CK and D3FEND mapping for OmniSec.

Sprint 33: Provides technique mapping, coverage analysis, and heatmap data.
Covers MITRE ATT&CK for Cloud (IaaS) and MITRE D3FEND countermeasures.
"""

from __future__ import annotations
import uuid, json, re
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.canonical_finding import CanonicalFinding
from app.models.swarm_agent import SwarmAgent
from app.models.simulation_run import SimulationRun


# MITRE ATT&CK Cloud Techniques (IaaS subset)
ATTACK_TECHNIQUES: dict[str, dict] = {
    "T1078": {"name": "Valid Accounts", "tactic": "Persistence", "subtechniques": ["T1078.001", "T1078.004"]},
    "T1078.004": {"name": "Cloud Accounts", "tactic": "Persistence", "parent": "T1078"},
    "T1190": {"name": "Exploit Public-Facing Application", "tactic": "Initial Access"},
    "T1098": {"name": "Account Manipulation", "tactic": "Persistence", "subtechniques": ["T1098.001", "T1098.003"]},
    "T1530": {"name": "Data from Cloud Storage", "tactic": "Collection"},
    "T1537": {"name": "Transfer Data to Cloud Account", "tactic": "Exfiltration"},
    "T1562": {"name": "Impair Defenses", "tactic": "Defense Evasion", "subtechniques": ["T1562.001", "T1562.007", "T1562.008"]},
    "T1562.008": {"name": "Disable Cloud Logs", "tactic": "Defense Evasion", "parent": "T1562"},
    "T1556": {"name": "Modify Authentication Process", "tactic": "Credential Access"},
    "T1021": {"name": "Remote Services", "tactic": "Lateral Movement"},
    "T1021.007": {"name": "Cloud Services", "tactic": "Lateral Movement", "parent": "T1021"},
    "T1580": {"name": "Cloud Infrastructure Discovery", "tactic": "Discovery"},
    "T1526": {"name": "Cloud Service Discovery", "tactic": "Discovery"},
    "T1578": {"name": "Modify Cloud Compute Infrastructure", "tactic": "Defense Evasion"},
    "T1552": {"name": "Unsecured Credentials", "tactic": "Credential Access", "subtechniques": ["T1552.001", "T1552.005"]},
    "T1552.005": {"name": "Cloud Instance Metadata API", "tactic": "Credential Access", "parent": "T1552"},
    "T1535": {"name": "Unused/Unsupported Cloud Regions", "tactic": "Defense Evasion"},
    "T1496": {"name": "Resource Hijacking", "tactic": "Impact"},
    "T1485": {"name": "Data Destruction", "tactic": "Impact"},
    "T1486": {"name": "Data Encrypted for Impact", "tactic": "Impact"},
    "T1498": {"name": "Network Denial of Service", "tactic": "Impact"},
    "T1525": {"name": "Implant Internal Image", "tactic": "Persistence"},
    "T1204": {"name": "User Execution", "tactic": "Execution"},
    "T1059": {"name": "Command and Scripting Interpreter", "tactic": "Execution"},
    "T1087": {"name": "Account Discovery", "tactic": "Discovery", "subtechniques": ["T1087.004"]},
    "T1087.004": {"name": "Cloud Account", "tactic": "Discovery", "parent": "T1087"},
    "T1069": {"name": "Permission Groups Discovery", "tactic": "Discovery", "subtechniques": ["T1069.003"]},
    "T1069.003": {"name": "Cloud Groups", "tactic": "Discovery", "parent": "T1069"},
    "T1136": {"name": "Create Account", "tactic": "Persistence", "subtechniques": ["T1136.003"]},
    "T1136.003": {"name": "Cloud Account", "tactic": "Persistence", "parent": "T1136"},
}

# MITRE ATT&CK Tactics (Cloud)
TACTICS = [
    "Initial Access", "Execution", "Persistence", "Privilege Escalation",
    "Defense Evasion", "Credential Access", "Discovery", "Lateral Movement",
    "Collection", "Exfiltration", "Impact",
]

# D3FEND countermeasure categories
D3FEND_CATEGORIES = {
    "Harden": ["Application Hardening", "Credential Hardening", "Platform Hardening"],
    "Detect": ["File Analysis", "Identifier Analysis", "Network Traffic Analysis", "Process Analysis"],
    "Isolate": ["Execution Isolation", "Network Isolation"],
    "Deceive": ["Decoy Environment", "Decoy Object"],
    "Evict": ["Credential Eviction", "Process Eviction"],
}


class MITREService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_technique_coverage(self, workspace_id: uuid.UUID) -> dict:
        """Analyze which ATT&CK techniques are covered by detection rules."""
        # Query detection alerts and findings for technique references
        findings = await self.db.execute(
            select(CanonicalFinding).where(CanonicalFinding.workspace_id == workspace_id)
        )
        all_findings = list(findings.scalars().all())

        # Extract technique IDs from finding titles/descriptions
        technique_re = re.compile(r'T\d{4}(?:\.\d{3})?', re.IGNORECASE)
        covered_techniques = set()
        technique_findings: dict[str, list] = {}

        for f in all_findings:
            text = (f.title or "") + " " + (f.description or "")
            for tech_id in technique_re.findall(text):
                tech_id = tech_id.upper()
                covered_techniques.add(tech_id)
                technique_findings.setdefault(tech_id, []).append({
                    "id": str(f.id),
                    "title": f.title,
                    "severity": f.severity,
                })

        # Build coverage map
        coverage = {}
        for tech_id, tech_info in ATTACK_TECHNIQUES.items():
            is_covered = tech_id in covered_techniques
            coverage[tech_id] = {
                "technique_id": tech_id,
                "name": tech_info["name"],
                "tactic": tech_info["tactic"],
                "covered": is_covered,
                "finding_count": len(technique_findings.get(tech_id, [])),
                "findings": technique_findings.get(tech_id, [])[:3],
            }

        total = len(ATTACK_TECHNIQUES)
        covered = sum(1 for c in coverage.values() if c["covered"])

        return {
            "total_techniques": total,
            "covered": covered,
            "uncovered": total - covered,
            "coverage_pct": round(covered / total * 100, 1) if total > 0 else 0,
            "techniques": coverage,
        }

    async def get_tactic_heatmap(self, workspace_id: uuid.UUID) -> dict:
        """Generate a tactic-level heatmap for ATT&CK visualization."""
        coverage = await self.get_technique_coverage(workspace_id)

        heatmap = {}
        for tactic in TACTICS:
            techniques_in_tactic = [
                t for t in coverage["techniques"].values()
                if t["tactic"] == tactic
            ]
            total = len(techniques_in_tactic)
            covered = sum(1 for t in techniques_in_tactic if t["covered"])

            heatmap[tactic] = {
                "total_techniques": total,
                "covered": covered,
                "coverage_pct": round(covered / total * 100, 1) if total > 0 else 0,
                "techniques": techniques_in_tactic,
            }

        return {"tactics": heatmap}

    async def get_simulation_techniques(self, run_id: uuid.UUID) -> dict:
        """Extract ATT&CK techniques from a simulation run's agent outputs."""
        agents = await self.db.execute(
            select(SwarmAgent).where(SwarmAgent.simulation_run_id == run_id)
        )
        all_agents = list(agents.scalars().all())

        technique_re = re.compile(r'T\d{4}(?:\.\d{3})?')
        by_agent: dict[str, list[str]] = {}
        all_techniques = set()

        for agent in all_agents:
            if not agent.output:
                continue
            found = set(technique_re.findall(agent.output))
            by_agent[agent.agent_id] = sorted(found)
            all_techniques.update(found)

        # Enrich with names
        enriched = []
        for tech_id in sorted(all_techniques):
            info = ATTACK_TECHNIQUES.get(tech_id, {"name": "Unknown", "tactic": "Unknown"})
            enriched.append({
                "technique_id": tech_id,
                "name": info["name"],
                "tactic": info["tactic"],
                "agents": [aid for aid, techs in by_agent.items() if tech_id in techs],
            })

        return {
            "run_id": str(run_id),
            "total_techniques": len(all_techniques),
            "techniques": enriched,
            "by_agent": by_agent,
        }

    def list_techniques(self) -> list[dict]:
        """Return all known ATT&CK techniques."""
        return [
            {"id": k, "name": v["name"], "tactic": v["tactic"]}
            for k, v in ATTACK_TECHNIQUES.items()
        ]

    def list_tactics(self) -> list[str]:
        """Return all ATT&CK tactics."""
        return TACTICS.copy()
