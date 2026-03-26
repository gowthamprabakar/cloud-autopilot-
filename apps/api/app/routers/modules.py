"""
CSPM + CWPP + Gap-Domain Simulation Module router (Sprint 33-34).

GET  /api/v1/modules/cspm/posture                 CSPM posture evaluation
GET  /api/v1/modules/cspm/remediation/{finding_id} Generate IaC fix
GET  /api/v1/modules/cwpp/workloads                Workload assessment
GET  /api/v1/modules/cwpp/sbom                     SBOM analysis
GET  /api/v1/modules/cwpp/runtime                  Runtime security assessment

# Quantum
GET  /api/v1/modules/quantum/crypto-bom            Cryptographic BOM
GET  /api/v1/modules/quantum/harvest-signals        Harvest signal detection
GET  /api/v1/modules/quantum/pqc-readiness          PQC migration readiness

# Deepfake
GET  /api/v1/modules/deepfake/risk                  Deepfake identity fraud risk
GET  /api/v1/modules/deepfake/auth-audit            Authentication method audit

# Supply Chain
GET  /api/v1/modules/supply-chain/dependencies      Dependency audit
GET  /api/v1/modules/supply-chain/sbom              SBOM validation
GET  /api/v1/modules/supply-chain/signing           Signing verification

# OT/ICS
GET  /api/v1/modules/ot-ics/digital-twin           Digital twin assessment
GET  /api/v1/modules/ot-ics/air-gap                Air gap integrity
GET  /api/v1/modules/ot-ics/nation-state           Nation-state indicators

# LLMjacking
GET  /api/v1/modules/llmjacking/credentials        Credential audit
GET  /api/v1/modules/llmjacking/spend              Spend anomaly detection

# Federated Identity
GET  /api/v1/modules/federated-id/golden-saml      Golden SAML assessment
GET  /api/v1/modules/federated-id/cross-cloud      Cross-cloud correlation

# DSPM
GET  /api/v1/modules/dspm/classify                 Data store classification
GET  /api/v1/modules/dspm/exposure                 Exposure paths
GET  /api/v1/modules/dspm/breach-impact            Breach impact model

# KSPM
GET  /api/v1/modules/kspm/rbac                     RBAC audit
GET  /api/v1/modules/kspm/network                  Network policy audit
GET  /api/v1/modules/kspm/admission                Admission controller assessment

# ASM
GET  /api/v1/modules/asm/exposure                  External exposure
GET  /api/v1/modules/asm/shadow                    Shadow assets
GET  /api/v1/modules/asm/priorities                Prioritized exposures
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import ForbiddenError, NotFoundError
from app.services.modules.cspm_module import CSPMModule
from app.services.modules.cwpp_module import CWPPModule
from app.services.modules.quantum_module import QuantumModule
from app.services.modules.dspm_module import DSPMModule
from app.services.modules.kspm_module import KSPMModule
from app.services.modules.asm_module import ASMModule

router = APIRouter(prefix="/modules", tags=["simulation-modules"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    wid = current_user.workspace_id
    return uuid.UUID(str(wid)) if not isinstance(wid, uuid.UUID) else wid


# ── CSPM Endpoints ──────────────────────────────────────────────────────────


@router.get(
    "/cspm/posture",
    summary="CSPM posture evaluation",
    description=(
        "Run Cloud Security Posture Management evaluation across all findings. "
        "Returns rule pass/fail by category, compliance framework scores, "
        "and an overall posture score."
    ),
)
async def cspm_posture(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = CSPMModule(db)
    return await svc.evaluate_posture(workspace_id)


@router.get(
    "/cspm/remediation/{finding_id}",
    summary="Generate IaC remediation",
    description=(
        "Generate Terraform remediation code for a specific finding. "
        "Produces auto-generated IaC blocks for common misconfiguration types."
    ),
)
async def cspm_remediation(
    finding_id: str,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = CSPMModule(db)
    result = await svc.generate_remediation(workspace_id, finding_id)
    if "error" in result:
        raise NotFoundError(result["error"])
    return result


# ── CWPP Endpoints ──────────────────────────────────────────────────────────


@router.get(
    "/cwpp/workloads",
    summary="Workload security assessment",
    description=(
        "Assess workload security posture across VM, container, and serverless. "
        "Includes CVE correlation, malware detection, and severity breakdown."
    ),
)
async def cwpp_workloads(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = CWPPModule(db)
    return await svc.assess_workloads(workspace_id)


@router.get(
    "/cwpp/sbom",
    summary="SBOM analysis",
    description=(
        "Analyze software bill of materials across workloads. "
        "Aggregates CVE data, maps to workload types, and identifies "
        "critical cross-workload dependencies."
    ),
)
async def cwpp_sbom(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = CWPPModule(db)
    return await svc.sbom_analysis(workspace_id)


@router.get(
    "/cwpp/runtime",
    summary="Runtime security assessment",
    description=(
        "Assess runtime security posture for containers and serverless workloads. "
        "Checks image security, syscall policies, secrets management, and network segmentation."
    ),
)
async def cwpp_runtime(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = CWPPModule(db)
    return await svc.runtime_assessment(workspace_id)


# ── Quantum Endpoints ──────────────────────────────────────────────────────


@router.get(
    "/quantum/crypto-bom",
    summary="Cryptographic BOM",
    description="Build a Cryptographic Bill of Materials — inventory all cryptographic algorithms in use and map quantum-vulnerable ciphers.",
)
async def quantum_crypto_bom(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = QuantumModule(db)
    return await svc.crypto_bom(workspace_id)


@router.get(
    "/quantum/harvest-signals",
    summary="Harvest signal detection",
    description="Detect Harvest-Now-Decrypt-Later (HNDL) interception signals across network findings and data flows.",
)
async def quantum_harvest_signals(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = QuantumModule(db)
    return await svc.harvest_signals(workspace_id)


@router.get(
    "/quantum/pqc-readiness",
    summary="PQC migration readiness",
    description="Assess readiness for Post-Quantum Cryptography migration — CRYSTALS-Kyber, Dilithium, and SPHINCS+ adoption.",
)
async def quantum_pqc_readiness(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = QuantumModule(db)
    return await svc.pqc_readiness(workspace_id)


# ── Deepfake Endpoints ─────────────────────────────────────────────────────


@router.get(
    "/deepfake/risk",
    summary="Deepfake identity fraud risk",
    description="Assess deepfake identity fraud risk by analysing authentication methods, biometric reliance, and social engineering exposure.",
)
async def deepfake_risk(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    # Stub — service module will be added in a future sprint
    return {
        "workspace_id": str(workspace_id),
        "module": "deepfake",
        "method": "risk",
        "status": "stub",
        "risk_score": 0,
        "biometric_auth_count": 0,
        "video_kyc_count": 0,
        "social_engineering_vectors": [],
    }


@router.get(
    "/deepfake/auth-audit",
    summary="Authentication method audit",
    description="Audit authentication methods for deepfake susceptibility — biometric-only, video KYC, and voice-based auth.",
)
async def deepfake_auth_audit(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    return {
        "workspace_id": str(workspace_id),
        "module": "deepfake",
        "method": "auth_audit",
        "status": "stub",
        "auth_methods": [],
        "vulnerable_methods": [],
        "recommendations": [],
    }


# ── Supply Chain Endpoints ─────────────────────────────────────────────────


@router.get(
    "/supply-chain/dependencies",
    summary="Dependency audit",
    description="Audit software dependencies for known vulnerabilities, EOL libraries, and typosquatting indicators.",
)
async def supply_chain_dependencies(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    return {
        "workspace_id": str(workspace_id),
        "module": "supply_chain",
        "method": "dependencies",
        "status": "stub",
        "total_dependencies": 0,
        "vulnerable": 0,
        "eol_libraries": [],
        "typosquat_suspects": [],
    }


@router.get(
    "/supply-chain/sbom",
    summary="SBOM validation",
    description="Validate Software Bill of Materials against known-good baselines and detect drift.",
)
async def supply_chain_sbom(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    return {
        "workspace_id": str(workspace_id),
        "module": "supply_chain",
        "method": "sbom",
        "status": "stub",
        "sbom_entries": 0,
        "drift_detected": False,
        "unsigned_packages": [],
    }


@router.get(
    "/supply-chain/signing",
    summary="Signing verification",
    description="Verify code-signing, container image signing (cosign/Sigstore), and provenance attestations.",
)
async def supply_chain_signing(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    return {
        "workspace_id": str(workspace_id),
        "module": "supply_chain",
        "method": "signing",
        "status": "stub",
        "signed_artifacts": 0,
        "unsigned_artifacts": 0,
        "provenance_verified": 0,
    }


# ── OT/ICS Endpoints ──────────────────────────────────────────────────────


@router.get(
    "/ot-ics/digital-twin",
    summary="Digital twin assessment",
    description="Assess OT/ICS digital twin security posture — network segmentation, protocol exposure, and firmware integrity.",
)
async def ot_ics_digital_twin(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    return {
        "workspace_id": str(workspace_id),
        "module": "ot_ics",
        "method": "digital_twin",
        "status": "stub",
        "twin_assets": 0,
        "segmentation_score": 0,
        "exposed_protocols": [],
    }


@router.get(
    "/ot-ics/air-gap",
    summary="Air gap integrity",
    description="Verify air-gap integrity between IT and OT networks — detect bridging devices, rogue connections, and data leaks.",
)
async def ot_ics_air_gap(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    return {
        "workspace_id": str(workspace_id),
        "module": "ot_ics",
        "method": "air_gap",
        "status": "stub",
        "air_gap_intact": True,
        "bridging_devices": [],
        "rogue_connections": [],
    }


@router.get(
    "/ot-ics/nation-state",
    summary="Nation-state indicators",
    description="Detect nation-state threat indicators targeting OT/ICS — TTPs from PIPEDREAM, TRITON, Industroyer families.",
)
async def ot_ics_nation_state(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    return {
        "workspace_id": str(workspace_id),
        "module": "ot_ics",
        "method": "nation_state",
        "status": "stub",
        "indicators_found": 0,
        "threat_families": [],
        "iocs": [],
    }


# ── LLMjacking Endpoints ──────────────────────────────────────────────────


@router.get(
    "/llmjacking/credentials",
    summary="Credential audit",
    description="Audit AI/ML API credentials — detect exposed keys, over-permissioned tokens, and unrotated secrets for LLM services.",
)
async def llmjacking_credentials(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    return {
        "workspace_id": str(workspace_id),
        "module": "llmjacking",
        "method": "credentials",
        "status": "stub",
        "exposed_keys": 0,
        "over_permissioned": 0,
        "unrotated_secrets": 0,
        "services_audited": [],
    }


@router.get(
    "/llmjacking/spend",
    summary="Spend anomaly detection",
    description="Detect anomalous LLM API spend patterns that may indicate credential hijacking or compute abuse.",
)
async def llmjacking_spend(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    return {
        "workspace_id": str(workspace_id),
        "module": "llmjacking",
        "method": "spend",
        "status": "stub",
        "anomalies_detected": 0,
        "baseline_daily_spend": 0.0,
        "current_daily_spend": 0.0,
        "spike_ratio": 0.0,
    }


# ── Federated Identity Endpoints ──────────────────────────────────────────


@router.get(
    "/federated-id/golden-saml",
    summary="Golden SAML assessment",
    description="Assess Golden SAML / Golden Ticket risk — ADFS signing cert exposure, token forging indicators, SAML assertion anomalies.",
)
async def federated_id_golden_saml(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    return {
        "workspace_id": str(workspace_id),
        "module": "federated_id",
        "method": "golden_saml",
        "status": "stub",
        "risk_score": 0,
        "signing_cert_exposed": False,
        "saml_anomalies": [],
        "recommendations": [],
    }


@router.get(
    "/federated-id/cross-cloud",
    summary="Cross-cloud correlation",
    description="Correlate federated identity trust chains across AWS, Azure, and GCP — detect orphaned trusts and excessive cross-cloud privileges.",
)
async def federated_id_cross_cloud(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    return {
        "workspace_id": str(workspace_id),
        "module": "federated_id",
        "method": "cross_cloud",
        "status": "stub",
        "trust_chains": [],
        "orphaned_trusts": 0,
        "excessive_privileges": 0,
    }


# ── DSPM Endpoints ─────────────────────────────────────────────────────────


@router.get(
    "/dspm/classify",
    summary="Data store classification",
    description="Classify data stores by sensitivity level — PII, PHI, PCI, and regulatory mapping.",
)
async def dspm_classify(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = DSPMModule(db)
    return await svc.classify_data_stores(workspace_id)


@router.get(
    "/dspm/exposure",
    summary="Exposure paths",
    description="Analyse data exposure paths — identify how sensitive data stores can be reached from external-facing assets.",
)
async def dspm_exposure(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = DSPMModule(db)
    return await svc.exposure_paths(workspace_id)


@router.get(
    "/dspm/breach-impact",
    summary="Breach impact model",
    description="Model breach impact per data store — estimated record count, regulatory exposure, and cost projection.",
)
async def dspm_breach_impact(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = DSPMModule(db)
    return await svc.breach_impact(workspace_id)


# ── KSPM Endpoints ─────────────────────────────────────────────────────────


@router.get(
    "/kspm/rbac",
    summary="RBAC audit",
    description="Audit Kubernetes RBAC — detect wildcard ClusterRoles, privilege escalation paths, and system:masters bindings.",
)
async def kspm_rbac(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = KSPMModule(db)
    return await svc.rbac_audit(workspace_id)


@router.get(
    "/kspm/network",
    summary="Network policy audit",
    description="Audit Kubernetes NetworkPolicies — detect unprotected namespaces, overly permissive ingress/egress, and missing default-deny.",
)
async def kspm_network(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = KSPMModule(db)
    return await svc.network_policy_audit(workspace_id)


@router.get(
    "/kspm/admission",
    summary="Admission controller assessment",
    description="Assess admission controller coverage — OPA/Gatekeeper, Kyverno, and Pod Security Standards enforcement.",
)
async def kspm_admission(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = KSPMModule(db)
    return await svc.admission_controller_assessment(workspace_id)


# ── ASM Endpoints ──────────────────────────────────────────────────────────


@router.get(
    "/asm/exposure",
    summary="External exposure",
    description="Enumerate internet-facing assets and assess external exposure risk.",
)
async def asm_exposure(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = ASMModule(db)
    return await svc.enumerate_exposure(workspace_id)


@router.get(
    "/asm/shadow",
    summary="Shadow assets",
    description="Discover shadow and unmanaged assets — orphaned resources, untagged infrastructure, and unknown endpoints.",
)
async def asm_shadow(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = ASMModule(db)
    return await svc.shadow_assets(workspace_id)


@router.get(
    "/asm/priorities",
    summary="Prioritized exposures",
    description="Prioritize external exposures by risk score — combines internet reachability, vulnerability severity, and blast radius.",
)
async def asm_priorities(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = ASMModule(db)
    return await svc.prioritize_exposures(workspace_id)
