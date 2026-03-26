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
GET  /api/v1/modules/ot-ics/protocol-whitelist     Protocol whitelist

# LLMjacking
GET  /api/v1/modules/llmjacking/credentials        Credential audit
GET  /api/v1/modules/llmjacking/spend              Spend anomaly detection
GET  /api/v1/modules/llmjacking/canary             Canary deployment plan
GET  /api/v1/modules/llmjacking/vpc                VPC enforcement

# Federated Identity
GET  /api/v1/modules/federated-id/golden-saml      Golden SAML assessment
GET  /api/v1/modules/federated-id/cross-cloud      Cross-cloud correlation
GET  /api/v1/modules/federated-id/oidc             OIDC validation
GET  /api/v1/modules/federated-id/token-revocation Token revocation SLA

# DSPM
GET  /api/v1/modules/dspm/classify                 Data store classification
GET  /api/v1/modules/dspm/exposure                 Exposure paths
GET  /api/v1/modules/dspm/breach-impact            Breach impact model
GET  /api/v1/modules/dspm/regulatory               Regulatory compliance

# KSPM
GET  /api/v1/modules/kspm/rbac                     RBAC audit
GET  /api/v1/modules/kspm/network                  Network policy audit
GET  /api/v1/modules/kspm/admission                Admission controller assessment
GET  /api/v1/modules/kspm/pod-pivots               Pod-to-cloud pivots

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
from app.services.modules.deepfake_module import DeepfakeModule
from app.services.modules.supply_chain_module import SupplyChainModule
from app.services.modules.ot_ics_module import OTICSModule
from app.services.modules.llmjacking_module import LLMjackingModule
from app.services.modules.federated_id_module import FederatedIDModule
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
    svc = DeepfakeModule(db)
    return await svc.assess_risk(workspace_id)


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
    svc = DeepfakeModule(db)
    return await svc.authentication_audit(workspace_id)


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
    svc = SupplyChainModule(db)
    return await svc.dependency_audit(workspace_id)


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
    svc = SupplyChainModule(db)
    return await svc.sbom_validation(workspace_id)


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
    svc = SupplyChainModule(db)
    return await svc.signing_verification(workspace_id)


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
    svc = OTICSModule(db)
    return await svc.digital_twin_assessment(workspace_id)


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
    svc = OTICSModule(db)
    return await svc.air_gap_integrity(workspace_id)


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
    svc = OTICSModule(db)
    return await svc.nation_state_indicators(workspace_id)


@router.get(
    "/ot-ics/protocol-whitelist",
    summary="Protocol whitelist",
    description="Validate OT/ICS protocol whitelist — ensure only approved industrial protocols (Modbus, DNP3, OPC-UA) are in use.",
)
async def ot_ics_protocol_whitelist(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = OTICSModule(db)
    return await svc.protocol_whitelist(workspace_id)


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
    svc = LLMjackingModule(db)
    return await svc.credential_audit(workspace_id)


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
    svc = LLMjackingModule(db)
    return await svc.spend_anomaly_detection(workspace_id)


@router.get(
    "/llmjacking/canary",
    summary="Canary deployment plan",
    description="Generate a canary deployment plan for LLM API keys — honeytokens, tripwire credentials, and alerting rules.",
)
async def llmjacking_canary(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = LLMjackingModule(db)
    return await svc.canary_deployment_plan(workspace_id)


@router.get(
    "/llmjacking/vpc",
    summary="VPC enforcement",
    description="Assess VPC endpoint enforcement for LLM API traffic — ensure AI service calls stay within private network boundaries.",
)
async def llmjacking_vpc(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = LLMjackingModule(db)
    return await svc.vpc_enforcement(workspace_id)


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
    svc = FederatedIDModule(db)
    return await svc.golden_saml_assessment(workspace_id)


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
    svc = FederatedIDModule(db)
    return await svc.cross_cloud_correlation(workspace_id)


@router.get(
    "/federated-id/oidc",
    summary="OIDC validation",
    description="Validate OpenID Connect configurations — issuer trust, audience restrictions, token lifetime policies, and JWKS rotation.",
)
async def federated_id_oidc(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = FederatedIDModule(db)
    return await svc.oidc_validation(workspace_id)


@router.get(
    "/federated-id/token-revocation",
    summary="Token revocation SLA",
    description="Assess token revocation SLA compliance — measure revocation propagation latency across federated identity providers.",
)
async def federated_id_token_revocation(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = FederatedIDModule(db)
    return await svc.token_revocation_sla(workspace_id)


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


@router.get(
    "/dspm/regulatory",
    summary="Regulatory compliance",
    description="Assess regulatory compliance posture for data stores — GDPR, HIPAA, PCI-DSS, and SOX mapping with gap analysis.",
)
async def dspm_regulatory(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = DSPMModule(db)
    return await svc.regulatory_compliance(workspace_id)


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


@router.get(
    "/kspm/pod-pivots",
    summary="Pod-to-cloud pivots",
    description="Detect pod-to-cloud pivot paths — identify pods with cloud credentials, IMDS access, and lateral movement vectors.",
)
async def kspm_pod_pivots(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = KSPMModule(db)
    return await svc.pod_cloud_pivots(workspace_id)


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
