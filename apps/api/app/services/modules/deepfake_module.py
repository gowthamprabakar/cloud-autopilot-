"""
DeepfakeModule — AI Deepfake Identity Fraud simulation.

Sprint 34: Simulates deepfake attack scenarios:
1. CEO voice cloning for social engineering
2. Synthetic video for identity verification bypass
3. FIDO2/Passkey defense effectiveness
4. Behavioral biometric baseline assessment
"""

from __future__ import annotations
import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from app.models.canonical_finding import CanonicalFinding
from app.models.security_graph_node import SecurityGraphNode
from app.models.enums import FindingSeverity, FindingStatus

# Authentication method deepfake-resistance ratings (0-100)
AUTH_RESISTANCE = {
    "fido2_passkey": {"resistance": 95, "label": "FIDO2 / Passkey", "bypassed_by": "None known"},
    "hardware_token": {"resistance": 90, "label": "Hardware Security Key", "bypassed_by": "Physical theft only"},
    "totp_app": {"resistance": 55, "label": "TOTP Authenticator App", "bypassed_by": "Real-time phishing + voice clone"},
    "sms_otp": {"resistance": 25, "label": "SMS OTP", "bypassed_by": "SIM swap + voice clone"},
    "push_notification": {"resistance": 50, "label": "Push MFA", "bypassed_by": "MFA fatigue + voice clone"},
    "email_otp": {"resistance": 30, "label": "Email OTP", "bypassed_by": "Email compromise + deepfake"},
    "password_only": {"resistance": 5, "label": "Password Only", "bypassed_by": "Voice clone social engineering"},
    "knowledge_based": {"resistance": 10, "label": "Knowledge-Based Auth", "bypassed_by": "AI-generated answers from OSINT"},
    "voice_biometric": {"resistance": 15, "label": "Voice Biometric", "bypassed_by": "3-second voice clone"},
    "facial_recognition": {"resistance": 35, "label": "Facial Recognition (2D)", "bypassed_by": "Synthetic video in real-time"},
    "liveness_detection": {"resistance": 65, "label": "Liveness Detection (3D)", "bypassed_by": "Advanced GAN injection"},
}

# Attack scenario templates
ATTACK_SCENARIOS = [
    {
        "id": "ceo_voice_clone",
        "name": "CEO Voice Cloning",
        "description": "Attacker clones C-suite voice from public earnings calls to authorize wire transfers via phone",
        "attack_vector": "Voice synthesis + social engineering",
        "sophistication": "MEDIUM",
        "data_required": "3 seconds of public audio",
        "target": "Finance / Treasury team",
        "impact": "Unauthorized fund transfers",
        "prevalence": "HIGH",
    },
    {
        "id": "synthetic_video_kyc",
        "name": "KYC Identity Bypass",
        "description": "Synthetic video used to pass identity verification during account creation or privilege escalation",
        "attack_vector": "Real-time deepfake video injection",
        "sophistication": "HIGH",
        "data_required": "Public photos (social media, LinkedIn)",
        "target": "Identity verification systems",
        "impact": "Fraudulent account creation / privilege escalation",
        "prevalence": "MEDIUM",
    },
    {
        "id": "board_impersonation",
        "name": "Board Member Impersonation",
        "description": "Deepfake video call impersonating board member to influence strategic decisions or extract data",
        "attack_vector": "Real-time video + voice deepfake on video conferencing",
        "sophistication": "HIGH",
        "data_required": "Public video appearances, interviews",
        "target": "Senior leadership / executives",
        "impact": "Strategic manipulation, data exfiltration",
        "prevalence": "LOW",
    },
    {
        "id": "helpdesk_social_engineering",
        "name": "IT Helpdesk Social Engineering",
        "description": "Voice clone of employee to call IT helpdesk and request password reset or MFA bypass",
        "attack_vector": "Voice clone + insider knowledge (OSINT)",
        "sophistication": "LOW",
        "data_required": "Voicemail recordings, org chart",
        "target": "IT helpdesk / support staff",
        "impact": "Account takeover, lateral movement",
        "prevalence": "HIGH",
    },
    {
        "id": "vendor_impersonation",
        "name": "Vendor Invoice Fraud",
        "description": "Deepfake video/voice of known vendor contact to redirect payments to attacker-controlled accounts",
        "attack_vector": "Voice clone + email compromise (BEC hybrid)",
        "sophistication": "MEDIUM",
        "data_required": "Vendor relationship data, public appearances",
        "target": "Accounts payable / procurement",
        "impact": "Payment redirection, financial loss",
        "prevalence": "HIGH",
    },
]


class DeepfakeModule:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def assess_risk(self, workspace_id: uuid.UUID) -> dict:
        """Assess deepfake identity fraud risk across the workspace."""
        auth_audit = await self.authentication_audit(workspace_id)
        iam_analysis = await self._iam_exposure_analysis(workspace_id)

        # Compute overall deepfake risk score (0-100, higher = more risk)
        auth_weakness = 100 - auth_audit["overall_resistance"]
        exposure_factor = min(2.0, 1 + iam_analysis["internet_facing_iam_count"] * 0.15)
        finding_factor = min(1.5, 1 + iam_analysis["iam_finding_count"] * 0.05)

        risk_score = min(100, round(auth_weakness * exposure_factor * finding_factor, 1))

        # Determine which attack scenarios are most relevant
        scored_scenarios = []
        for scenario in ATTACK_SCENARIOS:
            scenario_risk = risk_score
            if scenario["sophistication"] == "LOW":
                scenario_risk = min(100, scenario_risk * 1.2)
            elif scenario["sophistication"] == "HIGH":
                scenario_risk = scenario_risk * 0.8
            scored_scenarios.append({
                **scenario,
                "risk_score": round(scenario_risk, 1),
                "likelihood": "HIGH" if scenario_risk > 70 else "MEDIUM" if scenario_risk > 40 else "LOW",
            })
        scored_scenarios.sort(key=lambda s: s["risk_score"], reverse=True)

        # Generate recommendations based on weaknesses
        recommendations = await self._generate_recommendations(auth_audit, iam_analysis)

        return {
            "risk_score": risk_score,
            "risk_level": "CRITICAL" if risk_score > 80 else "HIGH" if risk_score > 60 else "MEDIUM" if risk_score > 40 else "LOW",
            "attack_scenarios": scored_scenarios,
            "auth_summary": {
                "overall_resistance": auth_audit["overall_resistance"],
                "weakest_method": auth_audit["weakest_method"],
                "fido2_coverage_pct": auth_audit["fido2_coverage_pct"],
            },
            "iam_exposure": {
                "total_iam_nodes": iam_analysis["total_iam_nodes"],
                "internet_facing": iam_analysis["internet_facing_iam_count"],
                "high_risk_findings": iam_analysis["iam_finding_count"],
            },
            "recommendations": recommendations,
        }

    async def authentication_audit(self, workspace_id: uuid.UUID) -> dict:
        """Audit authentication methods for deepfake resistance."""
        # Query IAM-related graph nodes to understand auth posture
        result = await self.db.execute(
            select(SecurityGraphNode).where(
                SecurityGraphNode.workspace_id == workspace_id,
                SecurityGraphNode.node_type == "iam_role",
            )
        )
        iam_nodes = list(result.scalars().all())

        # Query IAM/auth-related findings
        result = await self.db.execute(
            select(CanonicalFinding).where(
                CanonicalFinding.workspace_id == workspace_id,
                CanonicalFinding.status != FindingStatus.RESOLVED,
            )
        )
        findings = list(result.scalars().all())

        auth_findings = [f for f in findings if any(
            kw in (f.title or "").lower()
            for kw in ("mfa", "multi-factor", "authentication", "password", "credential", "login", "sso", "fido", "passkey")
        )]

        # Analyze which auth methods are indicated by findings
        detected_methods: dict[str, dict[str, Any]] = {}
        has_mfa_issues = any("mfa" in (f.title or "").lower() for f in auth_findings)
        has_password_issues = any("password" in (f.title or "").lower() for f in auth_findings)
        has_fido2 = any("fido" in (f.title or "").lower() or "passkey" in (f.title or "").lower() for f in auth_findings)

        # Build method assessment
        if has_fido2:
            detected_methods["fido2_passkey"] = {**AUTH_RESISTANCE["fido2_passkey"], "detected": True, "coverage_pct": 15}
        if has_mfa_issues:
            detected_methods["totp_app"] = {**AUTH_RESISTANCE["totp_app"], "detected": True, "coverage_pct": 40}
            detected_methods["sms_otp"] = {**AUTH_RESISTANCE["sms_otp"], "detected": True, "coverage_pct": 30}
        if has_password_issues:
            detected_methods["password_only"] = {**AUTH_RESISTANCE["password_only"], "detected": True, "coverage_pct": 60}

        # Default assessment when no specific findings exist
        if not detected_methods:
            detected_methods = {
                "totp_app": {**AUTH_RESISTANCE["totp_app"], "detected": False, "coverage_pct": 50},
                "sms_otp": {**AUTH_RESISTANCE["sms_otp"], "detected": False, "coverage_pct": 25},
                "password_only": {**AUTH_RESISTANCE["password_only"], "detected": False, "coverage_pct": 15},
                "push_notification": {**AUTH_RESISTANCE["push_notification"], "detected": False, "coverage_pct": 10},
            }

        # Compute weighted resistance score
        total_coverage = sum(m["coverage_pct"] for m in detected_methods.values())
        if total_coverage > 0:
            weighted_resistance = sum(
                m["resistance"] * m["coverage_pct"] for m in detected_methods.values()
            ) / total_coverage
        else:
            weighted_resistance = 30.0

        # Find weakest method in use
        weakest = min(detected_methods.values(), key=lambda m: m["resistance"])
        fido2_info = detected_methods.get("fido2_passkey", {})

        return {
            "overall_resistance": round(weighted_resistance, 1),
            "methods": detected_methods,
            "weakest_method": weakest["label"],
            "weakest_resistance": weakest["resistance"],
            "fido2_coverage_pct": fido2_info.get("coverage_pct", 0),
            "total_iam_roles": len(iam_nodes),
            "auth_findings": len(auth_findings),
            "deepfake_resistance_matrix": {
                k: {"resistance": v["resistance"], "bypassed_by": v["bypassed_by"]}
                for k, v in AUTH_RESISTANCE.items()
            },
        }

    async def _iam_exposure_analysis(self, workspace_id: uuid.UUID) -> dict:
        """Analyze IAM exposure surface for deepfake attack targeting."""
        # Count IAM nodes
        iam_count_result = await self.db.execute(
            select(func.count(SecurityGraphNode.id)).where(
                SecurityGraphNode.workspace_id == workspace_id,
                SecurityGraphNode.node_type == "iam_role",
            )
        )
        total_iam = iam_count_result.scalar() or 0

        # Count internet-facing IAM-adjacent resources
        internet_result = await self.db.execute(
            select(func.count(SecurityGraphNode.id)).where(
                SecurityGraphNode.workspace_id == workspace_id,
                SecurityGraphNode.is_internet_facing == True,
            )
        )
        internet_facing = internet_result.scalar() or 0

        # Count IAM-related findings
        finding_result = await self.db.execute(
            select(func.count(CanonicalFinding.id)).where(
                CanonicalFinding.workspace_id == workspace_id,
                CanonicalFinding.status != FindingStatus.RESOLVED,
            )
        )
        all_open = finding_result.scalar() or 0

        # Filter for IAM-specific findings by querying with title patterns
        iam_finding_result = await self.db.execute(
            select(CanonicalFinding).where(
                CanonicalFinding.workspace_id == workspace_id,
                CanonicalFinding.status != FindingStatus.RESOLVED,
            )
        )
        iam_findings = [
            f for f in iam_finding_result.scalars().all()
            if any(kw in (f.title or "").lower() for kw in ("iam", "role", "policy", "privilege", "access"))
        ]

        return {
            "total_iam_nodes": total_iam,
            "internet_facing_iam_count": internet_facing,
            "iam_finding_count": len(iam_findings),
            "total_open_findings": all_open,
        }

    async def _generate_recommendations(self, auth_audit: dict, iam_analysis: dict) -> list[dict]:
        """Generate prioritized deepfake defense recommendations."""
        recommendations = []

        if auth_audit["fido2_coverage_pct"] < 80:
            recommendations.append({
                "priority": "CRITICAL",
                "title": "Deploy FIDO2/Passkey Authentication",
                "description": "FIDO2 passkeys are the only authentication method with 95%+ deepfake resistance. "
                               f"Current coverage is {auth_audit['fido2_coverage_pct']}%.",
                "effort": "MEDIUM",
                "impact": "HIGH",
                "category": "authentication",
            })

        if auth_audit["weakest_resistance"] < 30:
            recommendations.append({
                "priority": "HIGH",
                "title": f"Eliminate Weak Auth: {auth_audit['weakest_method']}",
                "description": f"{auth_audit['weakest_method']} has only {auth_audit['weakest_resistance']}% "
                               "deepfake resistance. Migrate users to phishing-resistant MFA.",
                "effort": "LOW",
                "impact": "HIGH",
                "category": "authentication",
            })

        recommendations.append({
            "priority": "HIGH",
            "title": "Implement Out-of-Band Verification for Financial Transactions",
            "description": "Require callback on a pre-registered number for any wire transfer or payment "
                           "change request, regardless of requester identity.",
            "effort": "LOW",
            "impact": "HIGH",
            "category": "process",
        })

        recommendations.append({
            "priority": "MEDIUM",
            "title": "Deploy Behavioral Biometric Baseline",
            "description": "Establish keystroke dynamics, mouse movement patterns, and session behavior "
                           "baselines to detect account takeover even with valid credentials.",
            "effort": "HIGH",
            "impact": "MEDIUM",
            "category": "detection",
        })

        if iam_analysis["iam_finding_count"] > 5:
            recommendations.append({
                "priority": "HIGH",
                "title": "Remediate IAM Findings to Reduce Attack Surface",
                "description": f"{iam_analysis['iam_finding_count']} open IAM findings increase deepfake "
                               "attack surface. Least-privilege remediation limits blast radius.",
                "effort": "MEDIUM",
                "impact": "MEDIUM",
                "category": "iam",
            })

        recommendations.append({
            "priority": "MEDIUM",
            "title": "Deepfake Awareness Training Program",
            "description": "Train finance, HR, and IT helpdesk staff to recognize deepfake social engineering. "
                           "Include simulated voice clone attacks in security awareness program.",
            "effort": "LOW",
            "impact": "MEDIUM",
            "category": "training",
        })

        return recommendations
