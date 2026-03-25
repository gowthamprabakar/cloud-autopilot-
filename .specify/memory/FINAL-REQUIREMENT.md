# OmniSec — Autonomous Cloud Security Intelligence Platform

> **Version:** 2.0 | **Status:** APPROVED FOR IMPLEMENTATION
> **Date:** 2026-03-25 | **Owner:** Security Architecture Team, BA: Praba, Flat World Solutions
> **Authority:** This document is the SINGLE SOURCE OF TRUTH for the OmniSec project. It supersedes all previous specifications including the Cloud Copilot CSPM spec and Swarm Autopsy standalone spec.

---

## 1. Product Identity

| Field | Value |
|-------|-------|
| **Name** | OmniSec |
| **Category** | Next-Gen CNAPP + Simulation Intelligence + Swarm AI |
| **Owner** | Security Architecture Team, BA: Praba, Flat World Solutions |
| **Document Status** | APPROVED FOR IMPLEMENTATION |

OmniSec unifies cloud-native application protection (CNAPP), multi-agent swarm simulation, and autonomous gap coverage into a single intelligence platform. It enables security teams to discover misconfigurations, simulate adversarial attack chains, validate defenses through a 12-gate framework, and generate IaC-grade remediation — all orchestrated by an autonomous 15-agent swarm powered by Claude.

---

## 2. System Architecture

### 2.1 Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19 + TypeScript + TailwindCSS + Zustand |
| **API** | FastAPI (Python) + Celery + Redis |
| **AI Engine** | Anthropic Claude API (`claude-sonnet-4-20250514`) / Ollama for air-gapped deployments |
| **Knowledge Graph** | Neo4j Enterprise (GraphRAG) |
| **Agent Memory** | Zep Cloud (temporal episodic + working + group memory) |
| **Integration Bus** | Kafka / AWS EventBridge |
| **Authentication** | Auth0/Okta OIDC + RBAC + API keys |
| **Observability** | OpenTelemetry + Datadog/Grafana |

### 2.2 Architectural Principles

- Cloud-native microservices with container-first deployment
- Event-driven agent communication over Kafka/EventBridge
- GraphRAG-powered contextual reasoning via Neo4j
- Temporal memory continuity across simulation runs via Zep Cloud
- Air-gap capable with Ollama model substitution
- Multi-tenant isolation at the data, compute, and network layers

---

## 3. Product Modules

OmniSec is organized into three product modules encompassing 23 functional domains.

### 3.1 Module A — Wiz CNAPP Simulation Layer (10 Domains)

Module A simulates the full breadth of a Wiz-class CNAPP platform, providing configuration analysis, workload protection, identity governance, and detection across all cloud resource types.

#### A-01: Cloud Security Posture Management (CSPM)

- 2800+ configuration rules across AWS, Azure, GCP, OCI
- Infrastructure-as-Code (IaC) scanner for Terraform, CloudFormation, Pulumi, Bicep
- Compliance mapper: CIS Benchmarks, NIST 800-53, PCI-DSS, HIPAA, SOC2, ISO 27001
- Security graph: resource-to-resource relationship modeling with attack path context
- Auto-remediation: generates IaC fix PRs with rollback safety

#### A-02: Cloud Workload Protection Platform (CWPP)

- CVE scanner with NVD, OSV, and vendor advisory correlation
- Malware detector: static analysis + behavioral heuristics
- SBOM analyzer: CycloneDX and SPDX generation and vulnerability matching
- Container security: image scanning, runtime protection, drift detection
- Serverless protection: Lambda/Cloud Functions cold-start injection analysis

#### A-03: Cloud Infrastructure Entitlement Management (CIEM)

- Effective permissions calculator across IAM policies, resource policies, SCPs, permission boundaries
- Privilege escalation path mapper with graph-based traversal
- Least-privilege policy generator with usage-based recommendations
- Just-In-Time (JIT) access provisioning engine
- Federated trust analyzer: cross-account role chains, SAML/OIDC trust evaluation

#### A-04: Data Security Posture Management (DSPM)

- PII/PHI/PCI data classifier with ML-based pattern recognition
- Data exposure path analyzer: public buckets, overly permissive shares, cross-account access
- Data flow tracer: ingestion-to-storage-to-egress lineage mapping
- Regulatory assessor: GDPR Article 30, HIPAA data handling, PCI scope determination
- Breach impact simulator: blast radius estimation per data store

#### A-05: Kubernetes Security Posture Management (KSPM)

- RBAC analyzer: over-privileged service accounts, cluster-admin abuse
- Network policy auditor: missing ingress/egress rules, namespace isolation gaps
- Admission controller validator: OPA/Gatekeeper policy coverage
- Pod-to-cloud pivot detector: IMDS access, mounted secrets, node-level escape paths
- Multi-cluster federation security: cross-cluster trust boundaries

#### A-06: Cloud Detection & Response (CDR)

- eBPF runtime coverage analyzer: syscall monitoring breadth
- SecOps agent deployment validator: sensor health, coverage gaps
- Alert fidelity scorer: signal-to-noise ratio, false positive rate
- MTTR analyzer: detection-to-containment time measurement
- CDR-CSPM correlation engine: runtime alerts mapped to posture findings

#### A-07: IaC & Code Security

- Repository scanner: Terraform, Helm, Kustomize, Dockerfiles
- Software Composition Analysis (SCA): dependency vulnerability matching
- Secrets detection: API keys, tokens, credentials in code and config
- CI/CD pipeline security: runner isolation, artifact integrity, OIDC token usage
- 1-click fix PRs: auto-generated pull requests with validated remediation

#### A-08: Vulnerability Management

- Multi-scanner aggregator: consolidates findings from Qualys, Tenable, Wiz, Trivy
- Risk-based prioritization: CVSS + exploitability + exposure + business context
- SLA tracking: patch windows, exception management, escalation triggers
- Patch feasibility analyzer: dependency conflict detection, rollback readiness

#### A-09: AI Security Posture Management (AI-SPM)

- AI Bill of Materials (AI-BOM): model inventory, training data lineage, API surface
- OWASP LLM Top 10 coverage: prompt injection, data poisoning, model theft
- MCP server security: tool authorization, sandboxing, input validation
- Training data guardian: PII in training sets, data provenance verification

#### A-10: Attack Surface Management (ASM)

- External exposure discovery: internet-facing assets, open ports, exposed services
- Shadow asset detection: unmanaged cloud resources, orphaned DNS entries
- Exposure prioritizer: attack likelihood scoring based on threat intelligence
- Ownership resolver: asset-to-team mapping via tags, metadata, and graph analysis

---

### 3.2 Module B — MiroFish Swarm Intelligence Engine (6 Domains)

Module B implements the autonomous multi-agent simulation engine that orchestrates Claude-powered agents to discover, exploit, defend, and validate security posture.

#### B-01: Seed Ingestion & Graph Construction

- Wiz finding feed ingestion (JSON/CSV/API)
- GraphRAG construction in Neo4j: entities, relationships, attack paths
- SimConfig generator: domain-specific simulation parameters from seed data
- Seed validator: completeness and consistency checks before simulation launch
- Multi-source fusion: merge findings from multiple CNAPP tools into unified graph

#### B-02: Agent Anatomy Engine

- Working memory: per-agent scratchpad for current simulation context
- Episodic memory: timestamped interaction history via Zep Cloud
- Goal stack: hierarchical objective decomposition with priority ordering
- Perception module: ingests graph context, peer messages, and simulation state
- Action loop: observe-orient-decide-act cycle with structured Claude API calls
- System prompt engine: dynamic prompt assembly per agent role and simulation phase

#### B-03: 15-Agent Swarm Roster

| Agent ID | Codename | Role | Autonomy Level |
|----------|----------|------|----------------|
| ORCH-01 | SwarmMaster | Orchestration, task distribution, conflict resolution | 5 |
| SCOUT-01 | PathFinder | Reconnaissance, attack path discovery | 4 |
| EXPLOIT-01 | ExploitSynth | Exploit chain construction, proof-of-concept generation | 4 |
| DEFEND-01 | ShieldWeaver | Defense strategy, IaC remediation, countermeasure design | 4 |
| WIZ-CSPM | — | CSPM finding analysis, compliance mapping | 3 |
| WIZ-CIEM | — | Identity and entitlement analysis | 3 |
| WIZ-CDR | — | Detection and response correlation | 3 |
| VALID-01 | GateKeeper | 12-gate validation execution and scoring | 5 |
| REPORT-01 | — | Report generation, executive summaries, export | 3 |
| DEEP-XX | DeepDiver | Deep-dive analysis on specific domains on demand | 3 |
| QUANT-01 | QuantumSage | Quantum cryptography assessment, PQC readiness | 4 |
| FAKE-01 | DeepFakeHunter | Deepfake identity fraud detection and simulation | 4 |
| CHAIN-01 | ChainBreaker | Supply chain and firmware attack analysis | 4 |
| OT-01 | SCADAGuard | OT/ICS/SCADA security, digital twin simulation | 4 |
| LLM-01 | LLMShield | LLMjacking detection, AI agent threat analysis | 4 |

Autonomy levels: 1 (fully supervised) to 5 (fully autonomous).

#### B-04: OASIS Simulation Engine

- Time engine: configurable simulation clock (accelerated, real-time, step-through)
- Dual-platform execution: cloud-hosted and air-gapped modes
- Scalable inference: parallel Claude API calls with rate-limit management
- God's-Eye injector: mid-simulation scenario injection by operator
- Agent interview: pause and interrogate individual agents during simulation
- Emergent behavior capture: unexpected finding logging and classification

#### B-05: Zep Cloud Temporal Memory

- Per-agent episodic memory: chronological interaction records with decay
- Group memory: shared knowledge base accessible to all agents in a simulation
- Decay engine: configurable memory relevance scoring and pruning
- Cross-simulation continuity: agents retain learnings across simulation runs

#### B-06: Cross-Agent Communication Bus

- Directed message routing: point-to-point and broadcast messaging
- Message types: FINDING, HYPOTHESIS, REQUEST, RESPONSE, ALERT, DIRECTIVE
- Audit export: full message log with timestamps for compliance
- Real-time visualization: live message flow graph in the UI

---

### 3.3 Module C — 7-Domain Gap Coverage

Module C addresses seven emerging threat domains that fall outside traditional CNAPP coverage, representing the frontier of cloud security risk.

#### C-01: Quantum Cryptography Harvest-Now-Decrypt-Later

- Crypto-BOM: inventory all cryptographic algorithms, key lengths, certificates
- Harvest signal detector: identify data exfiltration patterns consistent with store-now attacks
- PQC migration planner: prioritized transition roadmap to NIST PQC algorithms (ML-KEM, ML-DSA)
- Crypto-agility scorer: assess ability to swap algorithms without code changes
- Q-Day readiness index: composite score of quantum vulnerability exposure

#### C-02: AI Deepfake Identity Fraud

- CEO doppelganger simulator: generate deepfake attack scenarios for executive impersonation
- Passkey validation checker: assess FIDO2/WebAuthn deployment coverage
- Out-of-band (OOB) verification auditor: evaluate secondary channel confirmation flows
- Behavioral biometrics analyzer: typing cadence, mouse movement, voice pattern baselines
- Social engineering simulation: phishing and vishing attack chain modeling

#### C-03: Supply Chain & Firmware Attack

- Dependency poisoning detector: typosquatting, namespace confusion, maintainer compromise
- SBOM+ analyzer: extended SBOM with build provenance and dependency health scoring
- Sigstore integration: verify artifact signatures across the software supply chain
- eBPF rootkit detector: kernel-level persistence mechanism identification
- Firmware attestation: TPM/Secure Boot validation, firmware integrity monitoring

#### C-04: Autonomous Malicious AI Agents

- Machine-speed attack simulator: model AI-driven reconnaissance and exploitation at scale
- Deception grid: honeypot and honeytoken deployment for AI agent detection
- Adaptive ransomware modeler: simulate ransomware that evolves evasion techniques
- AI vs AI arena: pit defensive agents against simulated offensive AI agents
- Circuit breaker: automated kill switch when simulated agents exceed safety thresholds

#### C-05: OT/ICS Critical Infrastructure

- Digital twin constructor: virtual replica of OT/ICS environments for safe simulation
- Air gap integrity validator: assess isolation controls between IT and OT networks
- Modbus/DNP3 protocol whitelist: allowlisted command sequences with anomaly detection
- Engineering workstation isolation checker: evaluate segmentation of HMI/SCADA systems
- Nation-state dwell time estimator: model long-duration APT persistence in OT environments

#### C-06: LLMjacking & AI Resource Theft

- Scylla pattern detector: identify credential stuffing targeting cloud AI APIs
- Canary credential deployer: strategically placed AI API keys as tripwires
- AI spend anomaly detector: usage-based alerting for unexpected inference costs
- Multi-account correlator: detect distributed abuse across cloud accounts
- VPC endpoint enforcer: restrict AI API access to approved network paths only

#### C-07: Federated Identity & Cross-Cloud Attacks

- Golden SAML detector: identify forged SAML assertion attack indicators
- OIDC token binding validator: ensure tokens are bound to intended relying parties
- Azure cross-tenant analyzer: evaluate Lighthouse, B2B, and guest access risks
- Token revocation auditor: assess ability to invalidate compromised tokens at scale
- Cross-cloud identity correlator: map identities across AWS, Azure, GCP for lateral movement paths

---

## 4. 12-Gate Validation Framework

Every simulation run produces a gate scorecard. Gates validate that proposed remediations and defense postures meet enterprise security standards.

| Gate | Name | Weight | Description |
|------|------|--------|-------------|
| G-01 | Cryptographic Hardening | **2x** | TLS versions, cipher suites, key management, certificate lifecycle |
| G-02 | Attack Surface Reduction | **2x** | Exposed services, unnecessary ports, public asset minimization |
| G-03 | IaC Policy Correctness | 1x | Terraform/CloudFormation output is syntactically valid and policy-compliant |
| G-04 | Detection Completeness | **2x** | Coverage of MITRE ATT&CK techniques by detection rules |
| G-05 | Automated Response Speed | 1x | Time from detection to automated containment action |
| G-06 | Blast Radius Containment | 1x | Segmentation effectiveness, lateral movement barriers |
| G-07 | Lateral Movement Prevention | 1x | Network segmentation, micro-segmentation, zero-trust enforcement |
| G-08 | Credential Lifecycle | 1x | Rotation policies, secret sprawl, credential hygiene |
| G-09 | Cross-Account Coverage | 1x | Multi-account, multi-cloud policy consistency |
| G-10 | Continuous Monitoring | 1x | Real-time visibility, log completeness, alert pipeline health |
| G-11 | IR Playbook Completeness | 1x | Incident response procedure coverage per threat scenario |
| G-12 | Red-Team Pass Rate | **2x** | Percentage of simulated red-team attacks successfully blocked |

### Scoring

- Each gate produces a verdict: **PASS**, **FAIL**, or **PARTIAL**
- Each gate produces a confidence score: **0-100%**
- Double-weight gates (G-01, G-02, G-04, G-12) count 2x in the composite score
- **Composite thresholds:**
  - **>=80%**: Implementation-ready — proceed to remediation deployment
  - **60-79%**: Conditional — requires ShieldWeaver revision and re-validation
  - **<60%**: Returned to ShieldWeaver for fundamental redesign

---

## 5. API Specification

### 5.1 Core Endpoints (12)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/simulations` | Launch a new simulation run with seed data and SimConfig |
| `GET` | `/api/v1/simulations/{run_id}` | Retrieve simulation status and summary |
| `GET` | `/api/v1/simulations/{run_id}/gates` | Retrieve 12-gate validation scorecard |
| `GET` | `/api/v1/simulations/{run_id}/solution` | Retrieve IaC remediation output |
| `GET` | `/api/v1/simulations/{run_id}/audit` | Retrieve full audit trail (agent messages, decisions, memory snapshots) |
| `POST` | `/api/v1/simulations/{run_id}/inject` | Inject a God's-Eye scenario mid-simulation |
| `GET` | `/api/v1/domains` | List all 23 threat domains with metadata |
| `GET` | `/api/v1/agents` | List all 15 agent types with status and configuration |
| `POST` | `/api/v1/agents/spawn` | Spawn an ad-hoc agent for targeted analysis |
| `GET` | `/api/v1/history` | List all past simulation runs with filters |
| `DELETE` | `/api/v1/history/{run_id}` | Delete a simulation run and its artifacts |
| `GET` | `/api/v1/health` | Platform health check (API, Neo4j, Zep, Kafka, Claude API) |

### 5.2 API Standards

- All responses use JSON with envelope: `{ "status": "ok|error", "data": {...}, "meta": {...} }`
- Authentication via Bearer token (Auth0/Okta JWT) or API key header
- Rate limiting: 100 req/min per tenant (configurable)
- Pagination: cursor-based for list endpoints
- Versioning: URI path (`/api/v1/`)
- OpenAPI 3.1 spec auto-generated from FastAPI

---

## 6. Release Roadmap

| Version | Target | Scope |
|---------|--------|-------|
| **v1.0** | Q1 2026 | 6 core agents (ORCH, SCOUT, EXPLOIT, DEFEND, VALID, REPORT), Claude API integration, 9 gap domains, 12-gate framework, single-tenant HTML prototype |
| **v2.0** | Q2 2026 | 15 agents, all 17 domains (10 CNAPP + 7 gap), context chaining across agents, simulation history and export |
| **v3.0** | Q3 2026 | React 19 SPA, FastAPI backend, Neo4j knowledge graph, Zep Cloud memory, multi-tenant auth, full REST API, Jira/Slack integrations |
| **v4.0** | Q4 2026 | OASIS simulation engine, 500-agent swarm scaling, parallel simulation execution, real-time WebSocket streaming, white-label MSSP packaging |
| **v5.0** | Q2 2027 | Live Wiz API integration, digital twin mode, 1M-agent OASIS scaling, air-gapped on-premise deployment with Ollama |

---

## 7. Deployment Models

| Model | Description |
|-------|-------------|
| **SaaS Multi-Tenant** | Shared infrastructure with tenant-level data isolation. Auth0/Okta SSO. Per-tenant encryption keys. |
| **Private Cloud** | Dedicated VPC deployment within customer's cloud account. Customer-managed keys. |
| **Air-Gapped On-Premise** | Fully offline deployment using Ollama for local LLM inference. No external API calls. |
| **MSSP White-Label** | Multi-tenant with branding customization. Managed service provider console with per-customer simulation isolation. |

---

## 8. Compliance & Standards Alignment

| Standard | Applicability |
|----------|--------------|
| **NIST CSF 2.0** | Platform-wide risk management framework alignment |
| **MITRE ATT&CK** | Detection completeness mapping (Gate G-04) |
| **MITRE D3FEND** | Defensive technique coverage validation |
| **NIST PQC** | Quantum cryptography readiness (Domain C-01) |
| **ISO 27001** | Information security management system controls |
| **SOC 2 Type II** | Trust services criteria for SaaS deployment |
| **PCI-DSS v4.0** | Payment card data security for DSPM domain |
| **HIPAA** | Health information protection for DSPM domain |
| **GDPR** | Data protection and privacy for DSPM domain |
| **FedRAMP** | Federal cloud security authorization (v5.0 target) |

---

## 9. Success Criteria

The platform is considered successfully implemented when ALL of the following criteria are met:

| # | Criterion | Measurement |
|---|-----------|-------------|
| SC-01 | 15 agents execute autonomous Claude API calls with structured outputs | All 15 agent types complete a full simulation cycle without manual intervention |
| SC-02 | 12-gate validation correctly scores PASS/FAIL/PARTIAL for all gates | Gate verdicts match expected outcomes on a reference simulation dataset |
| SC-03 | IaC-grade remediation for every threat domain | Every domain produces syntactically valid, deployable Terraform/CloudFormation output |
| SC-04 | Cross-agent communication bus routes messages between all agent pairs | All 210 agent-pair combinations (15 choose 2) successfully exchange messages |
| SC-05 | Full simulation completes in under 60 seconds for all 17 domains | End-to-end simulation time measured from seed ingestion to gate scorecard |
| SC-06 | Aggregate gate pass rate of 80% or higher across all domains | Composite weighted score meets implementation-ready threshold |

---

## 10. Glossary

| Term | Definition |
|------|-----------|
| **CNAPP** | Cloud-Native Application Protection Platform |
| **CSPM** | Cloud Security Posture Management |
| **CWPP** | Cloud Workload Protection Platform |
| **CIEM** | Cloud Infrastructure Entitlement Management |
| **DSPM** | Data Security Posture Management |
| **KSPM** | Kubernetes Security Posture Management |
| **CDR** | Cloud Detection and Response |
| **ASM** | Attack Surface Management |
| **AI-SPM** | AI Security Posture Management |
| **GraphRAG** | Graph-based Retrieval Augmented Generation |
| **OASIS** | OmniSec Agent Simulation Intelligence System |
| **SimConfig** | Simulation Configuration — parameters controlling a simulation run |
| **PQC** | Post-Quantum Cryptography |
| **IaC** | Infrastructure as Code |
| **SBOM** | Software Bill of Materials |
| **JIT** | Just-In-Time (access provisioning) |
| **MSSP** | Managed Security Service Provider |

---

## Document Control

| Field | Value |
|-------|-------|
| **Version** | 2.0 |
| **Created** | 2026-03-25 |
| **Author** | Security Architecture Team |
| **Business Analyst** | Praba, Flat World Solutions |
| **Supersedes** | Cloud Copilot CSPM Spec, Swarm Autopsy Spec, All prior gap analyses |
| **Next Review** | 2026-04-25 |

> This document is the FINAL, AUTHORITATIVE requirement specification for OmniSec. All implementation work, sprint planning, and architectural decisions must reference this document as the single source of truth.
