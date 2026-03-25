"""
SimulationService — OmniSec swarm simulation orchestration engine (Sprint 29).

Orchestrates a full threat simulation run. For Sprint 29, agents execute
SEQUENTIALLY with mock outputs. Celery parallel execution is planned for
Sprint 30 once the claude_client is wired up.
"""

from __future__ import annotations

import asyncio
import json
import random
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comm_message import CommMessage
from app.models.simulation_run import SimulationRun
from app.models.swarm_agent import SwarmAgent
from app.models.validation_gate import ValidationGate

logger = structlog.get_logger(__name__)

# ── Agent roster ──────────────────────────────────────────────────────────────

AGENT_ROSTER: list[dict[str, Any]] = [
    {"agent_id": "ORCH-01", "name": "SwarmMaster", "role": "orchestrator", "autonomy": 5, "spawn_authority": True},
    {"agent_id": "SCOUT-01", "name": "PathFinder", "role": "recon", "autonomy": 4, "spawn_authority": False},
    {"agent_id": "EXPLOIT-01", "name": "ExploitSynth", "role": "exploit", "autonomy": 4, "spawn_authority": True},
    {"agent_id": "DEFEND-01", "name": "ShieldWeaver", "role": "defend", "autonomy": 4, "spawn_authority": False},
    {"agent_id": "VALID-01", "name": "GateKeeper", "role": "validate", "autonomy": 5, "spawn_authority": False},
    {"agent_id": "REPORT-01", "name": "ReportAgent", "role": "report", "autonomy": 3, "spawn_authority": False},
]

# ── 12 Validation gates ──────────────────────────────────────────────────────

GATE_DEFINITIONS: list[dict[str, Any]] = [
    {"number": 1, "name": "Cryptographic Hardening", "double_weight": True},
    {"number": 2, "name": "Attack Surface Reduction", "double_weight": True},
    {"number": 3, "name": "IaC Policy Correctness", "double_weight": False},
    {"number": 4, "name": "Detection Completeness", "double_weight": True},
    {"number": 5, "name": "Automated Response Speed", "double_weight": False},
    {"number": 6, "name": "Blast Radius Containment", "double_weight": False},
    {"number": 7, "name": "Lateral Movement Prevention", "double_weight": False},
    {"number": 8, "name": "Credential Lifecycle", "double_weight": False},
    {"number": 9, "name": "Cross-Account Coverage", "double_weight": False},
    {"number": 10, "name": "Continuous Monitoring", "double_weight": False},
    {"number": 11, "name": "IR Playbook Completeness", "double_weight": False},
    {"number": 12, "name": "Red-Team Pass Rate", "double_weight": True},
]

# ── 17 Threat domains ────────────────────────────────────────────────────────

THREAT_DOMAINS: dict[str, str] = {
    "cspm": "Cloud Security Posture Management",
    "cwpp": "Cloud Workload Protection",
    "ciem": "Cloud Infrastructure Entitlement Management",
    "dspm": "Data Security Posture Management",
    "kspm": "Kubernetes Security Posture Management",
    "cdr": "Cloud Detection & Response",
    "iac": "IaC & Code Security",
    "uvm": "Vulnerability Management",
    "ai_spm": "AI Security Posture Management",
    "asm": "Attack Surface Management",
    "quantum": "Quantum Cryptography Harvest",
    "deepfake": "AI Deepfake Identity Fraud",
    "supply_chain": "Supply Chain Firmware Attack",
    "agentic_ai": "Autonomous Malicious AI Agents",
    "ot_ics": "OT/ICS Critical Infrastructure",
    "llmjacking": "LLMjacking Cloud AI Credential Abuse",
    "federated_id": "Federated Identity Cross-Cloud Abuse",
}


# ── Mock output generators (per-agent, per-domain) ───────────────────────────

def _mock_orch_output(domain: str, domain_label: str) -> str:
    return json.dumps({
        "agent": "ORCH-01",
        "phase": "threat_decomposition",
        "domain": domain,
        "domain_label": domain_label,
        "decomposition": {
            "primary_threat": f"{domain_label} — multi-vector attack surface",
            "sub_vectors": [
                f"{domain_label} misconfiguration exploitation",
                "Privilege escalation via lateral movement",
                "Data exfiltration through compromised control plane",
                "Persistence via backdoor IAM policies",
            ],
            "estimated_blast_radius": "3 accounts, 12 services, 47 resources",
            "priority": "critical",
        },
        "agent_assignments": {
            "SCOUT-01": "Enumerate attack surface and recon vectors",
            "EXPLOIT-01": "Synthesize kill chains with MITRE mapping",
            "DEFEND-01": "Generate IaC remediation for each vector",
            "VALID-01": "Run 12-gate validation on all solutions",
            "REPORT-01": "Compile executive summary",
        },
    }, indent=2)


def _mock_scout_output(domain: str, domain_label: str) -> str:
    return json.dumps({
        "agent": "SCOUT-01",
        "phase": "reconnaissance",
        "domain": domain,
        "vectors_found": [
            {
                "id": "VEC-001",
                "name": f"Exposed {domain_label} control plane API",
                "severity": "critical",
                "cvss": 9.1,
                "affected_resources": ["arn:aws:ec2:us-east-1:123456789012:instance/i-0abc123"],
            },
            {
                "id": "VEC-002",
                "name": "Over-permissive IAM role with cross-account trust",
                "severity": "high",
                "cvss": 8.4,
                "affected_resources": ["arn:aws:iam::123456789012:role/LegacyAdmin"],
            },
            {
                "id": "VEC-003",
                "name": "Unencrypted data-at-rest in S3 bucket",
                "severity": "high",
                "cvss": 7.8,
                "affected_resources": ["arn:aws:s3:::prod-data-lake-raw"],
            },
            {
                "id": "VEC-004",
                "name": f"Missing detection rules for {domain} anomalies",
                "severity": "medium",
                "cvss": 6.5,
                "affected_resources": ["arn:aws:guardduty:us-east-1:123456789012:detector/abc"],
            },
        ],
        "total_attack_surface_score": 87.3,
    }, indent=2)


def _mock_exploit_output(domain: str, domain_label: str) -> str:
    return json.dumps({
        "agent": "EXPLOIT-01",
        "phase": "kill_chain_synthesis",
        "domain": domain,
        "kill_chains": [
            {
                "id": "KC-001",
                "name": f"{domain_label} Full Compromise Chain",
                "mitre_techniques": [
                    {"id": "T1190", "name": "Exploit Public-Facing Application", "tactic": "Initial Access"},
                    {"id": "T1078", "name": "Valid Accounts", "tactic": "Persistence"},
                    {"id": "T1548", "name": "Abuse Elevation Control Mechanism", "tactic": "Privilege Escalation"},
                    {"id": "T1071", "name": "Application Layer Protocol", "tactic": "Command and Control"},
                    {"id": "T1537", "name": "Transfer Data to Cloud Account", "tactic": "Exfiltration"},
                ],
                "estimated_time_to_compromise": "4.2 hours",
                "blast_radius": "critical",
            },
            {
                "id": "KC-002",
                "name": "Lateral Movement via Credential Harvesting",
                "mitre_techniques": [
                    {"id": "T1552", "name": "Unsecured Credentials", "tactic": "Credential Access"},
                    {"id": "T1021", "name": "Remote Services", "tactic": "Lateral Movement"},
                    {"id": "T1486", "name": "Data Encrypted for Impact", "tactic": "Impact"},
                ],
                "estimated_time_to_compromise": "2.8 hours",
                "blast_radius": "high",
            },
        ],
        "total_kill_chains": 2,
    }, indent=2)


def _mock_defend_output(domain: str, domain_label: str) -> str:
    return json.dumps({
        "agent": "DEFEND-01",
        "phase": "iac_remediation",
        "domain": domain,
        "remediations": [
            {
                "vector_id": "VEC-001",
                "title": f"Restrict {domain_label} control plane access",
                "iac_type": "terraform",
                "snippet": (
                    'resource "aws_security_group_rule" "restrict_control_plane" {\n'
                    '  type              = "ingress"\n'
                    '  from_port         = 443\n'
                    '  to_port           = 443\n'
                    '  protocol          = "tcp"\n'
                    '  cidr_blocks       = [var.allowed_cidr]\n'
                    '  security_group_id = aws_security_group.control_plane.id\n'
                    "}"
                ),
                "priority": "P0",
            },
            {
                "vector_id": "VEC-002",
                "title": "Scope IAM role with least-privilege boundary",
                "iac_type": "terraform",
                "snippet": (
                    'resource "aws_iam_role" "scoped_role" {\n'
                    '  name               = "scoped-access-role"\n'
                    '  assume_role_policy = data.aws_iam_policy_document.trust.json\n'
                    '  permissions_boundary = aws_iam_policy.boundary.arn\n'
                    "}\n\n"
                    'resource "aws_iam_policy" "boundary" {\n'
                    '  name   = "least-privilege-boundary"\n'
                    '  policy = data.aws_iam_policy_document.boundary.json\n'
                    "}"
                ),
                "priority": "P0",
            },
            {
                "vector_id": "VEC-003",
                "title": "Enable S3 default encryption with KMS CMK",
                "iac_type": "terraform",
                "snippet": (
                    'resource "aws_s3_bucket_server_side_encryption_configuration" "encrypt" {\n'
                    '  bucket = aws_s3_bucket.prod_data_lake.id\n'
                    "  rule {\n"
                    "    apply_server_side_encryption_by_default {\n"
                    '      sse_algorithm     = "aws:kms"\n'
                    "      kms_master_key_id = aws_kms_key.data_lake.arn\n"
                    "    }\n"
                    "    bucket_key_enabled = true\n"
                    "  }\n"
                    "}"
                ),
                "priority": "P1",
            },
        ],
        "total_remediations": 3,
    }, indent=2)


def _mock_validate_output(gate_results: list[dict]) -> str:
    return json.dumps({
        "agent": "VALID-01",
        "phase": "12_gate_validation",
        "gate_results": gate_results,
        "summary": {
            "total_gates": len(gate_results),
            "passed": sum(1 for g in gate_results if g["state"] == "pass"),
            "failed": sum(1 for g in gate_results if g["state"] == "fail"),
            "partial": sum(1 for g in gate_results if g["state"] == "partial"),
        },
    }, indent=2)


def _mock_report_output(
    domain: str,
    domain_label: str,
    confidence: float,
    gates_passed: int,
    gates_total: int,
) -> str:
    return json.dumps({
        "agent": "REPORT-01",
        "phase": "executive_summary",
        "domain": domain,
        "domain_label": domain_label,
        "executive_summary": (
            f"OmniSec swarm simulation completed for {domain_label}. "
            f"The 6-agent swarm identified 4 attack vectors and synthesized "
            f"2 kill chains mapped to MITRE ATT&CK. ShieldWeaver generated "
            f"3 IaC remediation snippets (Terraform). GateKeeper validated "
            f"all solutions across {gates_total} quality gates — "
            f"{gates_passed}/{gates_total} passed. "
            f"Overall confidence score: {confidence:.1f}/100."
        ),
        "confidence_score": confidence,
        "gates_passed": gates_passed,
        "gates_total": gates_total,
        "recommendations": [
            "Apply P0 Terraform remediations within 24 hours",
            "Review IAM trust policies across all linked accounts",
            "Enable CloudTrail data events for S3 buckets",
            f"Schedule follow-up {domain} re-scan after remediation",
        ],
    }, indent=2)


# ── Service ──────────────────────────────────────────────────────────────────


class SimulationService:
    """Orchestrates OmniSec swarm simulation runs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── CRUD ──────────────────────────────────────────────────────────────

    async def create_run(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        domain: str,
        sim_config: dict | None = None,
    ) -> SimulationRun:
        """Create a new simulation run record."""
        run = SimulationRun(
            workspace_id=workspace_id,
            user_id=user_id,
            domain=domain,
            status="pending",
            agent_count=len(AGENT_ROSTER),
            sim_config=json.dumps(sim_config) if sim_config else None,
        )
        self.db.add(run)
        await self.db.flush()
        await self.db.refresh(run)
        return run

    async def get_run(self, run_id: uuid.UUID) -> SimulationRun | None:
        """Get a simulation run by ID."""
        result = await self.db.execute(
            select(SimulationRun).where(SimulationRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def list_runs(
        self, workspace_id: uuid.UUID, limit: int = 20
    ) -> list[SimulationRun]:
        """List simulation runs for a workspace, newest first."""
        result = await self.db.execute(
            select(SimulationRun)
            .where(SimulationRun.workspace_id == workspace_id)
            .order_by(SimulationRun.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_agents(self, run_id: uuid.UUID) -> list[SwarmAgent]:
        """Get all agents for a simulation run."""
        result = await self.db.execute(
            select(SwarmAgent)
            .where(SwarmAgent.simulation_run_id == run_id)
            .order_by(SwarmAgent.agent_id)
        )
        return list(result.scalars().all())

    async def get_messages(self, run_id: uuid.UUID) -> list[CommMessage]:
        """Get all comm bus messages for a run, ordered by sequence."""
        result = await self.db.execute(
            select(CommMessage)
            .where(CommMessage.simulation_run_id == run_id)
            .order_by(CommMessage.sequence_number)
        )
        return list(result.scalars().all())

    async def get_gates(self, run_id: uuid.UUID) -> list[ValidationGate]:
        """Get all validation gates for a run."""
        result = await self.db.execute(
            select(ValidationGate)
            .where(ValidationGate.simulation_run_id == run_id)
            .order_by(ValidationGate.gate_number)
        )
        return list(result.scalars().all())

    # ── Execution ────────────────────────────────────────────────────────

    async def execute_simulation(self, run_id: uuid.UUID) -> SimulationRun:
        """Execute the full simulation pipeline for a run.

        For Sprint 29, this is a MOCK implementation that:
        1. Creates 6 base agents (ORCH-01, SCOUT-01, EXPLOIT-01, DEFEND-01, VALID-01, REPORT-01)
        2. Runs them sequentially (each agent gets 2-second simulated delay)
        3. Each agent generates mock output based on the threat domain
        4. Creates comm bus messages between agents
        5. Creates 12 validation gates with mock scores
        6. Computes overall confidence score
        7. Updates the SimulationRun with results

        Real Claude API calls come in Sprint 30 when we have the claude_client ready.
        """
        run = await self.get_run(run_id)
        if run is None:
            raise ValueError(f"SimulationRun {run_id} not found")

        domain = run.domain
        domain_label = THREAT_DOMAINS.get(domain, domain)
        started_at = datetime.now(UTC)

        # Mark as running
        run.status = "running"
        run.started_at = started_at
        await self.db.flush()

        try:
            agents: list[SwarmAgent] = []
            seq = 0  # comm bus message sequence counter

            # ── Step 1: Create agents ────────────────────────────────────
            for roster in AGENT_ROSTER:
                agent = SwarmAgent(
                    simulation_run_id=run_id,
                    agent_id=roster["agent_id"],
                    name=roster["name"],
                    role=roster["role"],
                    status="idle",
                    autonomy_level=roster["autonomy"],
                    spawn_authority=roster["spawn_authority"],
                )
                self.db.add(agent)
                agents.append(agent)
            await self.db.flush()

            # ── Step 2: Execute agents sequentially with mock delay ──────
            gate_results: list[dict] = []  # built by VALID-01

            for agent in agents:
                agent.status = "running"
                agent.started_at = datetime.now(UTC)
                await self.db.flush()

                # Simulated 2-second processing delay
                await asyncio.sleep(2)

                # Generate mock output based on role
                if agent.role == "orchestrator":
                    agent.output = _mock_orch_output(domain, domain_label)
                    # Comm: ORCH -> ALL
                    seq += 1
                    self.db.add(CommMessage(
                        simulation_run_id=run_id,
                        from_agent_id="ORCH-01",
                        to_agent_id="ALL",
                        message_type="info",
                        body=f"Threat decomposition complete for {domain_label}. Dispatching agents.",
                        sequence_number=seq,
                    ))

                elif agent.role == "recon":
                    agent.output = _mock_scout_output(domain, domain_label)
                    seq += 1
                    self.db.add(CommMessage(
                        simulation_run_id=run_id,
                        from_agent_id="SCOUT-01",
                        to_agent_id="EXPLOIT-01",
                        message_type="info",
                        body="Recon complete. 4 attack vectors identified. Passing to ExploitSynth.",
                        sequence_number=seq,
                    ))
                    seq += 1
                    self.db.add(CommMessage(
                        simulation_run_id=run_id,
                        from_agent_id="SCOUT-01",
                        to_agent_id="ORCH-01",
                        message_type="info",
                        body="Attack surface score: 87.3/100. Recommend immediate action.",
                        sequence_number=seq,
                    ))

                elif agent.role == "exploit":
                    agent.output = _mock_exploit_output(domain, domain_label)
                    seq += 1
                    self.db.add(CommMessage(
                        simulation_run_id=run_id,
                        from_agent_id="EXPLOIT-01",
                        to_agent_id="DEFEND-01",
                        message_type="solution",
                        body="2 kill chains synthesized with MITRE ATT&CK mapping. Handing to ShieldWeaver.",
                        sequence_number=seq,
                    ))

                elif agent.role == "defend":
                    agent.output = _mock_defend_output(domain, domain_label)
                    seq += 1
                    self.db.add(CommMessage(
                        simulation_run_id=run_id,
                        from_agent_id="DEFEND-01",
                        to_agent_id="VALID-01",
                        message_type="solution",
                        body="3 IaC remediations generated (Terraform). Ready for validation.",
                        sequence_number=seq,
                    ))

                elif agent.role == "validate":
                    # Generate 12 gate scores
                    gate_results = self._generate_gate_results()
                    agent.output = _mock_validate_output(gate_results)
                    seq += 1
                    passed = sum(1 for g in gate_results if g["state"] == "pass")
                    self.db.add(CommMessage(
                        simulation_run_id=run_id,
                        from_agent_id="VALID-01",
                        to_agent_id="REPORT-01",
                        message_type="info",
                        body=f"12-gate validation complete. {passed}/12 gates passed.",
                        sequence_number=seq,
                    ))

                elif agent.role == "report":
                    gates_passed = sum(1 for g in gate_results if g["state"] == "pass")
                    confidence = self._compute_confidence(gate_results)
                    agent.output = _mock_report_output(
                        domain, domain_label, confidence, gates_passed, 12
                    )
                    seq += 1
                    self.db.add(CommMessage(
                        simulation_run_id=run_id,
                        from_agent_id="REPORT-01",
                        to_agent_id="ORCH-01",
                        message_type="solution",
                        body=f"Executive report compiled. Confidence: {confidence:.1f}/100.",
                        sequence_number=seq,
                    ))

                # Mark agent done
                agent.status = "done"
                agent.progress = 100
                agent.completed_at = datetime.now(UTC)
                # Mock token usage
                agent.input_tokens = random.randint(800, 2500)
                agent.output_tokens = random.randint(400, 1800)
                agent.cost_usd = round(
                    (agent.input_tokens * 0.003 + agent.output_tokens * 0.015) / 1000, 4
                )
                await self.db.flush()

            # ── Step 3: Persist validation gates ─────────────────────────
            for gdef in GATE_DEFINITIONS:
                gr = next(
                    (g for g in gate_results if g["gate_number"] == gdef["number"]),
                    None,
                )
                gate = ValidationGate(
                    simulation_run_id=run_id,
                    gate_number=gdef["number"],
                    name=gdef["name"],
                    is_double_weight=gdef["double_weight"],
                    state=gr["state"] if gr else "pending",
                    score=gr["score"] if gr else 0.0,
                    evidence=gr.get("evidence", "") if gr else "",
                    coverage="both",
                )
                self.db.add(gate)
            await self.db.flush()

            # ── Step 4: Finalize run ─────────────────────────────────────
            completed_at = datetime.now(UTC)
            gates_passed = sum(1 for g in gate_results if g["state"] == "pass")
            confidence = self._compute_confidence(gate_results)
            total_tokens = sum(a.input_tokens + a.output_tokens for a in agents)
            total_cost = sum(a.cost_usd for a in agents)

            run.status = "completed"
            run.completed_at = completed_at
            run.duration_seconds = (completed_at - started_at).total_seconds()
            run.gates_passed = gates_passed
            run.gates_total = 12
            run.confidence_score = round(confidence, 1)
            run.message_count = seq
            run.solution_count = sum(
                1 for a in agents if a.output is not None
            )
            run.total_tokens_used = total_tokens
            run.total_cost_usd = round(total_cost, 4)

            await self.db.commit()
            await self.db.refresh(run)

            logger.info(
                "simulation_completed",
                run_id=str(run_id),
                domain=domain,
                confidence=confidence,
                gates_passed=gates_passed,
                duration=run.duration_seconds,
            )
            return run

        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)[:500]
            run.completed_at = datetime.now(UTC)
            if run.started_at:
                run.duration_seconds = (
                    run.completed_at - run.started_at
                ).total_seconds()
            await self.db.commit()
            logger.error(
                "simulation_failed",
                run_id=str(run_id),
                error=str(exc),
            )
            raise

    # ── Deletion ─────────────────────────────────────────────────────────

    async def delete_run(self, run_id: uuid.UUID) -> bool:
        """Delete a simulation run and all associated data (cascades)."""
        run = await self.get_run(run_id)
        if run is None:
            return False
        await self.db.delete(run)
        await self.db.commit()
        return True

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _generate_gate_results() -> list[dict]:
        """Generate mock 12-gate validation results.

        Scores are randomized 60-100 with most passing (>80).
        """
        results: list[dict] = []
        for gdef in GATE_DEFINITIONS:
            # Bias towards passing: ~75% chance of score > 80
            score = random.choices(
                population=[
                    random.randint(60, 79),   # fail/partial range
                    random.randint(80, 100),  # pass range
                ],
                weights=[25, 75],
                k=1,
            )[0]

            if score >= 80:
                state = "pass"
            elif score >= 70:
                state = "partial"
            else:
                state = "fail"

            results.append({
                "gate_number": gdef["number"],
                "name": gdef["name"],
                "score": float(score),
                "state": state,
                "double_weight": gdef["double_weight"],
                "evidence": f"Gate {gdef['number']} ({gdef['name']}): "
                            f"score {score}/100 — {'PASS' if state == 'pass' else state.upper()}. "
                            f"{'Double-weighted gate.' if gdef['double_weight'] else 'Standard weight.'}",
            })
        return results

    @staticmethod
    def _compute_confidence(gate_results: list[dict]) -> float:
        """Compute weighted confidence score from gate results.

        Double-weighted gates count 2x in the average.
        """
        if not gate_results:
            return 0.0
        total_weight = 0.0
        weighted_sum = 0.0
        for g in gate_results:
            w = 2.0 if g.get("double_weight") else 1.0
            weighted_sum += g["score"] * w
            total_weight += w
        return round(weighted_sum / total_weight, 1) if total_weight else 0.0
