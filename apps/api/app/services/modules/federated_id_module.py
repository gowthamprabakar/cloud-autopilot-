"""
FederatedIDModule — Federated Identity Cross-Cloud Abuse simulation.

Sprint 34: Simulates federated identity attacks:
1. Golden SAML attacks (APT29/Solarigate pattern)
2. OIDC token binding validation
3. Cross-tenant sync auditing
4. Refresh token mass-revocation SLA
5. Cross-cloud identity correlation
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.canonical_finding import CanonicalFinding
from app.models.security_graph_node import SecurityGraphNode
from app.models.security_graph_edge import SecurityGraphEdge

# ── Constants ─────────────────────────────────────────────────────────────────

# Identity provider node types
_IDP_NODE_TYPES = {
    "iam_role", "iam_user", "iam_policy", "iam_group",
    "saml_provider", "oidc_provider", "identity_provider",
    "sso", "cognito", "directory_service",
}

# Cross-cloud identity provider identifiers
_CLOUD_IDENTITY_PROVIDERS: dict[str, dict[str, Any]] = {
    "aws_iam": {
        "arn_patterns": ["arn:aws:iam:"],
        "node_keywords": ["iam", "aws-iam"],
        "cloud": "AWS",
        "provider_type": "native",
    },
    "aws_sso": {
        "arn_patterns": ["arn:aws:sso:"],
        "node_keywords": ["sso", "identity-center", "aws-sso"],
        "cloud": "AWS",
        "provider_type": "sso",
    },
    "azure_ad": {
        "arn_patterns": [],
        "node_keywords": ["azure-ad", "entra-id", "aad", "microsoft-entra"],
        "cloud": "Azure",
        "provider_type": "directory",
    },
    "gcp_iam": {
        "arn_patterns": [],
        "node_keywords": ["gcp-iam", "google-iam", "gcloud-iam"],
        "cloud": "GCP",
        "provider_type": "native",
    },
    "okta": {
        "arn_patterns": [],
        "node_keywords": ["okta"],
        "cloud": "SaaS",
        "provider_type": "idp",
    },
    "ping_identity": {
        "arn_patterns": [],
        "node_keywords": ["ping", "pingfederate", "pingone"],
        "cloud": "SaaS",
        "provider_type": "idp",
    },
}

# SAML-related keywords for Golden SAML detection
_SAML_KEYWORDS = [
    "saml", "saml2", "assertion", "token signing",
    "certificate", "federation", "adfs", "ws-federation",
    "metadata", "relying party",
]

# Golden SAML attack indicators
_GOLDEN_SAML_INDICATORS = [
    "token signing certificate", "certificate export",
    "adfs", "saml assertion", "forged token",
    "golden saml", "token forgery", "mimikatz",
    "dcsync", "ad replication", "certificate private key",
    "token signing key", "saml provider", "trust relationship",
    "solarigate", "sunburst", "nobelium", "apt29",
]

# OIDC-related keywords
_OIDC_KEYWORDS = [
    "oidc", "openid", "jwt", "jwks", "id_token",
    "access_token", "audience", "issuer", "client_id",
    "client_secret", "authorization_code", "pkce",
]

# Token/credential revocation keywords
_REVOCATION_KEYWORDS = [
    "revoke", "revocation", "token lifetime",
    "session", "refresh token", "expiry", "timeout",
    "invalidate", "rotation", "max age",
]

# Trust relationship edge types
_TRUST_EDGE_TYPES = {
    "assumes_role", "has_access_to", "trusts",
    "federates_to", "delegates_to", "authenticates_via",
}

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def _parse_json(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return None


def _text_matches(text: str, keywords: list[str]) -> list[str]:
    lower = text.lower()
    return [kw for kw in keywords if kw.lower() in lower]


# ── Service ───────────────────────────────────────────────────────────────────


class FederatedIDModule:
    """Federated Identity Cross-Cloud Abuse — assesses Golden SAML attack
    surface, validates OIDC token bindings, correlates cross-cloud identities,
    and measures refresh token revocation SLAs."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _all_nodes(
        self, workspace_id: uuid.UUID,
    ) -> list[SecurityGraphNode]:
        q = select(SecurityGraphNode).where(
            SecurityGraphNode.workspace_id == workspace_id,
        )
        return list((await self.db.execute(q)).scalars().all())

    async def _all_findings(
        self, workspace_id: uuid.UUID,
    ) -> list[CanonicalFinding]:
        q = select(CanonicalFinding).where(
            CanonicalFinding.workspace_id == workspace_id,
        )
        return list((await self.db.execute(q)).scalars().all())

    async def _all_edges(
        self, workspace_id: uuid.UUID,
    ) -> list[SecurityGraphEdge]:
        q = select(SecurityGraphEdge).where(
            SecurityGraphEdge.workspace_id == workspace_id,
        )
        return list((await self.db.execute(q)).scalars().all())

    def _identify_cloud_provider(self, node: SecurityGraphNode) -> str | None:
        """Identify which cloud identity provider a node belongs to."""
        arn = (node.resource_arn or "").lower()
        name = (node.resource_name or "").lower()
        ntype = (node.node_type or "").lower()
        meta = _parse_json(node.node_metadata) or {}
        combined = f"{arn} {name} {ntype} {json.dumps(meta)}".lower()

        for provider_key, provider_info in _CLOUD_IDENTITY_PROVIDERS.items():
            for pattern in provider_info["arn_patterns"]:
                if pattern in arn:
                    return provider_key
            for keyword in provider_info["node_keywords"]:
                if keyword in combined:
                    return provider_key

        # Fallback: IAM-type nodes default to AWS IAM
        if ntype in _IDP_NODE_TYPES:
            return "aws_iam"
        return None

    def _extract_trust_details(self, edge: SecurityGraphEdge) -> dict:
        """Extract trust relationship details from edge metadata."""
        meta = _parse_json(edge.edge_metadata) or {}
        return {
            "trust_type": meta.get("trust_type", edge.edge_type),
            "conditions": meta.get("conditions", []),
            "external_id": meta.get("external_id"),
            "source_account": meta.get("source_account"),
            "target_account": meta.get("target_account"),
            "is_cross_account": bool(meta.get("is_cross_account", False)),
            "is_cross_cloud": bool(meta.get("is_cross_cloud", False)),
            "federation_protocol": meta.get("federation_protocol"),
        }

    # ── Public API ───────────────────────────────────────────────────────

    async def golden_saml_assessment(self, workspace_id: uuid.UUID) -> dict:
        """Assess Golden SAML attack surface.

        Queries SecurityGraphNode for SAML provider configurations,
        evaluates certificate management practices, and correlates with
        CanonicalFinding for APT29/Solarigate attack indicators.
        """
        all_nodes = await self._all_nodes(workspace_id)
        all_findings = await self._all_findings(workspace_id)
        all_edges = await self._all_edges(workspace_id)

        node_map: dict[uuid.UUID, SecurityGraphNode] = {n.id: n for n in all_nodes}

        # Index findings by ARN
        findings_by_arn: dict[str, list[CanonicalFinding]] = {}
        for f in all_findings:
            findings_by_arn.setdefault(f.resource_arn or "", []).append(f)

        # Identify SAML provider nodes
        saml_nodes: list[SecurityGraphNode] = []
        for node in all_nodes:
            ntype = (node.node_type or "").lower()
            meta = _parse_json(node.node_metadata) or {}
            combined = f"{ntype} {node.resource_name or ''} {json.dumps(meta)}".lower()
            if ntype in ("saml_provider", "identity_provider") or any(
                kw in combined for kw in ("saml", "adfs", "federation", "shibboleth")
            ):
                saml_nodes.append(node)

        # Assess each SAML provider
        provider_assessments: list[dict] = []

        for node in saml_nodes:
            meta = _parse_json(node.node_metadata) or {}
            arn = node.resource_arn or ""
            linked_findings = list(findings_by_arn.get(arn, []))

            risk_factors: list[str] = []
            risk_score = 0.0

            # Check certificate rotation
            cert_expiry = meta.get("certificate_expiry", meta.get("cert_expiry"))
            cert_rotation_days = meta.get("certificate_rotation_days")
            last_rotation = meta.get("last_certificate_rotation")

            if cert_rotation_days is None or (
                isinstance(cert_rotation_days, int) and cert_rotation_days > 365
            ):
                risk_factors.append("no_certificate_rotation_policy")
                risk_score += 2.5

            if cert_expiry:
                try:
                    expiry_dt = datetime.fromisoformat(str(cert_expiry))
                    if expiry_dt.tzinfo is None:
                        expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
                    days_until_expiry = (expiry_dt - datetime.now(timezone.utc)).days
                    if days_until_expiry < 0:
                        risk_factors.append("expired_signing_certificate")
                        risk_score += 3.0
                    elif days_until_expiry < 30:
                        risk_factors.append("certificate_expiring_soon")
                        risk_score += 1.5
                except (ValueError, TypeError):
                    pass

            # Check for certificate private key exposure
            for f in linked_findings:
                if f.status not in ("open", "in_progress"):
                    continue
                text = f"{f.title} {f.description or ''}".lower()
                matched = _text_matches(text, _GOLDEN_SAML_INDICATORS)
                if matched:
                    risk_factors.extend(matched[:3])
                    risk_score += len(matched) * 1.5

            # Check trust relationships for overly broad federation
            trust_edges: list[dict] = []
            for edge in all_edges:
                if edge.source_node_id == node.id or edge.target_node_id == node.id:
                    if edge.edge_type in _TRUST_EDGE_TYPES:
                        trust_detail = self._extract_trust_details(edge)
                        other_id = (
                            edge.target_node_id
                            if edge.source_node_id == node.id
                            else edge.source_node_id
                        )
                        other_node = node_map.get(other_id)
                        trust_detail["connected_to"] = (
                            other_node.resource_name if other_node else str(other_id)
                        )
                        trust_edges.append(trust_detail)

                        # Cross-account or cross-cloud trust increases risk
                        if trust_detail["is_cross_account"]:
                            risk_factors.append("cross_account_trust")
                            risk_score += 1.0
                        if trust_detail["is_cross_cloud"]:
                            risk_factors.append("cross_cloud_trust")
                            risk_score += 1.5

            # Check for missing conditions on trust
            no_condition_trusts = [t for t in trust_edges if not t.get("conditions")]
            if no_condition_trusts:
                risk_factors.append("trust_without_conditions")
                risk_score += len(no_condition_trusts) * 0.5

            risk_score = min(risk_score, 10.0)
            risk_factors = list(set(risk_factors))

            severity = "low"
            if risk_score >= 8.0:
                severity = "critical"
            elif risk_score >= 6.0:
                severity = "high"
            elif risk_score >= 3.5:
                severity = "medium"

            # Golden SAML specific findings
            golden_saml_findings: list[dict] = []
            for f in linked_findings:
                if f.status not in ("open", "in_progress"):
                    continue
                text = f"{f.title} {f.description or ''}".lower()
                matched = _text_matches(text, _GOLDEN_SAML_INDICATORS)
                if matched:
                    golden_saml_findings.append({
                        "finding_id": str(f.id),
                        "title": f.title,
                        "severity": f.severity,
                        "matched_indicators": matched,
                    })

            provider_assessments.append({
                "id": str(node.id),
                "name": node.resource_name or node.resource_arn or str(node.id),
                "node_type": node.node_type,
                "resource_arn": node.resource_arn,
                "risk_score": round(risk_score, 1),
                "severity": severity,
                "risk_factors": risk_factors,
                "certificate_rotation_days": cert_rotation_days,
                "trust_relationships": trust_edges[:10],
                "trust_count": len(trust_edges),
                "trusts_without_conditions": len(no_condition_trusts),
                "golden_saml_findings": golden_saml_findings[:5],
            })

        provider_assessments.sort(key=lambda p: (
            _SEVERITY_ORDER.get(p["severity"], 5),
            -p["risk_score"],
        ))

        # Also scan all findings for Golden SAML indicators not linked to providers
        global_indicators: list[dict] = []
        for f in all_findings:
            if f.status not in ("open", "in_progress"):
                continue
            text = f"{f.title} {f.description or ''}".lower()
            matched = _text_matches(text, _GOLDEN_SAML_INDICATORS)
            if matched:
                already_linked = any(
                    any(gf["finding_id"] == str(f.id) for gf in p.get("golden_saml_findings", []))
                    for p in provider_assessments
                )
                if not already_linked:
                    global_indicators.append({
                        "finding_id": str(f.id),
                        "title": f.title,
                        "severity": f.severity,
                        "matched_indicators": matched,
                        "resource_arn": str(f.resource_arn or ""),
                    })

        return {
            "total_saml_providers": len(saml_nodes),
            "assessed_providers": len(provider_assessments),
            "severity_breakdown": {
                sev: sum(1 for p in provider_assessments if p["severity"] == sev)
                for sev in ("critical", "high", "medium", "low")
            },
            "total_golden_saml_indicators": (
                sum(len(p["golden_saml_findings"]) for p in provider_assessments)
                + len(global_indicators)
            ),
            "global_indicators": global_indicators[:10],
            "provider_assessments": provider_assessments,
        }

    async def oidc_validation(self, workspace_id: uuid.UUID) -> dict:
        """Validate OIDC token binding configuration.

        Examines SecurityGraphNode metadata for OIDC provider audience
        restriction, issuer validation, token lifetime, and PKCE enforcement.
        """
        all_nodes = await self._all_nodes(workspace_id)
        all_findings = await self._all_findings(workspace_id)

        # Index findings by ARN
        findings_by_arn: dict[str, list[CanonicalFinding]] = {}
        for f in all_findings:
            findings_by_arn.setdefault(f.resource_arn or "", []).append(f)

        # Identify OIDC provider nodes
        oidc_nodes: list[SecurityGraphNode] = []
        for node in all_nodes:
            ntype = (node.node_type or "").lower()
            meta = _parse_json(node.node_metadata) or {}
            combined = f"{ntype} {node.resource_name or ''} {json.dumps(meta)}".lower()
            if ntype in ("oidc_provider", "identity_provider") or any(
                kw in combined for kw in ("oidc", "openid", "oauth", "cognito")
            ):
                oidc_nodes.append(node)

        # Validate each OIDC provider
        validations: list[dict] = []

        for node in oidc_nodes:
            meta = _parse_json(node.node_metadata) or {}
            arn = node.resource_arn or ""
            linked_findings = list(findings_by_arn.get(arn, []))

            checks: list[dict] = []
            risk_score = 0.0

            # Check 1: Audience restriction
            audiences = meta.get("audience", meta.get("client_id_list", []))
            if isinstance(audiences, str):
                audiences = [audiences]
            has_audience = bool(audiences)
            has_wildcard_audience = any(a in ("*", "any") for a in (audiences or []))
            checks.append({
                "check": "audience_restriction",
                "status": "fail" if not has_audience or has_wildcard_audience else "pass",
                "detail": (
                    f"{len(audiences)} audience(s) configured"
                    if has_audience and not has_wildcard_audience
                    else "No audience restriction or wildcard audience"
                ),
            })
            if not has_audience or has_wildcard_audience:
                risk_score += 2.5

            # Check 2: Issuer validation
            issuer = meta.get("issuer", meta.get("issuer_url", meta.get("url", "")))
            has_issuer = bool(issuer)
            issuer_https = str(issuer).startswith("https://") if issuer else False
            checks.append({
                "check": "issuer_validation",
                "status": "pass" if has_issuer and issuer_https else "fail",
                "detail": (
                    f"Issuer: {issuer}" if has_issuer
                    else "No issuer URL configured"
                ),
            })
            if not has_issuer or not issuer_https:
                risk_score += 2.0

            # Check 3: Token lifetime
            token_lifetime = meta.get(
                "token_lifetime_hours",
                meta.get("access_token_validity_hours"),
            )
            max_acceptable_hours = 12
            if isinstance(token_lifetime, (int, float)):
                lifetime_ok = token_lifetime <= max_acceptable_hours
            else:
                lifetime_ok = False
                token_lifetime = None
            checks.append({
                "check": "token_lifetime",
                "status": "pass" if lifetime_ok else ("warn" if token_lifetime else "unknown"),
                "detail": (
                    f"Token lifetime: {token_lifetime}h (max recommended: {max_acceptable_hours}h)"
                    if token_lifetime
                    else "Token lifetime not configured in metadata"
                ),
            })
            if not lifetime_ok:
                risk_score += 1.5

            # Check 4: PKCE enforcement
            pkce_enabled = meta.get("pkce_enabled", meta.get("require_pkce"))
            checks.append({
                "check": "pkce_enforcement",
                "status": "pass" if pkce_enabled else ("fail" if pkce_enabled is False else "unknown"),
                "detail": (
                    "PKCE enforced" if pkce_enabled
                    else "PKCE not enforced or unknown"
                ),
            })
            if not pkce_enabled:
                risk_score += 1.5

            # Check 5: Token binding (DPoP / mTLS)
            token_binding = meta.get("token_binding", meta.get("dpop_enabled"))
            checks.append({
                "check": "token_binding",
                "status": "pass" if token_binding else "warn",
                "detail": (
                    "Token binding (DPoP/mTLS) enabled" if token_binding
                    else "No token binding — bearer tokens may be replayed"
                ),
            })
            if not token_binding:
                risk_score += 1.0

            # Check 6: Thumbprint validation (AWS-specific for OIDC providers)
            thumbprints = meta.get("thumbprints", meta.get("thumbprint_list", []))
            checks.append({
                "check": "thumbprint_validation",
                "status": "pass" if thumbprints else "warn",
                "detail": (
                    f"{len(thumbprints)} thumbprint(s) configured"
                    if thumbprints
                    else "No thumbprints configured"
                ),
            })
            if not thumbprints:
                risk_score += 1.0

            # Correlate with findings
            oidc_findings: list[dict] = []
            for f in linked_findings:
                if f.status not in ("open", "in_progress"):
                    continue
                text = f"{f.title} {f.description or ''}".lower()
                matched = _text_matches(text, _OIDC_KEYWORDS)
                if matched:
                    oidc_findings.append({
                        "finding_id": str(f.id),
                        "title": f.title,
                        "severity": f.severity,
                        "matched_indicators": matched,
                    })
                    risk_score += 0.5

            risk_score = min(risk_score, 10.0)

            passed = sum(1 for c in checks if c["status"] == "pass")
            failed = sum(1 for c in checks if c["status"] == "fail")
            total = len(checks)

            severity = "low"
            if risk_score >= 7.0:
                severity = "critical"
            elif risk_score >= 5.0:
                severity = "high"
            elif risk_score >= 3.0:
                severity = "medium"

            validations.append({
                "id": str(node.id),
                "name": node.resource_name or node.resource_arn or str(node.id),
                "node_type": node.node_type,
                "resource_arn": node.resource_arn,
                "issuer": str(issuer) if issuer else None,
                "risk_score": round(risk_score, 1),
                "severity": severity,
                "checks_passed": passed,
                "checks_failed": failed,
                "checks_total": total,
                "compliance_rate": round(passed / total * 100, 1) if total > 0 else 0.0,
                "checks": checks,
                "oidc_findings": oidc_findings[:5],
            })

        validations.sort(key=lambda v: (
            _SEVERITY_ORDER.get(v["severity"], 5),
            -v["risk_score"],
        ))

        total_checks = sum(v["checks_total"] for v in validations)
        total_passed = sum(v["checks_passed"] for v in validations)

        return {
            "total_oidc_providers": len(oidc_nodes),
            "validated_providers": len(validations),
            "total_checks": total_checks,
            "total_passed": total_passed,
            "overall_compliance_rate": round(
                total_passed / total_checks * 100, 1
            ) if total_checks > 0 else 100.0,
            "severity_breakdown": {
                sev: sum(1 for v in validations if v["severity"] == sev)
                for sev in ("critical", "high", "medium", "low")
            },
            "validations": validations,
        }

    async def cross_cloud_correlation(self, workspace_id: uuid.UUID) -> dict:
        """Correlate identities across AWS IAM, Azure AD, GCP IAM.

        Maps SecurityGraphNode identity providers, traverses trust
        relationship edges, and identifies orphaned identities and
        stale cross-cloud trusts.
        """
        all_nodes = await self._all_nodes(workspace_id)
        all_findings = await self._all_findings(workspace_id)
        all_edges = await self._all_edges(workspace_id)

        node_map: dict[uuid.UUID, SecurityGraphNode] = {n.id: n for n in all_nodes}

        # Classify identity nodes by cloud provider
        cloud_identities: dict[str, list[dict]] = {}
        identity_nodes: list[SecurityGraphNode] = []

        for node in all_nodes:
            provider = self._identify_cloud_provider(node)
            if not provider:
                continue

            ntype = (node.node_type or "").lower()
            if ntype not in _IDP_NODE_TYPES:
                continue

            identity_nodes.append(node)
            meta = _parse_json(node.node_metadata) or {}

            identity_info = {
                "id": str(node.id),
                "name": node.resource_name or node.resource_arn or str(node.id),
                "node_type": node.node_type,
                "resource_arn": node.resource_arn,
                "cloud_provider": provider,
                "cloud": _CLOUD_IDENTITY_PROVIDERS.get(provider, {}).get("cloud", "Unknown"),
                "region": node.region,
                "risk_score": node.risk_score,
                "is_internet_facing": bool(node.is_internet_facing),
                "last_activity": meta.get("last_activity", meta.get("last_used")),
            }
            cloud_identities.setdefault(provider, []).append(identity_info)

        # Map trust relationships (cross-cloud and cross-account)
        trust_relationships: list[dict] = []
        for edge in all_edges:
            if edge.edge_type not in _TRUST_EDGE_TYPES:
                continue

            src = node_map.get(edge.source_node_id)
            tgt = node_map.get(edge.target_node_id)
            if not src or not tgt:
                continue

            src_provider = self._identify_cloud_provider(src)
            tgt_provider = self._identify_cloud_provider(tgt)
            if not src_provider and not tgt_provider:
                continue

            trust_detail = self._extract_trust_details(edge)
            is_cross_cloud = (
                src_provider != tgt_provider
                and src_provider is not None
                and tgt_provider is not None
            )

            trust_relationships.append({
                "edge_id": str(edge.id),
                "source_identity": src.resource_name or str(src.id),
                "source_provider": src_provider,
                "source_cloud": _CLOUD_IDENTITY_PROVIDERS.get(
                    src_provider or "", {}
                ).get("cloud", "Unknown"),
                "target_identity": tgt.resource_name or str(tgt.id),
                "target_provider": tgt_provider,
                "target_cloud": _CLOUD_IDENTITY_PROVIDERS.get(
                    tgt_provider or "", {}
                ).get("cloud", "Unknown"),
                "edge_type": edge.edge_type,
                "is_cross_cloud": is_cross_cloud,
                "is_attack_path": bool(edge.is_attack_path),
                "risk_contribution": edge.risk_contribution or 0.0,
                "trust_details": trust_detail,
            })

        # Identify orphaned identities: no edges, or stale last_activity
        orphaned_identities: list[dict] = []
        now = datetime.now(timezone.utc)

        for node in identity_nodes:
            meta = _parse_json(node.node_metadata) or {}
            last_activity = meta.get("last_activity", meta.get("last_used"))

            # Check if node has any edges
            has_edges = any(
                e.source_node_id == node.id or e.target_node_id == node.id
                for e in all_edges
            )

            # Check staleness
            is_stale = False
            stale_days = 0
            if last_activity:
                try:
                    last_dt = datetime.fromisoformat(str(last_activity))
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=timezone.utc)
                    stale_days = (now - last_dt).days
                    is_stale = stale_days > 90
                except (ValueError, TypeError):
                    pass

            # Check for orphan signals in findings
            orphan_signals: list[str] = []
            if not has_edges:
                orphan_signals.append("no_trust_relationships")
            if is_stale:
                orphan_signals.append(f"stale_{stale_days}_days")

            # Check findings for orphan indicators
            arn = node.resource_arn or ""
            for f in all_findings:
                if f.resource_arn != arn or f.status not in ("open", "in_progress"):
                    continue
                text = f"{f.title} {f.description or ''}".lower()
                if any(kw in text for kw in (
                    "orphan", "unused", "stale", "no activity",
                    "never used", "dormant",
                )):
                    orphan_signals.append("finding_indicated_orphan")
                    break

            if len(orphan_signals) < 1:
                continue

            provider = self._identify_cloud_provider(node)
            severity = "high" if len(orphan_signals) >= 2 else "medium"
            if node.is_internet_facing:
                severity = "critical"

            orphaned_identities.append({
                "id": str(node.id),
                "name": node.resource_name or str(node.id),
                "node_type": node.node_type,
                "resource_arn": node.resource_arn,
                "cloud_provider": provider,
                "cloud": _CLOUD_IDENTITY_PROVIDERS.get(
                    provider or "", {}
                ).get("cloud", "Unknown"),
                "orphan_signals": orphan_signals,
                "stale_days": stale_days,
                "severity": severity,
                "risk_score": node.risk_score,
            })

        orphaned_identities.sort(key=lambda o: (
            _SEVERITY_ORDER.get(o["severity"], 5),
            -o["stale_days"],
        ))

        # Stale trust detection
        stale_trusts: list[dict] = []
        for trust in trust_relationships:
            detail = trust.get("trust_details", {})
            # A trust is stale if no conditions and connected to orphaned identity
            orphaned_ids = {o["id"] for o in orphaned_identities}
            src_node = next(
                (n for n in all_nodes if n.resource_name == trust["source_identity"]),
                None,
            )
            tgt_node = next(
                (n for n in all_nodes if n.resource_name == trust["target_identity"]),
                None,
            )
            if (src_node and str(src_node.id) in orphaned_ids) or (
                tgt_node and str(tgt_node.id) in orphaned_ids
            ):
                stale_trusts.append({
                    **trust,
                    "reason": "connected_to_orphaned_identity",
                })
            elif not detail.get("conditions") and trust["is_cross_cloud"]:
                stale_trusts.append({
                    **trust,
                    "reason": "cross_cloud_without_conditions",
                })

        # Summary by cloud
        cloud_summary: dict[str, int] = {}
        for provider, identities in cloud_identities.items():
            cloud = _CLOUD_IDENTITY_PROVIDERS.get(provider, {}).get("cloud", "Unknown")
            cloud_summary[cloud] = cloud_summary.get(cloud, 0) + len(identities)

        return {
            "total_identity_nodes": len(identity_nodes),
            "cloud_distribution": cloud_summary,
            "provider_distribution": {k: len(v) for k, v in cloud_identities.items()},
            "total_trust_relationships": len(trust_relationships),
            "cross_cloud_trusts": sum(1 for t in trust_relationships if t["is_cross_cloud"]),
            "attack_path_trusts": sum(1 for t in trust_relationships if t["is_attack_path"]),
            "orphaned_identities": len(orphaned_identities),
            "stale_trusts": len(stale_trusts),
            "trust_relationships": trust_relationships[:30],
            "orphaned_identity_list": orphaned_identities[:20],
            "stale_trust_list": stale_trusts[:20],
        }

    async def token_revocation_sla(self, workspace_id: uuid.UUID) -> dict:
        """Assess refresh token mass-revocation capability.

        Evaluates identity provider nodes for revocation mechanism
        configuration, SLA compliance (5-minute target), and correlates
        with findings for token management issues.
        """
        all_nodes = await self._all_nodes(workspace_id)
        all_findings = await self._all_findings(workspace_id)

        # Index findings by ARN
        findings_by_arn: dict[str, list[CanonicalFinding]] = {}
        for f in all_findings:
            findings_by_arn.setdefault(f.resource_arn or "", []).append(f)

        # Identify identity provider nodes with token management
        target_sla_minutes = 5

        provider_assessments: list[dict] = []

        for node in all_nodes:
            provider = self._identify_cloud_provider(node)
            if not provider:
                continue

            ntype = (node.node_type or "").lower()
            if ntype not in _IDP_NODE_TYPES:
                continue

            meta = _parse_json(node.node_metadata) or {}

            # Extract token revocation configuration
            revocation_config = meta.get("revocation", meta.get("token_revocation", {}))
            if not isinstance(revocation_config, dict):
                revocation_config = {}

            # Check revocation capabilities
            checks: list[dict] = []

            # Check 1: Revocation endpoint exists
            has_revocation_endpoint = bool(
                revocation_config.get("endpoint")
                or meta.get("revocation_endpoint")
                or meta.get("revoke_endpoint")
            )
            checks.append({
                "check": "revocation_endpoint",
                "status": "pass" if has_revocation_endpoint else "fail",
                "detail": (
                    "Revocation endpoint configured"
                    if has_revocation_endpoint
                    else "No revocation endpoint found"
                ),
            })

            # Check 2: Mass revocation capability
            has_mass_revocation = bool(
                revocation_config.get("mass_revocation")
                or revocation_config.get("bulk_revoke")
                or meta.get("global_sign_out")
            )
            checks.append({
                "check": "mass_revocation",
                "status": "pass" if has_mass_revocation else "fail",
                "detail": (
                    "Mass/bulk revocation capability available"
                    if has_mass_revocation
                    else "No mass revocation capability detected"
                ),
            })

            # Check 3: Revocation SLA
            revocation_sla = revocation_config.get(
                "sla_minutes",
                meta.get("revocation_sla_minutes"),
            )
            sla_met = False
            if isinstance(revocation_sla, (int, float)):
                sla_met = revocation_sla <= target_sla_minutes
            checks.append({
                "check": "revocation_sla",
                "status": "pass" if sla_met else ("warn" if revocation_sla else "unknown"),
                "detail": (
                    f"Revocation SLA: {revocation_sla}min (target: {target_sla_minutes}min)"
                    if revocation_sla
                    else f"Revocation SLA not configured (target: {target_sla_minutes}min)"
                ),
                "current_sla_minutes": revocation_sla,
                "target_sla_minutes": target_sla_minutes,
            })

            # Check 4: Token lifetime limits
            max_token_lifetime = meta.get(
                "refresh_token_lifetime_hours",
                meta.get("refresh_token_max_age_hours"),
            )
            lifetime_acceptable = (
                isinstance(max_token_lifetime, (int, float))
                and max_token_lifetime <= 24
            )
            checks.append({
                "check": "refresh_token_lifetime",
                "status": "pass" if lifetime_acceptable else (
                    "warn" if max_token_lifetime else "unknown"
                ),
                "detail": (
                    f"Refresh token lifetime: {max_token_lifetime}h"
                    if max_token_lifetime
                    else "Refresh token lifetime not configured"
                ),
            })

            # Check 5: Session invalidation on password change
            invalidate_on_pw_change = meta.get(
                "invalidate_on_password_change",
                meta.get("revoke_on_pw_change"),
            )
            checks.append({
                "check": "invalidate_on_password_change",
                "status": "pass" if invalidate_on_pw_change else (
                    "fail" if invalidate_on_pw_change is False else "unknown"
                ),
                "detail": (
                    "Sessions invalidated on password change"
                    if invalidate_on_pw_change
                    else "Sessions may persist after password change"
                ),
            })

            # Check 6: Monitoring/alerting on revocation events
            has_monitoring = bool(
                revocation_config.get("monitoring")
                or meta.get("revocation_alerting")
                or meta.get("cloudwatch_alarms")
            )
            checks.append({
                "check": "revocation_monitoring",
                "status": "pass" if has_monitoring else "warn",
                "detail": (
                    "Revocation event monitoring configured"
                    if has_monitoring
                    else "No revocation event monitoring"
                ),
            })

            # Correlate with findings
            arn = node.resource_arn or ""
            linked_findings = list(findings_by_arn.get(arn, []))
            revocation_findings: list[dict] = []
            for f in linked_findings:
                if f.status not in ("open", "in_progress"):
                    continue
                text = f"{f.title} {f.description or ''}".lower()
                matched = _text_matches(text, _REVOCATION_KEYWORDS)
                if matched:
                    revocation_findings.append({
                        "finding_id": str(f.id),
                        "title": f.title,
                        "severity": f.severity,
                        "matched_indicators": matched,
                    })

            passed = sum(1 for c in checks if c["status"] == "pass")
            failed = sum(1 for c in checks if c["status"] == "fail")
            total = len(checks)

            # Calculate risk score
            risk_score = 0.0
            risk_score += (total - passed) * 1.2
            risk_score += len(revocation_findings) * 0.5
            if not has_mass_revocation:
                risk_score += 2.0
            if not sla_met and revocation_sla and revocation_sla > target_sla_minutes:
                risk_score += min((revocation_sla - target_sla_minutes) * 0.3, 2.0)
            risk_score = min(risk_score, 10.0)

            severity = "low"
            if risk_score >= 7.0:
                severity = "critical"
            elif risk_score >= 5.0:
                severity = "high"
            elif risk_score >= 3.0:
                severity = "medium"

            provider_assessments.append({
                "id": str(node.id),
                "name": node.resource_name or node.resource_arn or str(node.id),
                "node_type": node.node_type,
                "resource_arn": node.resource_arn,
                "cloud_provider": provider,
                "cloud": _CLOUD_IDENTITY_PROVIDERS.get(provider, {}).get("cloud", "Unknown"),
                "risk_score": round(risk_score, 1),
                "severity": severity,
                "checks_passed": passed,
                "checks_failed": failed,
                "checks_total": total,
                "compliance_rate": round(passed / total * 100, 1) if total > 0 else 0.0,
                "current_sla_minutes": revocation_sla,
                "sla_target_minutes": target_sla_minutes,
                "sla_met": sla_met,
                "checks": checks,
                "revocation_findings": revocation_findings[:5],
            })

        provider_assessments.sort(key=lambda p: (
            _SEVERITY_ORDER.get(p["severity"], 5),
            -p["risk_score"],
        ))

        total_checks = sum(p["checks_total"] for p in provider_assessments)
        total_passed = sum(p["checks_passed"] for p in provider_assessments)
        sla_compliant = sum(1 for p in provider_assessments if p["sla_met"])

        return {
            "total_providers_assessed": len(provider_assessments),
            "target_sla_minutes": target_sla_minutes,
            "sla_compliant_providers": sla_compliant,
            "sla_non_compliant_providers": len(provider_assessments) - sla_compliant,
            "total_checks": total_checks,
            "total_passed": total_passed,
            "overall_compliance_rate": round(
                total_passed / total_checks * 100, 1
            ) if total_checks > 0 else 100.0,
            "severity_breakdown": {
                sev: sum(1 for p in provider_assessments if p["severity"] == sev)
                for sev in ("critical", "high", "medium", "low")
            },
            "provider_assessments": provider_assessments,
        }
