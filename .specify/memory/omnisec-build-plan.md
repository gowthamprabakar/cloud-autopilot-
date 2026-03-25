# OmniSec Enterprise Platform: Sprint-by-Sprint Build Plan

**Document Version:** 1.0
**Created:** 2026-03-25
**Scope:** Sprints 29-42 (v1.0 through v3.0) -- 28 weeks
**Baseline:** Cloud Copilot at Sprint 28 (11 source files, FastAPI + SQLAlchemy async, 4 routers, detection engine with 8 MITRE-mapped rules, canonical finding model, security graph nodes/edges)

---

## Existing Asset Inventory (Reuse Targets)

| Asset | Location | Reuse Strategy |
|---|---|---|
| CanonicalFinding ORM | `apps/api/app/models/canonical_finding.py` | Extend with swarm metadata fields; keep as base finding schema |
| SecurityGraphNode/Edge ORM | `apps/api/app/models/security_graph_*.py` | Extend for Neo4j dual-write; add agent_id attribution |
| DetectionService (8 rules, MITRE) | `apps/api/app/services/detection_service.py` | Wrap as SwarmDetectionAgent; rules become agent capabilities |
| CDR Router | `apps/api/app/routers/detections.py` | Keep as v1 endpoint; add v2 swarm-orchestrated routes alongside |
| FastAPI app + dependency injection | `apps/api/app/main.py` | Extend with middleware, new router registrations |
| Alert schema (_alert helper) | `detection_service.py` lines 123-153 | Standardize as SwarmAlert Pydantic model; reuse across all agents |
| MITRE mapping dict | `detection_service.py` lines 64-73 | Extract to shared `mitre_registry.py`; expand from 8 to 60+ techniques |
| Risk score calculation | `detection_service.py` lines 97-99 | Promote to shared scoring service; add EPSS/KEV weighting |
| AWS integration scaffold | `apps/api/app/integrations/aws/` | Extend with new service clients |

---

## Phase 1: Infrastructure Upgrade + v1.0 Swarm Autopsy Prototype

### Sprint 29: Infrastructure Foundation -- "Break Ground"
**Duration:** 2 weeks (Apr 7-18, 2026)
**Story Points:** 34

#### Deliverables

1. **PostgreSQL migration from SQLite**
   - Acceptance: All existing ORM models create tables in PostgreSQL; async connection pool via asyncpg; Alembic migration chain from empty DB; existing detection_service tests pass against PostgreSQL
   - Risk: Data type mismatches between SQLite JSON columns and PostgreSQL JSONB

2. **Redis + Celery task queue setup**
   - Acceptance: Celery worker starts, processes a test task, and stores result in Redis; health endpoint reports Redis/Celery status
   - Risk: Celery async integration with FastAPI event loop

3. **Docker Compose development environment**
   - Acceptance: `docker compose up` starts PostgreSQL, Redis, Celery worker, and FastAPI app; all services healthy within 60 seconds

4. **Configuration management overhaul**
   - Acceptance: All secrets loaded from environment variables via Pydantic Settings; no hardcoded values; `.env.example` documents all required vars

#### Backend Files

| Action | File | Description |
|---|---|---|
| CREATE | `apps/api/app/core/config.py` | Pydantic BaseSettings for all env vars |
| CREATE | `apps/api/app/core/database.py` | AsyncSession factory, engine creation, connection pool config |
| CREATE | `apps/api/app/core/redis.py` | Redis connection manager |
| CREATE | `apps/api/app/core/celery_app.py` | Celery application factory with Redis broker |
| CREATE | `apps/api/alembic/` | Alembic migration directory + env.py |
| CREATE | `apps/api/alembic/versions/001_initial_schema.py` | Initial migration from existing ORM models |
| MODIFY | `apps/api/app/main.py` | Add lifespan handler for DB pool; register health router |
| MODIFY | `apps/api/app/models/canonical_finding.py` | Switch `Base` to shared declarative base; add JSONB type for PostgreSQL |
| CREATE | `apps/api/app/routers/health.py` | `/api/v1/health` with DB, Redis, Celery checks |
| CREATE | `docker-compose.yml` | PostgreSQL 16, Redis 7, Celery worker, FastAPI app |
| CREATE | `apps/api/app/dependencies.py` | Formalize get_async_db, get_current_user (currently implied by imports) |

#### Frontend Pages/Components
- None this sprint (infrastructure only)

#### Infrastructure Changes
- PostgreSQL 16 container (port 5432)
- Redis 7 container (port 6379)
- Celery worker container (same image, different entrypoint)
- Alembic migration tooling

#### Dependencies
- None (first sprint of the phase)

#### Risk Items
- SQLAlchemy async driver (asyncpg) compatibility with existing query patterns in detection_service.py
- Celery 5.x + asyncio interop requires careful bridge code (sync_to_async wrappers)
- Existing `get_async_db` dependency in detections.py router must remain backward-compatible

---

### Sprint 30: Swarm Agent Framework Core -- "First Heartbeat"
**Duration:** 2 weeks (Apr 21 - May 2, 2026)
**Story Points:** 40

#### Deliverables

1. **Base Agent abstract class + agent registry**
   - Acceptance: `BaseAgent` defines lifecycle (init, analyze, report); AgentRegistry discovers and loads agents by name; at least 2 concrete agents registered

2. **SwarmOrchestrator service (sequential execution)**
   - Acceptance: Orchestrator accepts a workspace_id + agent list, runs agents sequentially, collects results into a unified SwarmReport; report includes per-agent timing and findings count

3. **Claude API integration (replaces Ollama for Swarm)**
   - Acceptance: ClaudeProvider class wraps Anthropic SDK; supports structured output via tool_use; configurable model selection (claude-sonnet-4, claude-opus-4); retry with exponential backoff

4. **DetectionAgent -- wrap existing DetectionService as first agent**
   - Acceptance: DetectionAgent extends BaseAgent; calls existing DetectionService.alerts(); output conforms to SwarmFinding schema; zero behavior regression on detection rules

5. **SwarmFinding + SwarmReport Pydantic models**
   - Acceptance: SwarmFinding captures agent_id, finding_type, severity, MITRE mapping, evidence, confidence, raw_data; SwarmReport aggregates findings with execution metadata

#### Backend Files

| Action | File | Description |
|---|---|---|
| CREATE | `apps/api/app/swarm/__init__.py` | Swarm package init |
| CREATE | `apps/api/app/swarm/base_agent.py` | ABC: BaseAgent with analyze(), get_capabilities(), health_check() |
| CREATE | `apps/api/app/swarm/registry.py` | AgentRegistry: register, discover, instantiate agents |
| CREATE | `apps/api/app/swarm/orchestrator.py` | SwarmOrchestrator: sequential agent execution, result aggregation |
| CREATE | `apps/api/app/swarm/models.py` | SwarmFinding, SwarmReport, AgentCapability, ExecutionContext Pydantic models |
| CREATE | `apps/api/app/swarm/providers/__init__.py` | LLM provider package |
| CREATE | `apps/api/app/swarm/providers/claude.py` | ClaudeProvider: Anthropic SDK wrapper with structured output |
| CREATE | `apps/api/app/swarm/agents/__init__.py` | Agents package |
| CREATE | `apps/api/app/swarm/agents/detection_agent.py` | Wraps existing DetectionService as BaseAgent |
| CREATE | `apps/api/app/routers/swarm.py` | `/api/v1/swarm/run`, `/api/v1/swarm/agents`, `/api/v1/swarm/status` |
| MODIFY | `apps/api/app/main.py` | Register swarm router |
| CREATE | `apps/api/app/swarm/prompts/__init__.py` | Prompt template registry |
| CREATE | `apps/api/app/swarm/prompts/detection.py` | Claude prompt templates for detection analysis |

#### Frontend Pages/Components
- None this sprint (API foundation)

#### Infrastructure Changes
- Anthropic API key added to config.py environment variables
- New `/api/v1/swarm/*` route group

#### Dependencies
- Sprint 29 (PostgreSQL, Redis, Celery)

#### Risk Items
- Claude API rate limits may constrain throughput during batch analysis
- Agent lifecycle management needs careful error isolation (one agent failure must not crash the swarm)
- Prompt engineering for Claude structured output requires iteration

---

### Sprint 31: Gap Domain Agents (Batch 1) -- "The First Six"
**Duration:** 2 weeks (May 5-16, 2026)
**Story Points:** 42

#### Deliverables

1. **QuantumReadinessAgent**
   - Acceptance: Scans findings for cryptographic weaknesses (RSA < 3072, SHA-1, non-PQC algorithms); produces SwarmFindings with quantum risk scores; maps to custom MITRE sub-technique

2. **SupplyChainAgent**
   - Acceptance: Analyzes dependency-related findings (ECR image vulns, Lambda layer risks, S3 artifact integrity); produces supply chain risk assessment per resource

3. **AIAgentSecurityAgent (AI-SPM)**
   - Acceptance: Detects SageMaker/Bedrock misconfigurations from findings; identifies exposed model endpoints, overprivileged ML roles; maps to OWASP ML Top 10

4. **LLMjackingAgent**
   - Acceptance: Identifies LLM API abuse vectors (exposed API keys, unrestricted Bedrock model access, prompt injection surfaces); produces LLMjacking risk findings

5. **FederatedIdentityAgent**
   - Acceptance: Analyzes SAML/OIDC trust configurations from IAM findings; detects overprivileged federation, missing MFA on IdP trust; extends existing identity_gap_exposure rule

6. **DeepfakeDetectionAgent**
   - Acceptance: Flags resources involved in media processing pipelines (Rekognition, Transcribe, MediaConvert) that lack integrity controls; assesses deepfake attack surface

7. **Gap domain prompt templates for all 6 agents**
   - Acceptance: Each agent has a Claude prompt template that produces structured SwarmFinding output; templates stored in swarm/prompts/

#### Backend Files

| Action | File | Description |
|---|---|---|
| CREATE | `apps/api/app/swarm/agents/quantum_readiness.py` | QuantumReadinessAgent |
| CREATE | `apps/api/app/swarm/agents/supply_chain.py` | SupplyChainAgent |
| CREATE | `apps/api/app/swarm/agents/ai_agent_security.py` | AIAgentSecurityAgent |
| CREATE | `apps/api/app/swarm/agents/llmjacking.py` | LLMjackingAgent |
| CREATE | `apps/api/app/swarm/agents/federated_identity.py` | FederatedIdentityAgent |
| CREATE | `apps/api/app/swarm/agents/deepfake_detection.py` | DeepfakeDetectionAgent |
| CREATE | `apps/api/app/swarm/prompts/quantum.py` | Quantum readiness prompt templates |
| CREATE | `apps/api/app/swarm/prompts/supply_chain.py` | Supply chain prompt templates |
| CREATE | `apps/api/app/swarm/prompts/ai_security.py` | AI/ML security prompt templates |
| CREATE | `apps/api/app/swarm/prompts/llmjacking.py` | LLMjacking prompt templates |
| CREATE | `apps/api/app/swarm/prompts/federated_identity.py` | Federated identity prompt templates |
| CREATE | `apps/api/app/swarm/prompts/deepfake.py` | Deepfake detection prompt templates |
| CREATE | `apps/api/app/swarm/agents/gap_base.py` | Shared base class for gap domain agents with common finding-scan patterns |
| MODIFY | `apps/api/app/swarm/registry.py` | Auto-register all 6 gap agents |
| CREATE | `apps/api/app/swarm/mitre_registry.py` | Extracted from detection_service.py; expanded to 30+ techniques for gap domains |

#### Frontend Pages/Components
- None this sprint

#### Infrastructure Changes
- None (uses existing Claude API + PostgreSQL)

#### Dependencies
- Sprint 30 (BaseAgent, SwarmOrchestrator, ClaudeProvider)

#### Risk Items
- Quantum readiness heuristics are pattern-based (no actual crypto audit); must clearly label as "assessment" not "audit"
- AI-SPM detection depends on finding titles/descriptions containing SageMaker/Bedrock keywords; may miss custom-named resources
- 6 agents calling Claude API sequentially may exceed 60s request timeout; need Celery offload for batch runs

---

### Sprint 32: 12-Gate Validation + Swarm Autopsy MVP -- "Quality Gate"
**Duration:** 2 weeks (May 19-30, 2026)
**Story Points:** 44

#### Deliverables

1. **12-Gate Validation Framework**
   - Acceptance: Each SwarmFinding passes through 12 validation gates before inclusion in SwarmReport; gates include: (1) Schema Conformance, (2) MITRE Mapping Valid, (3) Severity Justified, (4) Evidence Present, (5) Resource ARN Valid, (6) Confidence Threshold Met, (7) Deduplication Check, (8) Cross-Agent Consistency, (9) False Positive Filter, (10) SLA Classification, (11) Remediation Present, (12) Compliance Mapping; gate results stored per finding

2. **Swarm Autopsy Report Generator**
   - Acceptance: POST `/api/v1/swarm/autopsy` runs all registered agents, applies 12-gate validation, and produces a structured autopsy report with: executive summary (Claude-generated), per-agent findings, validation gate pass/fail matrix, cross-domain correlation insights, remediation priority list; report persisted to DB

3. **Celery async swarm execution**
   - Acceptance: Swarm runs dispatched to Celery; status queryable via GET `/api/v1/swarm/status/{task_id}`; results stored in PostgreSQL on completion

4. **Gap domain agents batch 2: OT/ICS, PrivacyShield, DriftDetection**
   - Acceptance: Three additional gap agents registered; total of 9 gap domain agents + 1 detection agent = 10 agents in registry; OT/ICS scans for industrial protocol exposure; PrivacyShield checks data residency and PII exposure; DriftDetection compares current state against baseline

#### Backend Files

| Action | File | Description |
|---|---|---|
| CREATE | `apps/api/app/swarm/validation/__init__.py` | Validation package |
| CREATE | `apps/api/app/swarm/validation/gates.py` | 12 gate validator functions |
| CREATE | `apps/api/app/swarm/validation/pipeline.py` | ValidationPipeline: runs finding through all 12 gates, collects results |
| CREATE | `apps/api/app/swarm/autopsy.py` | SwarmAutopsy: orchestrate full autopsy run, generate report |
| CREATE | `apps/api/app/swarm/report_generator.py` | Claude-powered executive summary + report assembly |
| CREATE | `apps/api/app/models/swarm_run.py` | SwarmRun ORM: id, workspace_id, status, agent_list, started_at, completed_at, report_json |
| CREATE | `apps/api/app/models/swarm_finding_record.py` | SwarmFindingRecord ORM: persisted swarm findings with gate results |
| CREATE | `apps/api/app/swarm/tasks.py` | Celery tasks: run_swarm_autopsy, run_single_agent |
| CREATE | `apps/api/app/swarm/agents/ot_ics.py` | OT/ICS security agent |
| CREATE | `apps/api/app/swarm/agents/privacy_shield.py` | Privacy and data residency agent |
| CREATE | `apps/api/app/swarm/agents/drift_detection.py` | Configuration drift detection agent |
| CREATE | `apps/api/app/swarm/prompts/ot_ics.py` | OT/ICS prompt templates |
| CREATE | `apps/api/app/swarm/prompts/privacy.py` | Privacy prompt templates |
| CREATE | `apps/api/app/swarm/prompts/drift.py` | Drift detection prompt templates |
| MODIFY | `apps/api/app/routers/swarm.py` | Add `/swarm/autopsy`, `/swarm/status/{task_id}` endpoints |
| MODIFY | `apps/api/app/swarm/orchestrator.py` | Add Celery dispatch mode alongside sequential |
| CREATE | `apps/api/alembic/versions/002_swarm_tables.py` | Migration for swarm_runs and swarm_finding_records tables |

#### Frontend Pages/Components
- None this sprint (API-only v1.0 milestone)

#### Infrastructure Changes
- Celery beat scheduler for recurring autopsy scans (optional cron)
- New DB tables: swarm_runs, swarm_finding_records

#### Dependencies
- Sprint 29 (PostgreSQL, Celery)
- Sprint 30 (BaseAgent, Orchestrator, Claude)
- Sprint 31 (6 gap agents)

#### Risk Items
- 12-gate validation may be too strict initially, filtering out valid findings; need tunable thresholds per gate
- Full autopsy with 10 agents + Claude API calls may take 2-5 minutes; Celery timeout must accommodate
- Report generator Claude prompt needs careful engineering to avoid hallucinated findings

#### Milestone: v1.0 Swarm Autopsy Prototype Complete
- 10 registered agents (1 detection + 9 gap domain)
- 12-gate validation framework
- Async execution via Celery
- Persisted autopsy reports in PostgreSQL
- Claude-powered executive summary generation

---

## Phase 2: Module A (Wiz CNAPP Simulation) + Module B (Swarm Engine)

### Sprint 33: Wiz CNAPP Simulation Agents (CSPM + CIEM) -- "Mirror Start"
**Duration:** 2 weeks (Jun 1-12, 2026)
**Story Points:** 38

#### Deliverables

1. **CSPMSimulationAgent**
   - Acceptance: Simulates Wiz CSPM posture assessment; evaluates findings against CIS AWS Foundations Benchmark controls (top 50 controls); produces compliance posture score per control; outputs SwarmFindings for each failed control

2. **CIEMSimulationAgent**
   - Acceptance: Simulates Wiz CIEM effective permissions analysis; analyzes SecurityGraphNode IAM entities for over-privilege, unused permissions (heuristic based on last_activity_at), cross-account trust; extends existing rule_privilege_escalation_critical_iam and rule_identity_gap_exposure patterns from detection_service.py

3. **Compliance control library (CIS AWS v3.0 top 50)**
   - Acceptance: JSON schema defining 50 CIS controls with id, title, description, finding_patterns, severity, remediation; queryable by control ID

4. **IAM effective permissions model**
   - Acceptance: New ORM model for IAM entity effective permissions; fields: entity_arn, permissions_json, boundary_arn, scp_restrictions, effective_admin (bool), last_used_at; populated by CIEMSimulationAgent

#### Backend Files

| Action | File | Description |
|---|---|---|
| CREATE | `apps/api/app/swarm/agents/cspm_simulation.py` | CSPMSimulationAgent |
| CREATE | `apps/api/app/swarm/agents/ciem_simulation.py` | CIEMSimulationAgent |
| CREATE | `apps/api/app/swarm/prompts/cspm.py` | CSPM prompt templates |
| CREATE | `apps/api/app/swarm/prompts/ciem.py` | CIEM prompt templates |
| CREATE | `apps/api/app/data/cis_aws_v3_controls.json` | CIS AWS Foundations Benchmark top 50 controls |
| CREATE | `apps/api/app/models/compliance_control.py` | ComplianceControl ORM model |
| CREATE | `apps/api/app/models/iam_effective_permissions.py` | IAMEffectivePermissions ORM model |
| CREATE | `apps/api/app/services/compliance_service.py` | ComplianceService: evaluate findings against control library |
| MODIFY | `apps/api/app/swarm/mitre_registry.py` | Add CIEM-specific MITRE techniques (T1078.004, T1548, T1098) |
| CREATE | `apps/api/alembic/versions/003_compliance_iam_tables.py` | Migration for compliance_controls and iam_effective_permissions |

#### Frontend Pages/Components
- None this sprint

#### Infrastructure Changes
- New DB tables: compliance_controls, iam_effective_permissions

#### Dependencies
- Sprint 30 (BaseAgent framework)
- Sprint 32 (12-gate validation for finding quality)

#### Risk Items
- CIS control matching is pattern-based; real compliance requires actual AWS Config rule evaluation
- IAM effective permissions without real CloudTrail data are estimates; must label as "simulated"

---

### Sprint 34: Wiz CNAPP Simulation Agents (Vulns + DSPM + CDR) -- "Mirror Expand"
**Duration:** 2 weeks (Jun 15-26, 2026)
**Story Points:** 40

#### Deliverables

1. **VulnSimulationAgent**
   - Acceptance: Simulates Wiz vulnerability management; enriches CVE-containing findings with EPSS scores (from local EPSS CSV cache), KEV status (extends existing _KEV_SET from detection_service.py), and exploitability rating; produces prioritized patch queue

2. **DSPMSimulationAgent**
   - Acceptance: Simulates Wiz DSPM data security posture; identifies data stores (S3, RDS, DynamoDB) from findings and graph nodes; classifies as public/encrypted/contains-PII based on finding patterns; produces data exposure risk score per resource

3. **CDRSimulationAgent**
   - Acceptance: Extends existing DetectionService with simulated runtime detection; adds 12 new detection rules beyond the existing 8 (total 20); rules cover MITRE techniques T1562.008, T1136.003, T1098.001, T1552.001, T1530; all rules produce SwarmFindings via 12-gate validation

4. **EPSS data loader (batch Celery task)**
   - Acceptance: Celery task downloads EPSS CSV from first.org, parses into epss_scores table; refreshed daily; provides lookup by CVE ID

5. **KEV data loader (batch Celery task)**
   - Acceptance: Celery task downloads CISA KEV JSON catalog, parses into kev_entries table; refreshed daily; replaces hardcoded _KEV_SET in detection_service.py

#### Backend Files

| Action | File | Description |
|---|---|---|
| CREATE | `apps/api/app/swarm/agents/vuln_simulation.py` | VulnSimulationAgent |
| CREATE | `apps/api/app/swarm/agents/dspm_simulation.py` | DSPMSimulationAgent |
| CREATE | `apps/api/app/swarm/agents/cdr_simulation.py` | CDRSimulationAgent extending DetectionService |
| CREATE | `apps/api/app/swarm/prompts/vuln.py` | Vulnerability analysis prompt templates |
| CREATE | `apps/api/app/swarm/prompts/dspm.py` | DSPM prompt templates |
| CREATE | `apps/api/app/swarm/prompts/cdr.py` | CDR prompt templates |
| CREATE | `apps/api/app/models/epss_score.py` | EPSSScore ORM: cve_id, epss, percentile, updated_at |
| CREATE | `apps/api/app/models/kev_entry.py` | KEVEntry ORM: cve_id, vendor, product, date_added, due_date |
| CREATE | `apps/api/app/services/vuln_enrichment_service.py` | EPSS + KEV lookup service |
| CREATE | `apps/api/app/swarm/tasks_data.py` | Celery tasks: refresh_epss_data, refresh_kev_data |
| MODIFY | `apps/api/app/services/detection_service.py` | Replace hardcoded _KEV_SET with DB lookup; add 12 new detection rules |
| CREATE | `apps/api/alembic/versions/004_vuln_enrichment_tables.py` | Migration for epss_scores and kev_entries tables |

#### Frontend Pages/Components
- None this sprint

#### Infrastructure Changes
- Celery beat schedule: EPSS refresh daily at 02:00 UTC, KEV refresh daily at 02:15 UTC
- New DB tables: epss_scores, kev_entries

#### Dependencies
- Sprint 29 (Celery for async tasks)
- Sprint 30 (BaseAgent, ClaudeProvider)
- Sprint 33 (ComplianceControl model for cross-referencing)

#### Risk Items
- EPSS CSV download may fail; need fallback to cached data
- Expanding detection_service.py from 8 to 20 rules is a large change; needs comprehensive test coverage
- DSPM without real data classification is heuristic-only; clearly scope as "simulation"

---

### Sprint 35: Wiz CNAPP Simulation Agents (Attack Path + Code + Container) -- "Mirror Complete"
**Duration:** 2 weeks (Jun 29 - Jul 10, 2026)
**Story Points:** 42

#### Deliverables

1. **AttackPathSimulationAgent**
   - Acceptance: Simulates Wiz attack path analysis; traverses SecurityGraphNode/Edge to find multi-hop paths from internet-facing to sensitive data; scores paths by severity chain; produces attack path SwarmFindings with hop-by-hop evidence; reuses and extends existing rule_admin_entity_internet_facing pattern

2. **CodeSecuritySimulationAgent**
   - Acceptance: Simulates Wiz code security scanning; analyzes findings for IaC misconfiguration patterns, hardcoded secrets patterns, and dependency vulnerability patterns; produces code-to-cloud linkage findings

3. **ContainerSecuritySimulationAgent**
   - Acceptance: Simulates Wiz container scanning; identifies container-related findings (ECR, ECS, EKS, Lambda); assesses image vulnerability, runtime config, and network exposure; produces container risk findings

4. **KubernetesSimulationAgent**
   - Acceptance: Identifies EKS-related findings and graph nodes; assesses RBAC misconfigurations, pod security policy gaps, network policy absence; produces Kubernetes-specific findings

5. **CloudEntitlementAgent**
   - Acceptance: Combines CIEM with cloud entitlement optimization; identifies service accounts with admin access, cross-service role chaining, and entitlement sprawl

#### Backend Files

| Action | File | Description |
|---|---|---|
| CREATE | `apps/api/app/swarm/agents/attack_path_simulation.py` | AttackPathSimulationAgent |
| CREATE | `apps/api/app/swarm/agents/code_security_simulation.py` | CodeSecuritySimulationAgent |
| CREATE | `apps/api/app/swarm/agents/container_security.py` | ContainerSecuritySimulationAgent |
| CREATE | `apps/api/app/swarm/agents/kubernetes_simulation.py` | KubernetesSimulationAgent |
| CREATE | `apps/api/app/swarm/agents/cloud_entitlement.py` | CloudEntitlementAgent |
| CREATE | `apps/api/app/swarm/prompts/attack_path.py` | Attack path prompt templates |
| CREATE | `apps/api/app/swarm/prompts/code_security.py` | Code security prompt templates |
| CREATE | `apps/api/app/swarm/prompts/container.py` | Container security prompt templates |
| CREATE | `apps/api/app/swarm/prompts/kubernetes.py` | Kubernetes prompt templates |
| CREATE | `apps/api/app/swarm/prompts/entitlement.py` | Entitlement prompt templates |
| CREATE | `apps/api/app/services/graph_traversal_service.py` | Graph path-finding algorithms (BFS/DFS for attack paths) |
| MODIFY | `apps/api/app/swarm/registry.py` | Register all 5 new agents; total now: 15 agents |
| MODIFY | `apps/api/app/models/security_graph_edge.py` | Add edge_weight, attack_path_relevant (bool) fields |

#### Frontend Pages/Components
- None this sprint

#### Infrastructure Changes
- None beyond existing stack

#### Dependencies
- Sprint 30 (BaseAgent)
- Sprint 33 (CIEMSimulationAgent for entitlement base)
- Sprint 34 (VulnSimulationAgent for CVE data in attack paths)

#### Risk Items
- Graph traversal on large graphs may be slow without Neo4j; SQLAlchemy-based traversal is O(n*m) on edges
- Attack path scoring is novel; no established industry standard for path risk calculation
- 15 agents total may strain Claude API costs; implement agent result caching

---

### Sprint 36: Swarm Engine -- Context Chaining + Memory -- "The Brain"
**Duration:** 2 weeks (Jul 13-24, 2026)
**Story Points:** 44

#### Deliverables

1. **Zep Cloud memory integration**
   - Acceptance: Each swarm run creates a Zep session; agent findings stored as Zep memories with metadata tags; subsequent runs retrieve relevant prior memories for context enrichment; memory search by semantic similarity returns top-K relevant findings from prior runs

2. **Context chaining between agents**
   - Acceptance: SwarmOrchestrator passes output of Agent N as input context to Agent N+1; chain order configurable per autopsy profile; DetectionAgent output feeds VulnAgent feeds AttackPathAgent; context window managed to stay within Claude token limits

3. **Agent communication protocol**
   - Acceptance: Agents can publish "signals" (typed messages) to a shared context bus; other agents subscribe to signal types; e.g., DetectionAgent publishes "KEV_FOUND" signal, VulnSimulationAgent subscribes and enriches

4. **Swarm execution profiles**
   - Acceptance: Profiles define which agents run, in what order, with what context chain; "quick" profile: 5 core agents in 60s; "full" profile: all 15 agents in 5min; "gap-only" profile: 9 gap agents; profiles stored in DB and editable via API

#### Backend Files

| Action | File | Description |
|---|---|---|
| CREATE | `apps/api/app/swarm/memory/__init__.py` | Memory package |
| CREATE | `apps/api/app/swarm/memory/zep_client.py` | Zep Cloud SDK wrapper: create session, add memory, search |
| CREATE | `apps/api/app/swarm/memory/context_manager.py` | Manages context window for agent chains; truncation strategy |
| CREATE | `apps/api/app/swarm/context_bus.py` | Signal-based inter-agent communication bus |
| CREATE | `apps/api/app/swarm/chain.py` | Context chaining logic: output-to-input pipeline |
| CREATE | `apps/api/app/models/swarm_profile.py` | SwarmProfile ORM: name, agent_list, chain_order, max_duration |
| MODIFY | `apps/api/app/swarm/orchestrator.py` | Add context chaining mode, memory retrieval, signal dispatch |
| MODIFY | `apps/api/app/swarm/base_agent.py` | Add receive_context(), publish_signal() methods |
| CREATE | `apps/api/app/routers/swarm_profiles.py` | CRUD endpoints for swarm execution profiles |
| MODIFY | `apps/api/app/main.py` | Register swarm_profiles router |
| CREATE | `apps/api/alembic/versions/005_swarm_profiles.py` | Migration for swarm_profiles table |

#### Frontend Pages/Components
- None this sprint

#### Infrastructure Changes
- Zep Cloud API key added to environment config
- New DB table: swarm_profiles

#### Dependencies
- Sprint 30 (Orchestrator, BaseAgent)
- Sprint 32 (Celery async execution)
- Sprint 35 (all 15 agents registered)

#### Risk Items
- Zep Cloud latency may add 200-500ms per memory operation; batch memory writes
- Context window management is critical; 15 agents producing 50 findings each = massive context
- Signal bus ordering may create race conditions in parallel execution mode

---

### Sprint 37: GraphRAG + Neo4j Integration -- "The Graph Brain"
**Duration:** 2 weeks (Jul 27 - Aug 7, 2026)
**Story Points:** 46

#### Deliverables

1. **Neo4j graph database integration**
   - Acceptance: All SecurityGraphNode and SecurityGraphEdge data dual-written to Neo4j; Cypher queries for attack path traversal replace BFS/DFS from Sprint 35; sub-100ms query time for 3-hop paths on 10K node graphs

2. **GraphRAG retrieval service**
   - Acceptance: Given a SwarmFinding, retrieve related graph context (2-hop neighborhood) from Neo4j; format as structured context for Claude prompts; GraphRAG enhances agent analysis with topological awareness

3. **Attack path computation via Cypher**
   - Acceptance: AttackPathSimulationAgent uses Cypher shortest-path queries instead of Python traversal; supports weighted paths by severity; returns all paths from internet-facing nodes to sensitive data nodes

4. **Graph-aware Claude prompts**
   - Acceptance: SwarmFinding analysis prompts include graph neighborhood context; Claude receives node properties, edge types, and path information; finding quality improves measurably (gate pass rate increases)

#### Backend Files

| Action | File | Description |
|---|---|---|
| CREATE | `apps/api/app/core/neo4j.py` | Neo4j driver connection manager (async bolt) |
| CREATE | `apps/api/app/services/graph_service.py` | Neo4j-backed graph CRUD (replace/supplement SQLAlchemy graph queries) |
| CREATE | `apps/api/app/swarm/graphrag/__init__.py` | GraphRAG package |
| CREATE | `apps/api/app/swarm/graphrag/retriever.py` | GraphRAG retriever: query Neo4j for context around a finding |
| CREATE | `apps/api/app/swarm/graphrag/formatter.py` | Format graph context for Claude prompt injection |
| MODIFY | `apps/api/app/swarm/agents/attack_path_simulation.py` | Use Cypher queries via graph_service instead of Python traversal |
| MODIFY | `apps/api/app/swarm/providers/claude.py` | Accept graph_context parameter in prompt construction |
| MODIFY | `apps/api/app/swarm/orchestrator.py` | Inject GraphRAG context into agent execution pipeline |
| CREATE | `apps/api/app/services/graph_sync_service.py` | Dual-write sync: PostgreSQL SecurityGraph* tables <-> Neo4j |
| MODIFY | `docker-compose.yml` | Add Neo4j 5.x container |

#### Frontend Pages/Components
- None this sprint

#### Infrastructure Changes
- Neo4j 5.x container (ports 7474/7687)
- Neo4j Bolt driver dependency (neo4j-python-driver)
- Dual-write middleware for graph data

#### Dependencies
- Sprint 29 (Docker Compose)
- Sprint 35 (AttackPathSimulationAgent, graph_traversal_service)
- Sprint 36 (Context chaining for GraphRAG injection)

#### Risk Items
- Neo4j + PostgreSQL dual-write adds consistency risk; implement eventual consistency with retry
- Neo4j licensing: Community Edition is AGPL (free); Enterprise requires license for production
- GraphRAG context can be very large for densely connected nodes; implement context budget per agent

---

### Sprint 38: Parallel Execution + Kafka Event Bus -- "Scale Up"
**Duration:** 2 weeks (Aug 10-21, 2026)
**Story Points:** 40

#### Deliverables

1. **Parallel agent execution in SwarmOrchestrator**
   - Acceptance: Agents without dependency chains run in parallel via Celery group(); execution time for "full" profile drops from 5min sequential to under 2min parallel; results merged in correct order

2. **Kafka event streaming**
   - Acceptance: All swarm events (agent_started, finding_produced, gate_passed, gate_failed, run_completed) published to Kafka topics; consumer writes events to swarm_events table for audit; external systems can subscribe to Kafka topics

3. **Agent result caching (Redis)**
   - Acceptance: Agent results cached in Redis with workspace_id + agent_id + data_hash as key; TTL configurable per agent (default 1 hour); cache hit skips Claude API call; cache invalidated on new finding ingestion

4. **Rate limiter for Claude API**
   - Acceptance: Token bucket rate limiter in ClaudeProvider; configurable requests-per-minute and tokens-per-minute limits; queues excess requests; logs rate limit events

5. **Swarm metrics and observability**
   - Acceptance: Prometheus metrics exported: agent_execution_seconds, findings_produced_total, gate_pass_rate, cache_hit_rate, claude_api_latency; `/metrics` endpoint exposed

#### Backend Files

| Action | File | Description |
|---|---|---|
| MODIFY | `apps/api/app/swarm/orchestrator.py` | Add parallel execution via Celery chord/group |
| CREATE | `apps/api/app/core/kafka.py` | Kafka producer/consumer connection manager |
| CREATE | `apps/api/app/swarm/events.py` | SwarmEvent Pydantic models, Kafka publisher |
| CREATE | `apps/api/app/swarm/event_consumer.py` | Kafka consumer: writes swarm events to DB |
| CREATE | `apps/api/app/swarm/cache.py` | Redis-backed agent result cache |
| MODIFY | `apps/api/app/swarm/providers/claude.py` | Add token bucket rate limiter |
| CREATE | `apps/api/app/core/metrics.py` | Prometheus metrics definitions |
| CREATE | `apps/api/app/routers/metrics.py` | `/metrics` endpoint for Prometheus scraping |
| CREATE | `apps/api/app/models/swarm_event.py` | SwarmEvent ORM for audit trail |
| MODIFY | `apps/api/app/main.py` | Register metrics router |
| MODIFY | `docker-compose.yml` | Add Kafka + Zookeeper containers |
| CREATE | `apps/api/alembic/versions/006_swarm_events.py` | Migration for swarm_events table |

#### Frontend Pages/Components
- None this sprint

#### Infrastructure Changes
- Apache Kafka container + Zookeeper (or KRaft mode)
- Kafka topics: swarm.events, swarm.findings, swarm.status
- Prometheus metrics endpoint

#### Dependencies
- Sprint 29 (Redis, Celery)
- Sprint 36 (Context chaining -- needed for parallel dependency resolution)
- Sprint 37 (Neo4j -- GraphRAG queries must be thread-safe)

#### Risk Items
- Parallel Celery execution with shared Neo4j/PostgreSQL connections needs connection pool sizing
- Kafka adds operational complexity; consider starting with Redis Streams as simpler alternative
- Prometheus metrics cardinality explosion if per-agent labels not bounded

#### Milestone: v2.0 Complete
- 15 agents with parallel execution
- 17 analysis domains (10 Wiz CNAPP + 9 gap domains, some overlap)
- Context chaining + Zep memory
- GraphRAG via Neo4j
- Kafka event streaming
- Redis caching + rate limiting
- Full observability stack

---

## Phase 3: Module C (Gap Domains) + 12-Gate Hardening + Frontend

### Sprint 39: React SPA -- Dashboard + Swarm Control Center -- "The Face"
**Duration:** 2 weeks (Aug 24 - Sep 4, 2026)
**Story Points:** 42

#### Deliverables

1. **Next.js app scaffolding for OmniSec**
   - Acceptance: New `/app/dashboard` route group with layout; shared shell components (sidebar nav, header, breadcrumbs); shadcn/ui component library integrated; dark mode support

2. **Swarm Control Center page**
   - Acceptance: Dashboard page showing: registered agents (name, status, last run, capabilities); swarm execution profiles; trigger autopsy run button; active run status with real-time progress (SSE or polling)

3. **Autopsy Report Viewer page**
   - Acceptance: View completed autopsy report; executive summary section; per-agent finding list with severity badges; 12-gate validation matrix (pass/fail per finding per gate); finding detail drawer with evidence, MITRE mapping, remediation

4. **Findings Explorer page (enhanced)**
   - Acceptance: Paginated findings table with filters (severity, agent, gate status, MITRE tactic); sorting by risk_score, confidence, detected_at; bulk actions (suppress, acknowledge); CSV export

5. **API client hooks**
   - Acceptance: React hooks for all swarm API endpoints: useSwarmRun, useSwarmStatus, useAgents, useAutopsyReport, useSwarmFindings; SWR-based with automatic revalidation

#### Frontend Pages/Components

| Action | File | Description |
|---|---|---|
| CREATE | `apps/web/app/dashboard/layout.tsx` | Dashboard layout with sidebar + header shell |
| CREATE | `apps/web/app/dashboard/page.tsx` | Dashboard overview (redirect to swarm control) |
| CREATE | `apps/web/app/dashboard/swarm/page.tsx` | Swarm Control Center page |
| CREATE | `apps/web/app/dashboard/swarm/[runId]/page.tsx` | Autopsy Report Viewer page |
| CREATE | `apps/web/app/dashboard/findings/page.tsx` | Findings Explorer page |
| CREATE | `apps/web/components/shell/sidebar-nav.tsx` | Sidebar navigation component |
| CREATE | `apps/web/components/shell/header.tsx` | Header with user menu + workspace selector |
| CREATE | `apps/web/components/shell/breadcrumbs.tsx` | Breadcrumb navigation |
| CREATE | `apps/web/components/swarm/agent-card.tsx` | Agent status card component |
| CREATE | `apps/web/components/swarm/run-status.tsx` | Real-time swarm run status indicator |
| CREATE | `apps/web/components/swarm/gate-matrix.tsx` | 12-gate validation matrix visualization |
| CREATE | `apps/web/components/swarm/finding-drawer.tsx` | Finding detail slide-over drawer |
| CREATE | `apps/web/components/swarm/executive-summary.tsx` | Claude-generated summary display |
| CREATE | `apps/web/components/findings/findings-table.tsx` | Paginated findings data table |
| CREATE | `apps/web/components/findings/filter-bar.tsx` | Multi-filter bar for findings |
| CREATE | `apps/web/components/ui/severity-badge.tsx` | Severity badge (critical/high/medium/low) |
| CREATE | `apps/web/components/ui/mitre-tag.tsx` | MITRE ATT&CK tactic/technique tag |
| CREATE | `apps/web/lib/hooks/use-swarm-run.ts` | Hook for POST /swarm/autopsy + status polling |
| CREATE | `apps/web/lib/hooks/use-agents.ts` | Hook for GET /swarm/agents |
| CREATE | `apps/web/lib/hooks/use-autopsy-report.ts` | Hook for GET /swarm/autopsy/{id} |
| CREATE | `apps/web/lib/hooks/use-swarm-findings.ts` | Hook for GET /swarm/findings |
| CREATE | `apps/web/lib/api-client.ts` | Centralized fetch wrapper with auth headers |
| MODIFY | `apps/web/components/shell/sidebar-nav.tsx` | Add swarm + findings nav items |

#### Infrastructure Changes
- SSE (Server-Sent Events) endpoint for real-time run progress, or polling fallback
- Next.js API routes for BFF (Backend-for-Frontend) if needed

#### Dependencies
- Sprint 32 (Swarm autopsy API endpoints)
- Sprint 38 (All backend APIs stable)

#### Risk Items
- Large autopsy reports (1000+ findings) may cause slow page renders; implement virtual scrolling
- Real-time run status requires SSE or WebSocket; polling fallback every 2s as MVP
- 12-gate matrix visualization is complex; consider heatmap approach

---

### Sprint 40: Security Graph Visualization + Attack Path UI -- "See the Threats"
**Duration:** 2 weeks (Sep 7-18, 2026)
**Story Points:** 40

#### Deliverables

1. **Interactive security graph visualization**
   - Acceptance: @xyflow/react graph canvas showing SecurityGraphNodes and Edges from Neo4j; nodes colored by type (IAM, compute, storage, network); edges styled by type; zoom/pan/fit; click node to see properties + linked findings

2. **Attack path visualization**
   - Acceptance: Highlight attack paths on the graph with animated edges; show path severity score; step-through mode showing hop-by-hop progression; path list sidebar with sorting by risk score

3. **Graph filtering and search**
   - Acceptance: Filter nodes by type, region, severity; search by name/ARN; highlight connected components; show/hide edge types; minimap for navigation

4. **MITRE ATT&CK matrix view**
   - Acceptance: MITRE ATT&CK Cloud matrix grid; cells colored by number of findings mapped to each technique; click cell to see findings list; coverage percentage displayed per tactic

#### Frontend Pages/Components

| Action | File | Description |
|---|---|---|
| CREATE | `apps/web/app/dashboard/graph/page.tsx` | Security graph visualization page |
| CREATE | `apps/web/app/dashboard/graph/[pathId]/page.tsx` | Attack path detail page |
| CREATE | `apps/web/app/dashboard/mitre/page.tsx` | MITRE ATT&CK matrix view |
| CREATE | `apps/web/components/graph/security-graph.tsx` | Main @xyflow/react graph canvas |
| CREATE | `apps/web/components/graph/graph-node.tsx` | Custom graph node component (typed by resource) |
| CREATE | `apps/web/components/graph/graph-edge.tsx` | Custom graph edge component (styled by type) |
| CREATE | `apps/web/components/graph/attack-path-overlay.tsx` | Attack path highlight overlay |
| CREATE | `apps/web/components/graph/graph-filters.tsx` | Graph filter sidebar |
| CREATE | `apps/web/components/graph/node-detail-panel.tsx` | Node detail panel with findings |
| CREATE | `apps/web/components/graph/graph-minimap.tsx` | Minimap for large graphs |
| CREATE | `apps/web/components/mitre/mitre-matrix.tsx` | MITRE ATT&CK matrix grid component |
| CREATE | `apps/web/components/mitre/technique-cell.tsx` | Single technique cell with finding count |
| CREATE | `apps/web/components/mitre/tactic-column.tsx` | Tactic column header + stats |
| CREATE | `apps/web/lib/hooks/use-graph-data.ts` | Hook for graph node/edge data |
| CREATE | `apps/web/lib/hooks/use-attack-paths.ts` | Hook for attack path queries |
| CREATE | `apps/web/lib/hooks/use-mitre-coverage.ts` | Hook for MITRE coverage data |
| MODIFY | `apps/web/components/shell/sidebar-nav.tsx` | Add graph + MITRE nav items |

#### Backend Files

| Action | File | Description |
|---|---|---|
| CREATE | `apps/api/app/routers/graph.py` | `/api/v1/graph/nodes`, `/graph/edges`, `/graph/paths` |
| CREATE | `apps/api/app/routers/mitre.py` | `/api/v1/mitre/coverage`, `/mitre/findings/{technique}` |
| MODIFY | `apps/api/app/main.py` | Register graph and mitre routers |

#### Infrastructure Changes
- @xyflow/react + dagre layout dependency in frontend
- Graph API endpoints with pagination for large graphs

#### Dependencies
- Sprint 37 (Neo4j for graph queries)
- Sprint 39 (Dashboard shell, API client)

#### Risk Items
- @xyflow/react performance with 10K+ nodes requires virtualization and level-of-detail rendering
- Attack path animation may cause jank; use requestAnimationFrame
- MITRE matrix is a dense UI; needs responsive design for smaller screens

---

### Sprint 41: Multi-Tenant Auth + RBAC + API Gateway -- "Enterprise Ready"
**Duration:** 2 weeks (Sep 21 - Oct 2, 2026)
**Story Points:** 44

#### Deliverables

1. **Auth0/Okta OIDC integration**
   - Acceptance: Login via Auth0 or Okta; JWT access tokens validated by FastAPI middleware; user profile synced to local users table; session management with refresh tokens; logout invalidates session

2. **Multi-tenant workspace isolation**
   - Acceptance: All queries scoped by workspace_id; workspace_id extracted from JWT claims; no cross-tenant data leakage; tenant isolation tested with 2+ workspaces

3. **Role-Based Access Control (RBAC)**
   - Acceptance: Roles defined: admin, analyst, viewer, api_only; permissions matrix: admin (all), analyst (read + run swarm + suppress findings), viewer (read-only), api_only (API access no UI); role assignment per user per workspace

4. **API Gateway middleware**
   - Acceptance: Rate limiting per tenant (configurable); request logging with correlation IDs; API key authentication for service-to-service; request/response validation middleware

5. **Audit log service**
   - Acceptance: All user actions (login, run swarm, suppress finding, change role) logged to audit_logs table; immutable entries; queryable by user, action, timestamp; retention policy configurable

#### Backend Files

| Action | File | Description |
|---|---|---|
| CREATE | `apps/api/app/auth/__init__.py` | Auth package |
| CREATE | `apps/api/app/auth/oidc.py` | Auth0/Okta OIDC token validation |
| CREATE | `apps/api/app/auth/rbac.py` | RBAC permission checking middleware |
| CREATE | `apps/api/app/auth/api_key.py` | API key authentication for service accounts |
| CREATE | `apps/api/app/models/user.py` | User ORM: id, email, name, auth_provider_id |
| CREATE | `apps/api/app/models/workspace.py` | Workspace ORM: id, name, slug, plan, settings |
| CREATE | `apps/api/app/models/workspace_membership.py` | WorkspaceMembership ORM: user_id, workspace_id, role |
| CREATE | `apps/api/app/models/audit_log.py` | AuditLog ORM: id, user_id, workspace_id, action, resource_type, resource_id, metadata, created_at |
| CREATE | `apps/api/app/services/audit_service.py` | AuditService: log action, query logs |
| CREATE | `apps/api/app/middleware/tenant_isolation.py` | Middleware: inject workspace_id into request state from JWT |
| CREATE | `apps/api/app/middleware/rate_limit.py` | Per-tenant rate limiting middleware |
| CREATE | `apps/api/app/middleware/request_logging.py` | Request logging with correlation ID |
| MODIFY | `apps/api/app/dependencies.py` | Replace stub get_current_user with real OIDC validation |
| MODIFY | `apps/api/app/routers/swarm.py` | Add RBAC decorators (analyst+ for run, viewer+ for read) |
| MODIFY | `apps/api/app/routers/detections.py` | Add RBAC decorators |
| CREATE | `apps/api/app/routers/auth.py` | `/api/v1/auth/callback`, `/auth/logout`, `/auth/me` |
| CREATE | `apps/api/app/routers/admin.py` | `/api/v1/admin/users`, `/admin/workspaces`, `/admin/roles` |
| CREATE | `apps/api/alembic/versions/007_auth_tables.py` | Migration for users, workspaces, workspace_memberships, audit_logs |

#### Frontend Pages/Components

| Action | File | Description |
|---|---|---|
| CREATE | `apps/web/app/auth/login/page.tsx` | Auth0/Okta login redirect page |
| CREATE | `apps/web/app/auth/callback/page.tsx` | OIDC callback handler |
| CREATE | `apps/web/app/dashboard/settings/page.tsx` | Workspace settings page |
| CREATE | `apps/web/app/dashboard/settings/members/page.tsx` | Member management (invite, role assignment) |
| CREATE | `apps/web/app/dashboard/settings/audit/page.tsx` | Audit log viewer |
| CREATE | `apps/web/components/auth/auth-provider.tsx` | Auth context provider (React context) |
| CREATE | `apps/web/components/auth/protected-route.tsx` | Route guard based on auth state + role |
| CREATE | `apps/web/components/settings/member-table.tsx` | Workspace member table with role selector |
| CREATE | `apps/web/components/settings/audit-table.tsx` | Audit log data table |
| CREATE | `apps/web/lib/hooks/use-auth.ts` | Auth hook: login, logout, token refresh, user profile |
| CREATE | `apps/web/lib/hooks/use-workspace.ts` | Workspace selection + settings hook |
| MODIFY | `apps/web/components/shell/header.tsx` | Add user menu with workspace switcher |
| MODIFY | `apps/web/lib/api-client.ts` | Add auth token injection to all requests |

#### Infrastructure Changes
- Auth0 tenant (or Okta org) configuration
- JWT validation library (python-jose or PyJWT)
- CORS configuration update for Auth0/Okta callback URLs

#### Dependencies
- Sprint 39 (Dashboard shell, API client)
- Sprint 29 (PostgreSQL for user/workspace tables)

#### Risk Items
- Auth0 free tier limits to 7K active users; Okta has similar limits; plan for pricing
- RBAC middleware on every endpoint adds ~5ms latency; use cached role lookups
- Multi-tenant query isolation requires discipline; missing WHERE workspace_id = leaks data

---

### Sprint 42: Integration Hub + REST API + Documentation -- "Ship It"
**Duration:** 2 weeks (Oct 5-16, 2026)
**Story Points:** 38

#### Deliverables

1. **Integration hub: Slack, Jira, PagerDuty**
   - Acceptance: Slack: send autopsy summary to configured channel when run completes; Jira: create ticket from any SwarmFinding with severity/description/remediation populated; PagerDuty: trigger incident for critical findings exceeding threshold; all integrations configurable per workspace

2. **Public REST API with OpenAPI documentation**
   - Acceptance: All endpoints documented in OpenAPI 3.1 schema; interactive Swagger UI at /docs; ReDoc at /redoc; API versioning via URL prefix /api/v1/; API key authentication for programmatic access

3. **Webhook delivery system**
   - Acceptance: Workspace admins configure webhook URLs; events (autopsy_completed, critical_finding, sla_breach) delivered via POST with HMAC signature; retry with exponential backoff (3 attempts); delivery log viewable in UI

4. **Executive dashboard with portfolio view**
   - Acceptance: Dashboard page showing: overall risk posture score, finding trend (30-day), agent coverage heatmap, compliance posture gauge, top 10 critical findings, swarm run history chart

5. **CSV/JSON/PDF export for reports**
   - Acceptance: Export autopsy report as PDF (server-side generation via WeasyPrint); export findings as CSV or JSON; export compliance report as PDF

6. **End-to-end integration tests**
   - Acceptance: Pytest test suite covering: swarm run lifecycle, 12-gate validation, multi-tenant isolation, RBAC enforcement, integration webhook delivery; all tests pass in CI

#### Backend Files

| Action | File | Description |
|---|---|---|
| CREATE | `apps/api/app/integrations/slack.py` | Slack webhook integration |
| CREATE | `apps/api/app/integrations/jira.py` | Jira ticket creation via REST API |
| CREATE | `apps/api/app/integrations/pagerduty.py` | PagerDuty event trigger |
| CREATE | `apps/api/app/services/webhook_service.py` | Webhook delivery engine with retry + HMAC signing |
| CREATE | `apps/api/app/models/integration_config.py` | IntegrationConfig ORM: workspace_id, type, settings_json, enabled |
| CREATE | `apps/api/app/models/webhook_delivery.py` | WebhookDelivery ORM: delivery log |
| CREATE | `apps/api/app/routers/integrations.py` | CRUD for integration configs + webhook management |
| CREATE | `apps/api/app/routers/export.py` | `/api/v1/export/findings`, `/export/autopsy/{id}`, `/export/compliance` |
| CREATE | `apps/api/app/services/export_service.py` | PDF/CSV/JSON export generation |
| CREATE | `apps/api/app/services/portfolio_service.py` | Aggregate risk posture, trend calculation, portfolio metrics |
| CREATE | `apps/api/app/routers/portfolio.py` | `/api/v1/portfolio/posture`, `/portfolio/trend`, `/portfolio/top-findings` |
| MODIFY | `apps/api/app/main.py` | Register integrations, export, portfolio routers; configure OpenAPI metadata |
| CREATE | `apps/api/alembic/versions/008_integrations.py` | Migration for integration_configs, webhook_deliveries |
| CREATE | `apps/api/tests/test_swarm_lifecycle.py` | E2E test: create workspace, run autopsy, verify findings |
| CREATE | `apps/api/tests/test_multi_tenant.py` | E2E test: verify tenant isolation |
| CREATE | `apps/api/tests/test_rbac.py` | E2E test: verify role enforcement |
| CREATE | `apps/api/tests/test_12_gate.py` | Unit tests for all 12 validation gates |

#### Frontend Pages/Components

| Action | File | Description |
|---|---|---|
| CREATE | `apps/web/app/dashboard/portfolio/page.tsx` | Executive portfolio dashboard |
| CREATE | `apps/web/app/dashboard/settings/integrations/page.tsx` | Integration configuration page |
| CREATE | `apps/web/components/portfolio/risk-posture-gauge.tsx` | Overall risk score gauge |
| CREATE | `apps/web/components/portfolio/trend-chart.tsx` | 30-day finding trend line chart |
| CREATE | `apps/web/components/portfolio/agent-heatmap.tsx` | Agent coverage heatmap |
| CREATE | `apps/web/components/portfolio/top-findings.tsx` | Top 10 critical findings list |
| CREATE | `apps/web/components/integrations/slack-config.tsx` | Slack integration config form |
| CREATE | `apps/web/components/integrations/jira-config.tsx` | Jira integration config form |
| CREATE | `apps/web/components/integrations/pagerduty-config.tsx` | PagerDuty integration config form |
| CREATE | `apps/web/components/integrations/webhook-config.tsx` | Custom webhook config form |
| CREATE | `apps/web/lib/hooks/use-portfolio.ts` | Portfolio metrics hook |
| CREATE | `apps/web/lib/hooks/use-integrations.ts` | Integration config CRUD hook |
| MODIFY | `apps/web/components/shell/sidebar-nav.tsx` | Add portfolio + integrations nav items |

#### Infrastructure Changes
- WeasyPrint system dependency for PDF generation (or alternative like reportlab)
- Webhook delivery uses Celery for async retry

#### Dependencies
- Sprint 39 (Dashboard shell)
- Sprint 41 (Auth + RBAC for integration config permissions)
- Sprint 38 (Kafka for event-driven webhook triggers)

#### Risk Items
- PDF generation is CPU-intensive; offload to Celery worker
- Jira/Slack API token storage requires encryption at rest
- Webhook HMAC secret rotation needs admin workflow

#### Milestone: v3.0 Complete
- Full React SPA with 8 dashboard pages
- Multi-tenant auth with RBAC (4 roles)
- Neo4j-powered security graph visualization
- 15 agents with parallel execution + context chaining
- GraphRAG enrichment
- Zep memory for historical context
- 12-gate validation framework
- Integration hub (Slack, Jira, PagerDuty, webhooks)
- Export (PDF, CSV, JSON)
- Portfolio executive dashboard
- Kafka event streaming
- Full observability (Prometheus metrics)
- Comprehensive test suite

---

## Cumulative File Inventory

### Backend (Python) -- New Files by Sprint

| Sprint | New Files | Modified Files | Total New |
|---|---|---|---|
| 29 | 11 | 2 | 11 |
| 30 | 12 | 1 | 23 |
| 31 | 13 | 1 | 36 |
| 32 | 12 | 2 | 48 |
| 33 | 10 | 1 | 58 |
| 34 | 12 | 1 | 70 |
| 35 | 11 | 2 | 81 |
| 36 | 10 | 3 | 91 |
| 37 | 9 | 3 | 100 |
| 38 | 10 | 3 | 110 |
| 39 | 2 (API only) | 1 | 112 |
| 40 | 3 | 1 | 115 |
| 41 | 17 | 3 | 132 |
| 42 | 17 | 1 | 149 |

### Frontend (TypeScript/React) -- New Files by Sprint

| Sprint | New Files | Modified Files | Total New |
|---|---|---|---|
| 29-38 | 0 | 0 | 0 |
| 39 | 22 | 1 | 22 |
| 40 | 17 | 1 | 39 |
| 41 | 12 | 2 | 51 |
| 42 | 12 | 1 | 63 |

### Cumulative Story Points

| Sprint | Points | Running Total |
|---|---|---|
| 29 | 34 | 34 |
| 30 | 40 | 74 |
| 31 | 42 | 116 |
| 32 | 44 | 160 |
| 33 | 38 | 198 |
| 34 | 40 | 238 |
| 35 | 42 | 280 |
| 36 | 44 | 324 |
| 37 | 46 | 370 |
| 38 | 40 | 410 |
| 39 | 42 | 452 |
| 40 | 40 | 492 |
| 41 | 44 | 536 |
| 42 | 38 | 574 |

**Total: 574 story points across 14 sprints (28 weeks)**
**Average velocity: 41 points/sprint**

---

## Critical Path Dependencies

```
Sprint 29 (Infra) ─────┬──> Sprint 30 (Agent Framework) ──> Sprint 31 (6 Agents)
                        │                                         │
                        │                                         v
                        │                               Sprint 32 (12-Gate + MVP)  ← v1.0
                        │                                         │
                        ├──> Sprint 33 (CSPM+CIEM) ──────────────┤
                        │                                         │
                        ├──> Sprint 34 (Vulns+DSPM+CDR) ─────────┤
                        │                                         │
                        │    Sprint 35 (AttackPath+Code+K8s) ─────┤
                        │                                         │
                        │    Sprint 36 (Context+Memory) ──────────┤
                        │         │                               │
                        │         v                               │
                        │    Sprint 37 (Neo4j+GraphRAG) ──────────┤
                        │         │                               │
                        │         v                               │
                        └──> Sprint 38 (Parallel+Kafka) ──────────┤  ← v2.0
                                                                  │
                             Sprint 39 (React SPA) ───────────────┤
                                  │                               │
                                  ├──> Sprint 40 (Graph UI) ──────┤
                                  │                               │
                                  ├──> Sprint 41 (Auth+RBAC) ─────┤
                                  │                               │
                                  └──> Sprint 42 (Ship) ──────────┘  ← v3.0
```

---

## Risk Register (Cross-Sprint)

| Risk | Probability | Impact | Mitigation | Sprint Affected |
|---|---|---|---|---|
| Claude API cost overrun (15 agents x N workspaces) | HIGH | MEDIUM | Agent result caching (Sprint 38); model selection per agent (sonnet for simple, opus for complex) | 31-42 |
| Neo4j operational complexity | MEDIUM | HIGH | Start with PostgreSQL-backed graph queries; Neo4j as optimization only | 37-42 |
| Zep Cloud availability/latency | MEDIUM | MEDIUM | Local fallback memory store in PostgreSQL; Zep as enhancement not requirement | 36-42 |
| Kafka operational overhead | MEDIUM | MEDIUM | Start with Redis Streams (Sprint 38); migrate to Kafka only if throughput demands | 38-42 |
| Context window limits (Claude 200K) | HIGH | HIGH | Aggressive summarization in context chaining; per-agent context budget | 36-42 |
| Multi-tenant data leakage | LOW | CRITICAL | Mandatory workspace_id in all queries; integration tests per sprint; row-level security in PostgreSQL | 41-42 |
| Frontend performance with large datasets | MEDIUM | MEDIUM | Virtual scrolling for tables/graphs; pagination on all list endpoints; lazy loading | 39-42 |
| Auth0/Okta integration delays | LOW | MEDIUM | Build with generic OIDC; Auth0 and Okta as provider implementations | 41 |
| Team velocity below 41 pts/sprint | MEDIUM | HIGH | Buffer sprints 33-35 have parallelizable work; can extend timeline by 2 sprints if needed | All |
| Detection rule false positive rate | MEDIUM | MEDIUM | 12-gate validation gates 9 (False Positive Filter) tunable per rule; feedback loop in v3.0 | 32-42 |

---

## Reuse Summary

| Existing Asset | Reused In | How |
|---|---|---|
| `DetectionService` (8 rules) | Sprint 30 DetectionAgent, Sprint 34 CDRSimulationAgent | Wrapped as agent; extended with 12 new rules |
| `_alert()` helper function | Sprint 30 SwarmFinding model | Pattern extracted into Pydantic model |
| `_MITRE` mapping dict | Sprint 31 mitre_registry.py | Extracted and expanded from 8 to 60+ techniques |
| `_KEV_SET` frozenset | Sprint 34 kev_entries DB table | Replaced with DB-backed lookup; data from CISA catalog |
| `_risk_score()` function | Sprint 30 SwarmFinding.risk_score | Pattern kept; added EPSS/KEV weighting |
| `CanonicalFinding` ORM | All sprints | Extended with swarm_agent_id, gate_results fields |
| `SecurityGraphNode/Edge` ORM | Sprint 37 Neo4j sync | Dual-write adapter; PostgreSQL remains source of truth |
| FastAPI dependency injection | All sprints | Existing pattern (get_async_db, get_current_user) extended |
| Router pattern (prefix + tags) | All sprints | 10+ new routers follow existing detections.py pattern |
| AWS integrations scaffold | Sprint 33+ | Extended with new service clients |
