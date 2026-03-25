# OmniSec Enterprise Platform -- Comprehensive Gap Analysis
## Cloud Copilot Codebase vs OmniSec Requirements

**Date:** 2026-03-25
**Scope:** Full mapping of existing Cloud Copilot code to OmniSec Enterprise Platform target state
**Methodology:** File-by-file codebase audit + requirement-by-requirement coverage scoring

---

## Executive Summary

| Metric | Value |
|---|---|
| OmniSec Total Modules | 3 (A, B, C) |
| OmniSec Total Submodules | ~23 top-level domains |
| Existing Code Match: FULL | 0 |
| Existing Code Match: PARTIAL | 7 |
| Existing Code Match: NONE | 16 |
| Estimated Overall Reuse | ~18% by effort, ~30% by pattern |
| Net-New Engineering Required | ~70-75% of total platform |
| Infrastructure Overhaul Required | YES (SQLite to PostgreSQL+Neo4j+Redis+Kafka) |

**Bottom line:** Cloud Copilot provides a solid FastAPI+Next.js skeleton, 3 reusable domain services (CIEM, CDR, Vulns), and proven data model patterns. However, OmniSec demands 10x the scope with fundamentally new infrastructure (graph DB, agent orchestration, event streaming). The codebase is a foundation, not a shortcut.

---

## SECTION 1: MODULE-BY-MODULE GAP TABLE

### Module A -- Wiz CNAPP Simulation Layer

| ID | Submodule | Existing Code | Match Level | Reuse % | Effort | Priority | Dependencies | Risk |
|---|---|---|---|---|---|---|---|---|
| A-01 | **CSPM** (Cloud Security Posture Management) | `canonical_finding` model, findings normalization, `risk_score_service`, compliance framework tags, executive dashboard | **PARTIAL** | 40% | **L** | P1 | None (foundation) | LOW -- strongest existing coverage; needs real scanner + policy engine + multi-cloud |
| A-02 | **CWPP** (Cloud Workload Protection) | `vuln_service` (CVE regex extraction, static EPSS dataset of 30 CVEs, static KEV set of 20 CVEs) | **PARTIAL** | 25% | **XL** | P2 | A-01 | HIGH -- static data only; needs runtime agent, ECR/Lambda/EKS scanning, live EPSS/KEV feeds |
| A-03 | **CIEM** (Cloud Infrastructure Entitlement Mgmt) | `ciem_service` (entity inventory, 5 priv-esc patterns, cross-account trust, graph edge detection), `/dashboard/ciem` | **PARTIAL** | 35% | **L** | P1 | A-01, Infra (Neo4j) | MED -- good logic base; needs effective permissions engine, IAM Access Analyzer, least-privilege recs |
| A-04 | **DSPM** (Data Security Posture Management) | None | **NONE** | 0% | **XL** | P3 | A-01, A-03 | HIGH -- entirely new domain; needs Macie integration, data classification engine, DLP policies |
| A-05 | **KSPM** (Kubernetes Security Posture) | None | **NONE** | 0% | **XL** | P3 | A-01, A-02 | HIGH -- no K8s code exists; needs admission controller, CIS K8s benchmarks, runtime policies |
| A-06 | **CDR** (Cloud Detection & Response) | `detection_service.py` (8 correlation rules, MITRE ATT&CK mapping for 8 tactics/techniques), `detections` router, alerts + summary API | **PARTIAL** | 40% | **L** | P1 | A-01, A-03 | LOW -- strongest match; needs CloudTrail streaming, real-time correlation, SOAR playbooks |
| A-07 | **IaC & Code Security** | None | **NONE** | 0% | **XL** | P4 | A-01 | MED -- standard tooling exists (checkov, tfsec); integration effort is well-understood |
| A-08 | **Vulnerability Management** | `vuln_service` (CVE+EPSS+KEV), `/dashboard/vulns`, KEV detection rule in CDR | **PARTIAL** | 30% | **L** | P2 | A-01, A-02 | MED -- good data model; needs live NVD/EPSS feeds, prioritization engine, remediation workflows |
| A-09 | **AI-SPM** (AI Security Posture) | `prompt_registry` (concept exists in ai_service), `ai_insight` + `ai_feedback` models | **MINIMAL** | 10% | **XL** | P4 | A-01, B-03 | HIGH -- prompt registry is basic; needs AI model inventory, shadow AI detection, AI risk scoring |
| A-10 | **ASM** (Attack Surface Management) | None | **NONE** | 0% | **XL** | P3 | A-01, A-03 | HIGH -- needs external recon, domain enumeration, certificate monitoring, exposed API detection |

### Module B -- MiroFish Swarm Intelligence Engine

| ID | Submodule | Existing Code | Match Level | Reuse % | Effort | Priority | Dependencies | Risk |
|---|---|---|---|---|---|---|---|---|
| B-01 | **Seed Ingestion + GraphRAG + Neo4j** | `security_graph_node` + `security_graph_edge` SQLAlchemy models (SQLite); node types: IAMUser, IAMRole, EC2Instance, S3Bucket; edge types: PRIVILEGE_ESCALATION_PATH, ASSUMES_ROLE, HAS_POLICY | **PARTIAL** | 20% | **XL** | P1 | Infra (Neo4j, PostgreSQL) | CRITICAL -- data model concepts transfer but implementation is entirely different; SQLite graph to Neo4j Cypher is a rewrite |
| B-02 | **Agent Anatomy Engine** | None | **NONE** | 0% | **XL** | P2 | B-01, Infra (Redis+Celery) | CRITICAL -- entirely new; needs agent lifecycle, tool registry, capability framework |
| B-03 | **15-Agent Swarm** | None | **NONE** | 0% | **XL** | P2 | B-01, B-02, B-05, B-06 | CRITICAL -- most complex new component; 15 specialized agents need design, testing, orchestration |
| B-04 | **OASIS Simulation Engine** | `attack_path` model (partial), `causal_engine` (7-factor weighted scoring), `SecurityGraphEdge.is_attack_path` field | **PARTIAL** | 15% | **XL** | P3 | B-01, B-03 | HIGH -- attack path concepts exist; needs Monte Carlo simulation, scenario modeling, what-if engine |
| B-05 | **Zep Cloud Memory** | None | **NONE** | 0% | **L** | P2 | Infra (Zep Cloud API) | MED -- third-party integration; well-documented API; moderate effort |
| B-06 | **Communication Bus** | None | **NONE** | 0% | **L** | P1 | Infra (Kafka/EventBridge) | MED -- standard event bus pattern; Redis pub/sub as fallback |

### Module C -- 7 Gap Domains

| ID | Submodule | Existing Code | Match Level | Reuse % | Effort | Priority | Dependencies | Risk |
|---|---|---|---|---|---|---|---|---|
| C-01 | **Multi-Cloud Expansion** (Azure, GCP) | None (AWS-only: `aws_account` model, `aws_scanner` service) | **NONE** | 5% | **XL** | P4 | A-01 | HIGH -- scanner pattern can be cloned but each cloud is ~3 months work |
| C-02 | **Compliance Automation Engine** | Compliance framework tags on findings (JSON array), `/dashboard/compliance` page | **MINIMAL** | 10% | **L** | P2 | A-01 | MED -- needs control mapping, assessment engine, evidence collection, audit workflow |
| C-03 | **SOAR / Orchestration** | `jira_service`, `webhook_service`, `notification_service` -- basic integration stubs | **MINIMAL** | 10% | **XL** | P3 | A-06, B-06 | HIGH -- needs playbook engine, automated response, approval workflows |
| C-04 | **Enterprise SSO & RBAC** | JWT auth + RBAC middleware, `user` model, `workspace` model, `totp` router | **PARTIAL** | 30% | **M** | P1 | Infra (Auth0/Okta) | LOW -- patterns exist; needs SAML/OIDC, SCIM provisioning, fine-grained permissions |
| C-05 | **Reporting & Analytics Engine** | `report_service`, `email_digest_service`, executive dashboard, PDF generation | **PARTIAL** | 25% | **M** | P2 | A-01 | LOW -- good foundation; needs scheduled analytics, custom dashboards, BI export |
| C-06 | **Multi-Tenant Architecture** | `workspace_id` on all models, workspace settings router | **PARTIAL** | 20% | **L** | P1 | Infra (PostgreSQL RLS) | CRITICAL -- SQLite has no RLS; needs complete DB migration, tenant isolation, data partitioning |
| C-07 | **Developer Portal & API Gateway** | FastAPI with `/api/v1/` prefix, `api_keys` router, OpenAPI auto-docs | **MINIMAL** | 15% | **M** | P3 | C-04 | LOW -- FastAPI gives free OpenAPI; needs rate limiting, API versioning, developer docs portal |

---

## SECTION 2: INFRASTRUCTURE MIGRATION MATRIX

| Component | Current State | Target State | Effort | Risk | Priority |
|---|---|---|---|---|---|
| **Primary Database** | SQLite (single file, no concurrency) | PostgreSQL 16 (multi-tenant, RLS, partitioning) | **XL** | CRITICAL | P0 -- blocks everything |
| **Graph Database** | SQLAlchemy models (`security_graph_node`, `security_graph_edge`) in SQLite | Neo4j 5.x (Cypher queries, GraphRAG) | **XL** | CRITICAL | P0 -- blocks B-01 |
| **Cache / Message Queue** | None | Redis 7 + Celery (agent task execution) | **L** | MED | P1 -- blocks B-02, B-03 |
| **Event Streaming** | None | Kafka or AWS EventBridge (integration bus) | **L** | MED | P1 -- blocks B-06 |
| **Agent Memory** | None | Zep Cloud (conversation memory, entity extraction) | **M** | LOW | P2 -- blocks B-05 |
| **Authentication** | JWT + TOTP (custom implementation) | Auth0 or Okta (SAML, OIDC, SCIM) | **M** | MED | P1 -- blocks C-04 |
| **Frontend State** | SWR (per-hook data fetching, 30 hooks) | Zustand + SWR hybrid (global state + server cache) | **M** | LOW | P2 |
| **Container Orchestration** | Docker Compose (local dev) | Kubernetes (EKS) with Helm charts | **L** | MED | P2 |
| **CI/CD** | Not observed | GitHub Actions + ArgoCD | **M** | LOW | P2 |
| **Observability** | None observed | OpenTelemetry + Grafana + Loki | **M** | LOW | P3 |

---

## SECTION 3: REUSABLE ASSET INVENTORY

### Directly Reusable (copy + adapt)

| Asset | File/Location | Maps To | Adaptation Needed |
|---|---|---|---|
| `DetectionService` (8 rules, MITRE mapping) | `apps/api/app/services/detection_service.py` (746 lines) | A-06 CDR | Add CloudTrail streaming input, expand rule set from 8 to 50+, add SOAR triggers |
| `CanonicalFinding` model | `apps/api/app/models/canonical_finding.py` | A-01 CSPM | Migrate to PostgreSQL, add multi-cloud fields, add compliance_control FK |
| `SecurityGraphNode` model | `apps/api/app/models/security_graph_node.py` | B-01 GraphRAG | Schema concepts transfer to Neo4j node labels; SQLAlchemy code does not transfer |
| `SecurityGraphEdge` model | `apps/api/app/models/security_graph_edge.py` | B-01 GraphRAG | Edge types (PRIVILEGE_ESCALATION_PATH, ASSUMES_ROLE, HAS_POLICY) become Neo4j relationships |
| FastAPI app structure | `apps/api/app/main.py` | All backend | Router registration pattern, dependency injection, prefix conventions all reuse |
| Detection router pattern | `apps/api/app/routers/detections.py` | All routers | `Depends(get_current_user)` + `Depends(get_async_db)` + `_workspace_id()` pattern reuses across all 32+ routers |
| Risk score algorithm | `detection_service._risk_score()` | A-01, B-04 | Severity weight * confidence formula is a good base; needs factor expansion |
| KEV/CVE constants | `detection_service._KEV_SET`, `_CVE_RE` | A-08 Vulns | Static set needs live CISA KEV API feed; regex pattern reuses directly |
| MITRE ATT&CK mapping | `detection_service._MITRE` dict | A-06 CDR | 8 mappings need expansion to full ATT&CK matrix (~200 techniques) |
| Alert schema | `detection_service._alert()` helper | A-06 CDR | Standardized alert dict with id, rule_id, severity, confidence, affected_resources, evidence -- excellent base |

### Pattern-Reusable (architecture transfers, code rewrites)

| Pattern | Current Implementation | OmniSec Application |
|---|---|---|
| Workspace-scoped queries | `WHERE workspace_id = ?` on all models | PostgreSQL RLS policies replace query-level filtering |
| Async SQLAlchemy sessions | `AsyncSession` dependency injection | Same pattern with PostgreSQL async driver (asyncpg) |
| Deterministic ID generation | `hashlib.sha256(f"{rule_id}:{resource_arn}")` | Idempotent alert/finding IDs across all modules |
| Severity weight system | `_SEV_WEIGHT` dict (critical=1.0, high=0.75, medium=0.5, low=0.25) | Universal severity scoring across all A-* modules |
| CIEM priv-esc detection | 5 patterns in ciem_service | Expand to 20+ patterns with Neo4j graph traversal |
| CVE+EPSS+KEV correlation | vuln_service triple-source scoring | Feed into B-04 OASIS simulation inputs |

### Not Reusable (must build from scratch)

| Component | Reason |
|---|---|
| 15-Agent Swarm (B-03) | No agent framework, no LangChain/LangGraph, no tool-use patterns exist |
| GraphRAG (B-01) | SQLite graph is a flat table; Neo4j+vector embeddings+RAG is architecturally different |
| OASIS Simulation (B-04) | No simulation engine, no Monte Carlo, no scenario modeling |
| Zep Cloud Memory (B-05) | No memory management, no entity extraction, no temporal knowledge |
| DSPM (A-04) | No data classification, no Macie integration, no DLP |
| KSPM (A-05) | No Kubernetes code whatsoever |
| IaC Security (A-07) | No Terraform/CloudFormation parsing |
| ASM (A-10) | No external recon capability |
| Multi-Cloud (C-01) | AWS-only; each cloud is a ground-up effort |

---

## SECTION 4: BUILD ORDER & DEPENDENCY GRAPH

### Phase 0: Infrastructure Foundation (Weeks 1-4) -- MUST COMPLETE FIRST

```
P0-1: PostgreSQL migration (SQLite -> PG + RLS)
P0-2: Neo4j deployment + schema design
P0-3: Redis + Celery setup
P0-4: Kafka/EventBridge bus
P0-5: Auth0/Okta integration
```

**Blocks:** Everything in Modules A, B, C

### Phase 1: Core Platform (Weeks 5-12)

```
P1-1: A-01 CSPM (enhance existing) ------> depends on P0-1
P1-2: A-03 CIEM (enhance existing) ------> depends on P0-1, P0-2
P1-3: A-06 CDR (enhance existing) --------> depends on P0-1, P1-1
P1-4: B-01 GraphRAG + Neo4j -------------> depends on P0-2
P1-5: B-06 Communication Bus ------------> depends on P0-4
P1-6: C-04 Enterprise SSO ---------------> depends on P0-5
P1-7: C-06 Multi-Tenant Architecture ----> depends on P0-1
```

### Phase 2: Intelligence Layer (Weeks 13-20)

```
P2-1: A-08 Vuln Management (enhance) ----> depends on P1-1
P2-2: B-02 Agent Anatomy Engine ---------> depends on P0-3, P1-4
P2-3: B-05 Zep Cloud Memory ------------> depends on P2-2
P2-4: B-03 15-Agent Swarm (first 5) ----> depends on P2-2, P2-3, P1-5
P2-5: C-02 Compliance Automation --------> depends on P1-1
P2-6: C-05 Reporting Engine (enhance) ---> depends on P1-1
P2-7: A-02 CWPP --------------------------> depends on P1-1
```

### Phase 3: Advanced Capabilities (Weeks 21-30)

```
P3-1: B-03 15-Agent Swarm (remaining 10) -> depends on P2-4
P3-2: B-04 OASIS Simulation Engine -------> depends on P1-4, P3-1
P3-3: A-04 DSPM --------------------------> depends on P1-1, P1-2
P3-4: A-05 KSPM --------------------------> depends on P1-1, P2-7
P3-5: A-10 ASM ---------------------------> depends on P1-1, P1-2
P3-6: C-03 SOAR --------------------------> depends on P1-3, P1-5
```

### Phase 4: Expansion (Weeks 31-40)

```
P4-1: A-07 IaC & Code Security ----------> depends on P1-1
P4-2: A-09 AI-SPM -----------------------> depends on P3-1
P4-3: C-01 Multi-Cloud ------------------> depends on P1-1 (per-cloud: 8-12 weeks each)
P4-4: C-07 Developer Portal -------------> depends on C-04
```

---

## SECTION 5: EFFORT ESTIMATION SUMMARY

| Size | Definition | Estimated Weeks (2-person team) | Modules |
|---|---|---|---|
| **S** | Minor enhancement, <1 week | 0.5-1 | -- |
| **M** | Moderate feature, 1-3 weeks | 2-3 | C-04, C-05, C-07 |
| **L** | Major feature, 3-6 weeks | 4-6 | A-01, A-03, A-06, A-08, B-05, B-06, C-02, C-06 |
| **XL** | New domain, 6-12+ weeks | 8-12 | A-02, A-04, A-05, A-07, A-09, A-10, B-01, B-02, B-03, B-04, C-01, C-03 |

### Total Effort Estimate

| Category | Module Count | Avg Weeks | Total Person-Weeks |
|---|---|---|---|
| Infrastructure (P0) | 5 components | 3 | 30 |
| Module A (10 submodules) | 10 | 6 | 120 |
| Module B (6 submodules) | 6 | 9 | 108 |
| Module C (7 submodules) | 7 | 4 | 56 |
| **TOTAL** | **28** | -- | **~314 person-weeks** |

With a team of 6 engineers: **~52 weeks (12 months)** with parallelization.
With a team of 10 engineers: **~32 weeks (8 months)** with parallelization.

---

## SECTION 6: RISK REGISTER

| Risk ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-01 | **PostgreSQL migration breaks existing functionality** | HIGH | CRITICAL | Write migration scripts with rollback; run dual-write for 2 weeks; comprehensive integration tests |
| R-02 | **Neo4j learning curve delays B-01** | MED | HIGH | Hire/contract Neo4j specialist; use managed Neo4j Aura; prototype GraphRAG in isolation first |
| R-03 | **15-Agent Swarm complexity explosion** | HIGH | CRITICAL | Build agents incrementally (5 at a time); each agent must work standalone before swarm integration |
| R-04 | **Scope creep in Module A (10 submodules)** | HIGH | HIGH | Strict sprint boundaries; each submodule is a separate epic with acceptance criteria |
| R-05 | **Auth0/Okta migration breaks existing JWT flow** | MED | MED | Implement adapter pattern; support both JWT and OIDC during transition |
| R-06 | **GraphRAG quality insufficient for production** | MED | HIGH | Benchmark RAG accuracy early (week 8); have fallback to keyword search |
| R-07 | **Kafka operational overhead** | LOW | MED | Start with Redis Streams; migrate to Kafka only when throughput demands it |
| R-08 | **Multi-cloud (C-01) is bottomless pit** | HIGH | HIGH | Defer until Module A is complete for AWS; scope Azure first, GCP second |
| R-09 | **Frontend state migration (SWR to Zustand)** | LOW | LOW | Keep SWR for server cache; add Zustand only for global UI state; no big-bang rewrite |
| R-10 | **OASIS simulation accuracy** | MED | MED | Start with deterministic graph traversal (existing attack_path model); add Monte Carlo later |

---

## SECTION 7: CRITICAL PATH ANALYSIS

The **critical path** (longest dependency chain) is:

```
PostgreSQL Migration (4 wk)
  -> Neo4j Setup (2 wk)
    -> B-01 GraphRAG (10 wk)
      -> B-02 Agent Anatomy (8 wk)
        -> B-03 15-Agent Swarm (12 wk)
          -> B-04 OASIS Simulation (10 wk)
```

**Total critical path: ~46 weeks**

This means Module B is the schedule bottleneck. Module A and C can be parallelized alongside B, but B-04 (the capstone) cannot start until B-03 is functional.

### Schedule Compression Opportunities

1. **Start B-01 and A-01 in parallel** after P0 completes (saves 4 weeks)
2. **Build first 5 agents (B-03 partial) while B-02 stabilizes** (saves 4 weeks)
3. **Defer B-04 OASIS to Phase 3** and ship with graph-traversal attack paths from existing code (saves 10 weeks from critical path)
4. **Defer C-01 Multi-Cloud entirely** to post-launch (saves 12+ weeks)

With compression: **Critical path reduces to ~32 weeks.**

---

## SECTION 8: WHAT TO BUILD FIRST (Recommended Sprint Plan)

| Sprint | Duration | Focus | Deliverable |
|---|---|---|---|
| S1 | 2 weeks | PostgreSQL migration + Auth0 | All existing data on PG with RLS; OIDC login working |
| S2 | 2 weeks | Neo4j + Redis + Event Bus | Graph DB with migrated nodes/edges; Celery workers running; Kafka topics created |
| S3-S4 | 4 weeks | A-01 CSPM + A-06 CDR + C-06 Multi-Tenant | Enhanced CSPM with real policy engine; CDR with 20+ rules; tenant isolation verified |
| S5-S6 | 4 weeks | A-03 CIEM + A-08 Vulns + B-01 GraphRAG | Effective permissions engine; live EPSS/KEV feeds; Neo4j populated with GraphRAG |
| S7-S8 | 4 weeks | B-02 Agent Anatomy + B-05 Zep + B-06 Bus | Agent framework operational; memory layer connected; event bus flowing |
| S9-S12 | 8 weeks | B-03 Swarm (first 5 agents) + C-04 SSO + C-02 Compliance | Core agent swarm functional; enterprise auth; compliance automation |
| S13-S16 | 8 weeks | B-03 Swarm (remaining) + A-02 CWPP + C-05 Reporting | Full swarm; workload protection; analytics engine |
| S17-S20 | 8 weeks | B-04 OASIS + A-04 DSPM + A-05 KSPM + A-10 ASM | Simulation engine; new security domains |
| S21-S24 | 8 weeks | A-07 IaC + A-09 AI-SPM + C-03 SOAR + C-07 Portal | Code security; AI posture; orchestration; developer portal |
| S25+ | Ongoing | C-01 Multi-Cloud + hardening + scale testing | Azure, then GCP; performance optimization |

---

## SECTION 9: EXISTING FILE-TO-MODULE MAPPING

| Existing File | Lines | Module A | Module B | Module C | Reuse Action |
|---|---|---|---|---|---|
| `apps/api/app/main.py` | 27 | A-all | B-all | C-all | Expand with new router registrations |
| `apps/api/app/services/detection_service.py` | 746 | A-06 | -- | -- | Enhance: add streaming input, expand rules, add SOAR hooks |
| `apps/api/app/models/canonical_finding.py` | 65 | A-01 | B-01 | C-02 | Migrate to PG; add fields: `cve_id`, `compliance_control_id`, `cloud_provider` |
| `apps/api/app/models/security_graph_node.py` | 47 | A-03 | B-01 | -- | Schema concepts to Neo4j node labels; SQLAlchemy model retired |
| `apps/api/app/models/security_graph_edge.py` | 43 | A-03, A-06 | B-01 | -- | Edge types become Neo4j relationships; SQLAlchemy model retired |
| `apps/api/app/routers/detections.py` | 65 | A-06 | -- | -- | Keep pattern; add WebSocket endpoint, pagination, filtering |
| `apps/api/app/routers/__init__.py` | 1 | -- | -- | -- | Expand with all new router imports |
| `apps/api/app/integrations/aws/__init__.py` | -- | A-01 | -- | C-01 | Foundation for multi-cloud adapter pattern |
| `apps/api/app/services/__init__.py` | -- | -- | -- | -- | Service registration |
| `apps/api/app/models/__init__.py` | -- | -- | -- | -- | Model registration |

---

## SECTION 10: DECISION LOG

| Decision | Rationale | Impact |
|---|---|---|
| Migrate to PostgreSQL before any feature work | SQLite cannot support multi-tenant RLS, concurrent writes, or production scale | Blocks all work; 4-week investment pays for itself immediately |
| Keep FastAPI as backend framework | Proven async performance; existing patterns reuse; team familiarity | No rewrite cost for backend framework |
| Adopt Neo4j instead of enhancing SQLite graph | GraphRAG requires native graph traversal, vector indexes, and Cypher; SQL JOINs cannot match | Critical for B-01; means security_graph_node/edge models are retired |
| Build agents incrementally (5-5-5) | 15 agents simultaneously is unmanageable; each agent needs isolated testing | Reduces B-03 risk from CRITICAL to HIGH |
| Defer multi-cloud (C-01) to Phase 4 | Each cloud provider is 8-12 weeks; AWS-first strategy aligns with existing code | Removes 24+ weeks from initial timeline |
| Keep SWR for data fetching, add Zustand for global state | SWR handles server cache well; Zustand adds client state management without full rewrite | Minimal frontend disruption |
| Start with Redis Streams, not Kafka | Lower operational complexity for initial agent communication | Can upgrade to Kafka if throughput demands it |
