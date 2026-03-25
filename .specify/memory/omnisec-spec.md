# OmniSec --- Autonomous Cloud Security Intelligence Platform

**Created**: 2026-03-25
**Status**: Draft
**Scope**: Full-stack autonomous cloud security simulation platform with multi-agent orchestration, CNAPP simulation, gap domain coverage, and enterprise integration layer
**Architecture**: Next.js 15 + FastAPI + PostgreSQL + Multi-Agent AI Engine (Claude)
**Go-Live Target**: Q4 2026 (5 modules, 10 sprints)
**Relationship to Cloud Copilot**: Evolution of the Cloud Copilot CSPM platform; OmniSec subsumes all existing CSPM capabilities and extends them with autonomous simulation, gap domain coverage, and enterprise-grade multi-tenancy.

---

## Table of Contents

1. [Product Overview](#product-overview)
2. [Architecture](#architecture)
3. [Data Models](#data-models)
4. [API Contracts](#api-contracts)
5. [Module A: CNAPP Simulation Layer](#module-a-cnapp-simulation-layer)
6. [Module B: Simulation Engine](#module-b-simulation-engine)
7. [Module C: Gap Domain Coverage](#module-c-gap-domain-coverage)
8. [Module D: Enterprise Features](#module-d-enterprise-features)
9. [Module E: Cross-Agent Communication](#module-e-cross-agent-communication)
10. [User Stories](#user-stories)
11. [Sprint Mapping](#sprint-mapping)
12. [Non-Functional Requirements](#non-functional-requirements)
13. [Glossary](#glossary)

---

## Product Overview

**OmniSec** is an autonomous cloud security intelligence platform that combines CNAPP simulation, multi-agent threat modeling, gap domain analysis (quantum, deepfake, supply chain, OT/ICS, LLMjacking, federated identity), and enterprise-grade integration. Security teams launch simulations across threat domains and receive certified, validated solutions with confidence scoring, MITRE ATT&CK mapping, and auto-remediation artifacts (IaC, PRs, SIEM alerts, tickets) --- all orchestrated by a swarm of specialist AI agents.

### Target Users

| Persona | Primary Module | Need |
|---|---|---|
| Security Architect | B, C | Threat simulation with validated remediation |
| CISO | B, D | Confidence-scored outputs and executive reporting |
| Red Team Lead | B, C | Multi-stage exploit chains with MITRE mapping |
| SOC Analyst | A, C | Detection coverage validation and MTTR analysis |
| Cloud Engineer | A, D | Auto-remediation IaC and 1-click fix PRs |
| Compliance Officer / Analyst | A, B | Framework mapping and 12-gate validation evidence |
| OT Security Engineer | C | OT/ICS digital twin simulation |
| Identity Architect | C | Federated identity abuse testing |
| MSSP / Platform Admin | D | Multi-tenant white-label management |
| DevOps Engineer | D | GitHub/GitLab PR integration |
| SOC Manager | D | SIEM forwarding |
| Project Manager | D | Jira/ServiceNow ticket automation |
| Auditor | E | Immutable audit logs |

---

## Architecture

### Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 / React 19 / Tailwind CSS 4 |
| Backend API | FastAPI + SQLAlchemy + PostgreSQL |
| AI Engine | Anthropic Claude (claude-sonnet-4, claude-opus-4) |
| Agent Runtime | Python asyncio multi-agent orchestrator |
| Auth | Auth0 / Okta SSO + JWT + RBAC |
| Queue | Redis Streams (agent communication bus) |
| Storage | S3-compatible object store (audit logs, reports) |
| Integrations | GitHub/GitLab API, Splunk/Elastic SIEM, Jira/ServiceNow |
| Deployment | Docker / Kubernetes / Helm charts |

### Hard Constraints

| Constraint | Limit |
|---|---|
| Full Simulation | < 60 seconds end-to-end for any single threat domain |
| Agent Inspection Latency | < 200ms for real-time anatomy viewer updates |
| UI Response | < 100ms for any user interaction |
| Concurrent Tenants | 100+ isolated workspaces |
| Validation Gates | 12 gates with evidence per gate |
| Confidence Score | 0-100% weighted composite for every simulation output |
| Audit Log | Immutable, append-only, exportable (JSON/CSV/PDF) |

---

## Data Models

### DM-01: Simulation

```typescript
interface Simulation {
  id: string;                          // UUID v4
  workspaceId: string;                 // Tenant workspace
  threatDomain: ThreatDomain;          // enum of all supported domains
  status: SimulationStatus;            // pending | running | completed | failed
  agents: AgentInstance[];             // Spawned agents for this simulation
  validationScorecard: ValidationGate[];
  confidenceScore: number;             // 0-100
  findings: Finding[];
  remediationArtifacts: Artifact[];
  auditLog: AuditEntry[];
  createdAt: string;                   // ISO 8601
  completedAt: string | null;
  durationMs: number | null;
  createdBy: string;                   // User ID
}
```

### DM-02: AgentInstance

```typescript
interface AgentInstance {
  id: string;                          // e.g. "ORCH-01", "CSPM-01"
  simulationId: string;
  codename: string;
  role: AgentRole;                     // orchestrator | scout | exploit | defend | validate | report | specialist
  status: AgentStatus;                 // idle | thinking | streaming | complete | error
  workingMemory: Record<string, any>;
  episodicMemory: EpisodicEntry[];     // FIFO, max 10
  goalStack: Goal[];
  actionLoop: ActionStage;             // SENSE | THINK | PLAN | ACT
  tokenUsage: { input: number; output: number; cost: number };
  startedAt: string | null;
  completedAt: string | null;
  output: Record<string, any> | null;
}
```

### DM-03: ValidationGate

```typescript
interface ValidationGate {
  id: string;                          // "GATE-01" through "GATE-12"
  name: string;
  category: GateCategory;
  status: "PASS" | "FAIL" | "PARTIAL";
  score: number;                       // 0-100
  weight: number;                      // Contribution to confidence score
  evidence: Evidence[];
  remediationHints: string[];
}
```

### DM-04: Finding

```typescript
interface Finding {
  id: string;
  simulationId: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
  title: string;
  description: string;
  mitreTechniques: string[];           // e.g. ["T1078", "T1190"]
  blastRadius: BlastRadius;
  affectedResources: string[];
  exploitChain: ExploitStep[];
  confidence: number;                  // 0-100
  agentId: string;                     // Which agent produced this
}
```

### DM-05: BlastRadius

```typescript
interface BlastRadius {
  directImpact: string[];              // Immediately compromised resources
  lateralPaths: LateralPath[];         // Reachable via lateral movement
  dataAtRisk: string[];                // Sensitive data in blast zone
  estimatedFinancialImpact: string;    // e.g. "$500K-$2M"
  affectedUsers: number;
}
```

### DM-06: Artifact (Remediation)

```typescript
interface Artifact {
  id: string;
  type: "terraform" | "cloudformation" | "opa_policy" | "siem_rule" | "detection_rule" | "pr_diff" | "jira_ticket";
  content: string;
  targetIntegration: string;           // e.g. "github", "splunk", "jira"
  status: "generated" | "pushed" | "applied" | "failed";
  findingIds: string[];                // Which findings this remediates
}
```

### DM-07: AuditEntry

```typescript
interface AuditEntry {
  id: string;
  timestamp: string;                   // ISO 8601
  actorType: "agent" | "user" | "system";
  actorId: string;
  action: string;
  detail: Record<string, any>;
  simulationId: string;
  immutable: true;                     // Append-only, never modified
}
```

### DM-08: CommBusMessage

```typescript
interface CommBusMessage {
  id: string;
  timestamp: string;
  fromAgent: string;
  toAgent: string | "broadcast";
  type: "info" | "solution" | "alert" | "spawn";
  content: string;
  metadata: Record<string, any>;
  simulationId: string;
}
```

### DM-09: Workspace (Multi-Tenant)

```typescript
interface Workspace {
  id: string;
  name: string;
  slug: string;
  plan: "free" | "pro" | "enterprise";
  brandingConfig: BrandingConfig | null;   // White-label
  ssoProvider: "auth0" | "okta" | null;
  members: WorkspaceMember[];
  apiKeys: ApiKey[];
  integrations: Integration[];
  createdAt: string;
}
```

### DM-10: CSPMConfigRule

```typescript
interface CSPMConfigRule {
  id: string;
  provider: "aws" | "azure" | "gcp";
  service: string;
  ruleCode: string;
  description: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  complianceFrameworks: string[];      // ["NIST-800-53", "ISO-27001", "SOC2", "PCI-DSS"]
  autoRemediationIaC: string | null;   // Terraform/CF snippet
  enabled: boolean;
}
```

---

## API Contracts

### Simulation Engine

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/simulations` | Launch a new simulation |
| GET | `/api/v1/simulations/{id}` | Get simulation status and results |
| GET | `/api/v1/simulations/{id}/agents` | List all agents in a simulation |
| GET | `/api/v1/simulations/{id}/agents/{agentId}` | Get agent anatomy (memory, goals, action loop) |
| GET | `/api/v1/simulations/{id}/agents/{agentId}/stream` | SSE stream of agent real-time state |
| POST | `/api/v1/simulations/{id}/agents/spawn` | Spawn a specialist agent mid-simulation |
| GET | `/api/v1/simulations/{id}/validation` | Get 12-gate validation scorecard |
| GET | `/api/v1/simulations/{id}/findings` | List findings with MITRE mapping |
| GET | `/api/v1/simulations/{id}/artifacts` | List remediation artifacts |
| GET | `/api/v1/simulations/{id}/confidence` | Get confidence score breakdown |
| GET | `/api/v1/simulations/{id}/audit-log` | Get immutable audit log |
| POST | `/api/v1/simulations/{id}/audit-log/export` | Export audit log (JSON/CSV/PDF) |

### CNAPP Simulation

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/cnapp/cspm/simulate` | Run CSPM config rule simulation |
| GET | `/api/v1/cnapp/cspm/rules` | List all 2800+ config rules |
| POST | `/api/v1/cnapp/ciem/simulate` | Run CIEM privilege escalation simulation |
| POST | `/api/v1/cnapp/cdr/simulate` | Run CDR detection coverage simulation |
| GET | `/api/v1/cnapp/compliance/frameworks` | List supported compliance frameworks |
| POST | `/api/v1/cnapp/compliance/map` | Map findings to compliance frameworks |
| POST | `/api/v1/cnapp/vulns/simulate` | Run vulnerability management simulation |

### Enterprise Integrations

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/integrations/github/pr` | Push fix PR to GitHub |
| POST | `/api/v1/integrations/gitlab/mr` | Push fix MR to GitLab |
| POST | `/api/v1/integrations/siem/forward` | Forward findings to Splunk/Elastic |
| POST | `/api/v1/integrations/ticketing/create` | Create Jira/ServiceNow ticket |
| GET | `/api/v1/workspaces` | List workspaces (multi-tenant) |
| POST | `/api/v1/workspaces` | Create workspace |
| PUT | `/api/v1/workspaces/{id}/branding` | Update white-label branding |
| GET | `/api/v1/workspaces/{id}/members` | List workspace members |
| POST | `/api/v1/auth/sso/configure` | Configure SSO provider |
| POST | `/api/v1/auth/api-keys` | Generate API key |

### Cross-Agent Communication

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/simulations/{id}/comm-bus` | Get all cross-agent messages |
| GET | `/api/v1/simulations/{id}/comm-bus/stream` | SSE stream of live messages |

---

## User Stories

---

### Module B: Simulation Engine

---

#### US-001: Launch Autonomous Threat Simulation

**As a** Security Architect,
**I want to** select a threat domain and launch a full autonomous simulation,
**So that** I receive a certified solution in under 60 seconds.

**Priority**: MUST
**Sprint**: Sprint 1

**Acceptance Criteria**

```gherkin
Given I am authenticated and on the Simulation Dashboard
When I select a threat domain from the domain picker (e.g., "Quantum Harvest Attack")
  And I click "Launch Simulation"
Then the system spawns the agent swarm (ORCH, SCOUT, EXPLOIT, DEFEND, VALID, REPORT)
  And a real-time progress indicator shows pipeline stage
  And the full simulation completes in under 60 seconds
  And I receive a certified solution with findings, remediation artifacts, and a confidence score

Given the simulation is already running
When I attempt to launch another simulation in the same workspace
Then the system queues the request and displays "Simulation queued --- current run in progress"

Given the Claude API is unreachable or returns 5xx
When the simulation starts
Then the system retries with exponential backoff (max 3 retries)
  And if all retries fail, the simulation is marked as "failed" with a descriptive error
  And the audit log records the failure with timestamps and error codes
```

**Edge Cases**
- API rate limit (429) mid-simulation: backoff and resume from last completed agent
- Network disconnect during streaming: reconnect SSE within 5 seconds or mark simulation degraded
- Simulation exceeds 60-second SLA: complete but flag as "SLA_EXCEEDED" in metadata
- Concurrent simulations across workspaces must not interfere (tenant isolation)

**Functional Requirements**
- FR-001: Domain picker must list all supported threat domains (CNAPP + gap domains)
- FR-002: Agent swarm pipeline executes sequentially: ORCH -> SCOUT -> EXPLOIT -> DEFEND -> VALID -> REPORT
- FR-003: Each agent's output is validated against its JSON schema before passing downstream
- FR-004: Total simulation duration tracked and stored in `Simulation.durationMs`
- FR-005: Simulation status transitions: pending -> running -> completed | failed

**Data Model References**: DM-01 (Simulation), DM-02 (AgentInstance), DM-07 (AuditEntry)
**API Endpoint References**: `POST /api/v1/simulations`, `GET /api/v1/simulations/{id}`

---

#### US-002: Inspect Agent Anatomy in Real Time

**As a** Security Architect,
**I want to** inspect any agent's anatomy (working memory, episodic memory, goals, action loop) in real time,
**So that** I can understand and verify the agent's reasoning process during simulation.

**Priority**: MUST
**Sprint**: Sprint 2

**Acceptance Criteria**

```gherkin
Given a simulation is running
When I click on an agent in the agent roster panel
Then the Agent Anatomy Viewer opens showing 5 sections:
  | Section          | Content                                      |
  | Working Memory   | currentTask, findings[], hypotheses[], confidence |
  | Episodic Memory  | FIFO timeline of max 10 entries with timestamp, event, outcome, insight |
  | Goal Stack       | Ordered list of goals with priority and completion status |
  | Perception       | Current input context summary and token count |
  | Action Loop      | 4-stage ring (SENSE -> THINK -> PLAN -> ACT) with active stage highlighted |
  And all sections update in real time (< 200ms latency) via SSE stream

Given the agent transitions from THINK to PLAN in the action loop
When I am viewing the anatomy panel
Then the PLAN stage highlights with a pulse animation within 200ms

Given the agent has completed execution
When I view its anatomy
Then all sections show final state and a "Completed" badge appears
  And episodic memory shows the full execution history
```

**Edge Cases**
- Agent errors mid-execution: anatomy viewer shows error state with last known memory
- Rapid agent transitions: debounce UI updates to prevent DOM thrashing (16ms min)
- Multiple users viewing same agent: SSE fan-out must handle concurrent subscribers
- Agent has no episodic memory entries yet: show "No memory entries --- agent has not started"

**Functional Requirements**
- FR-006: SSE endpoint streams agent state changes as typed events
- FR-007: Episodic memory is FIFO with configurable max size (default 10)
- FR-008: Action loop visualization uses SVG ring with CSS animation
- FR-009: Working memory keys are schema-validated per agent role
- FR-010: Anatomy viewer is read-only; no user modification of agent state

**Data Model References**: DM-02 (AgentInstance)
**API Endpoint References**: `GET /api/v1/simulations/{id}/agents/{agentId}`, `GET /api/v1/simulations/{id}/agents/{agentId}/stream`

---

#### US-003: View Multi-Stage Exploit Chains with MITRE Mapping

**As a** Red Team Lead,
**I want to** see multi-stage exploit chains with MITRE ATT&CK technique mapping and blast radius,
**So that** I can assess the realistic attack surface and prioritize defenses.

**Priority**: MUST
**Sprint**: Sprint 2

**Acceptance Criteria**

```gherkin
Given a simulation has completed
When I navigate to the Findings tab
Then each finding displays:
  | Field              | Format                                     |
  | Exploit Chain      | Ordered list of steps with technique IDs    |
  | MITRE Techniques   | Clickable badges linking to attack.mitre.org |
  | Blast Radius       | Visual diagram showing direct impact, lateral paths, data at risk |
  | Severity           | CRITICAL/HIGH/MEDIUM/LOW with color coding  |
  | Confidence         | 0-100% per finding                         |

Given a finding has 3 exploit steps mapped to T1078.004, T1548.002, T1003.006
When I view the exploit chain
Then each step shows the technique ID, technique name, tactic category, and a description
  And clicking a technique badge opens the MITRE ATT&CK page in a new tab

Given a blast radius includes 12 directly impacted resources and 3 lateral paths
When I view the blast radius diagram
Then the diagram renders a graph with nodes (resources) and edges (attack paths)
  And directly impacted resources are highlighted in red
  And lateral paths are shown as dashed edges with traversal order
  And estimated financial impact and affected user count are displayed
```

**Edge Cases**
- Finding with no MITRE mapping: display "Unmapped" badge with warning icon
- Blast radius with 100+ nodes: virtualize graph rendering, enable zoom/pan
- Invalid MITRE technique ID (hallucinated by agent): validate against `T\d{4}(\.\d{3})?` regex; flag invalid IDs
- Findings across multiple cloud providers: group by provider with toggle

**Functional Requirements**
- FR-011: Exploit chain rendering supports 1-10 steps per chain
- FR-012: MITRE technique IDs validated against known format at ingestion time
- FR-013: Blast radius graph uses force-directed layout (D3.js or similar)
- FR-014: Findings sortable by severity, confidence, blast radius size
- FR-015: Export findings as JSON or PDF report

**Data Model References**: DM-04 (Finding), DM-05 (BlastRadius)
**API Endpoint References**: `GET /api/v1/simulations/{id}/findings`

---

#### US-004: View 12-Gate Validation Scorecard

**As a** Compliance Analyst,
**I want to** view a 12-gate validation scorecard with evidence per gate,
**So that** I can verify that simulated defenses meet compliance requirements.

**Priority**: MUST
**Sprint**: Sprint 3

**Acceptance Criteria**

```gherkin
Given a simulation has completed the VALID agent phase
When I navigate to the Validation tab
Then a grid of 12 gate cards is displayed, each showing:
  | Field      | Content                                    |
  | Gate Name  | e.g., "Cryptographic Hardening"            |
  | Status     | PASS (green) / FAIL (red) / PARTIAL (amber) |
  | Score      | 0-100% with progress bar                   |
  | Weight     | Contribution percentage to overall confidence |
  And an overall confidence score is displayed as a radial gauge (0-100%)

Given I click on "Gate 3: Lateral Movement Containment" showing PARTIAL (68%)
When the evidence panel expands
Then I see:
  - Evidence items with source agent references
  - Specific controls evaluated (e.g., "micro-segmentation: present", "zero-trust policies: partial")
  - Remediation hints for improving the score
  - Links to relevant findings

Given all 12 gates score PASS (>= threshold)
When the overall confidence is calculated
Then the confidence score is a weighted average >= 85%
  And a "Certified" badge appears on the simulation result
```

**Edge Cases**
- Gate with no evidence (agent failed): show "Insufficient Evidence" with score 0
- All gates FAIL: confidence score < 20%; show prominent "Critical Gaps Identified" warning
- Gate weights sum to != 100%: normalize weights at render time
- Partial gate with edge-case threshold (e.g., 69.5% rounds to 70%): use consistent rounding (Math.round)

**Functional Requirements**
- FR-016: 12 gates defined with immutable IDs (GATE-01 through GATE-12)
- FR-017: Gate weights configurable per threat domain (default: equal weights)
- FR-018: Evidence items link back to specific agent outputs and findings
- FR-019: Confidence score formula: `sum(gate.score * gate.weight) / sum(gate.weight)`
- FR-020: Gate definitions: Cryptographic Hardening, Identity Chain Integrity, Lateral Movement Containment, Data Exfiltration Prevention, Supply Chain Verification, AI/ML Model Integrity, OT/ICS Safety Assurance, Detection Coverage, Incident Response Readiness, Compliance Mapping, Recovery & Resilience, Red-Team Pass Rate

**Data Model References**: DM-03 (ValidationGate), DM-01 (Simulation)
**API Endpoint References**: `GET /api/v1/simulations/{id}/validation`, `GET /api/v1/simulations/{id}/confidence`

---

#### US-005: Spawn Specialist Agent Mid-Simulation

**As a** Security Architect,
**I want to** spawn a specialist agent mid-simulation for deep-dive analysis,
**So that** I can investigate a specific finding or attack path in more detail without restarting.

**Priority**: SHOULD
**Sprint**: Sprint 3

**Acceptance Criteria**

```gherkin
Given a simulation is running or has completed
When I select a finding or agent output and click "Spawn DeepDiver"
Then a new specialist agent (DEEP-XX) is created with:
  - Context from the parent agent's working memory
  - A focused sub-prompt targeting the selected finding/topic
  - An entry in the agent roster with "running" status
  And a spawn message is posted to the communication bus (type: "spawn", color: yellow)
  And the header stats bar "Active Agents" counter increments

Given I have already spawned 3 specialist agents in this simulation
When I attempt to spawn a 4th
Then the system displays "Maximum specialist agents reached (3)" and blocks the spawn
  And suggests reviewing existing specialist outputs first

Given the specialist agent completes analysis
When its output is ready
Then the output is appended to the simulation's findings and solutions
  And the agent status transitions to "complete"
  And token usage is tracked and added to the simulation's total cost
```

**Edge Cases**
- Spawning from a failed agent: inherit last valid working memory state
- Specialist agent itself fails: mark as error; do not cascade failure to parent simulation
- Spawn during VALID phase: specialist runs in parallel, does not block validation
- Token budget exceeded by spawn: warn user of cost estimate before confirming spawn

**Functional Requirements**
- FR-021: Max specialist agents per simulation: 3 (configurable per workspace plan)
- FR-022: Specialist prompt auto-generated from parent context + user-selected focus area
- FR-023: Spawn event recorded in audit log with parent agent reference
- FR-024: Specialist outputs merged into simulation results with `agentId` attribution
- FR-025: Token cost estimate displayed before user confirms spawn

**Data Model References**: DM-02 (AgentInstance), DM-08 (CommBusMessage), DM-07 (AuditEntry)
**API Endpoint References**: `POST /api/v1/simulations/{id}/agents/spawn`

---

#### US-006: View Confidence Score Before Deployment Approval

**As a** CISO,
**I want to** see a confidence score (0-100%) for every simulation output before approving deployment,
**So that** I can make risk-informed decisions based on validated evidence.

**Priority**: MUST
**Sprint**: Sprint 3

**Acceptance Criteria**

```gherkin
Given a simulation has completed
When I view the simulation summary
Then a confidence score (0-100%) is prominently displayed with:
  - Color coding: red (< 40%), amber (40-69%), green (>= 70%)
  - Breakdown by validation gate with individual gate contributions
  - Trend comparison with previous simulations in same domain (if available)

Given the confidence score is 72% (green)
When I click "Approve for Deployment"
Then the simulation is marked as "approved" with my user ID and timestamp
  And approval is recorded in the immutable audit log
  And downstream integrations (PR, SIEM, tickets) are unlocked for execution

Given the confidence score is 38% (red)
When I attempt to approve
Then the system shows a warning: "Confidence below threshold (40%). Approval requires override justification."
  And I must enter a text justification before approval proceeds
  And the override is recorded in the audit log with justification text
```

**Edge Cases**
- Confidence exactly at threshold boundary (e.g., 40.0%): treat as amber, no warning
- No previous simulation for trend comparison: show "No baseline --- first simulation in this domain"
- Approval by non-CISO role: blocked unless workspace RBAC grants approval permission
- Simulation re-run after approval: previous approval is not inherited; new approval required

**Functional Requirements**
- FR-026: Confidence score persisted in `Simulation.confidenceScore`
- FR-027: Approval workflow requires RBAC role `simulation:approve`
- FR-028: Low-confidence override requires justification text (min 20 characters)
- FR-029: Approval unlocks integration endpoints (PR push, SIEM forward, ticket creation)
- FR-030: Trend comparison queries last 5 simulations in same threat domain for same workspace

**Data Model References**: DM-01 (Simulation), DM-03 (ValidationGate), DM-07 (AuditEntry)
**API Endpoint References**: `GET /api/v1/simulations/{id}/confidence`, `GET /api/v1/simulations/{id}`

---

### Module A: CNAPP Simulation Layer

---

#### US-007: CSPM Simulation with Auto-Remediation IaC

**As a** Cloud Engineer,
**I want** CSPM simulation that checks 2800+ config rules and produces auto-remediation IaC,
**So that** I can identify and fix cloud misconfigurations before they become incidents.

**Priority**: MUST
**Sprint**: Sprint 4

**Acceptance Criteria**

```gherkin
Given I am on the CNAPP Simulation dashboard
When I select "CSPM Simulation" and choose a cloud provider (AWS/Azure/GCP)
  And I click "Run CSPM Simulation"
Then the system evaluates 2800+ configuration rules against the simulated environment
  And findings are categorized by severity (CRITICAL/HIGH/MEDIUM/LOW)
  And each finding includes auto-remediation IaC (Terraform or CloudFormation)
  And the simulation completes within 60 seconds

Given a finding for "S3 bucket public access enabled" (CRITICAL)
When I view the remediation artifact
Then I see valid Terraform HCL that adds `block_public_acls = true` and related settings
  And a "Copy to Clipboard" button and a "Push as PR" button are available

Given I select "Push as PR" for a remediation artifact
When the PR is created
Then the PR targets the configured repository and branch
  And the PR title includes the finding ID and rule code
  And the PR body includes finding description, severity, and compliance framework references
```

**Edge Cases**
- Rule returns false positive: user can mark finding as "suppressed" with justification
- IaC generation produces invalid syntax: validate Terraform/CF output with `terraform validate` equivalent check
- Cloud provider not supported for a rule: skip rule and note "Provider not applicable" in results
- 2800+ rules cause timeout: batch rules by service, parallelize evaluation, progressive result streaming

**Functional Requirements**
- FR-031: Rule engine stores 2800+ rules in `CSPMConfigRule` table
- FR-032: Rules tagged with compliance frameworks: NIST-800-53, ISO-27001, SOC2, PCI-DSS
- FR-033: Auto-remediation IaC generated per finding when available
- FR-034: Findings exportable as CSV, JSON, or PDF
- FR-035: Rule suppression tracked with user, reason, timestamp in audit log

**Data Model References**: DM-10 (CSPMConfigRule), DM-04 (Finding), DM-06 (Artifact)
**API Endpoint References**: `POST /api/v1/cnapp/cspm/simulate`, `GET /api/v1/cnapp/cspm/rules`

---

#### US-008: CIEM Privilege Escalation Simulation

**As a** Security Architect,
**I want** CIEM simulation that maps privilege escalation paths and generates least-privilege policies,
**So that** I can reduce identity-based attack surface.

**Priority**: MUST
**Sprint**: Sprint 4

**Acceptance Criteria**

```gherkin
Given I initiate a CIEM simulation
When the simulation completes
Then I see a privilege escalation graph showing:
  - All IAM principals (users, roles, service accounts)
  - Escalation paths (e.g., iam:PassRole -> lambda:CreateFunction -> admin)
  - Overprivileged principals highlighted with risk score
  And each escalation path is mapped to MITRE techniques (T1078, T1548)

Given a principal "deploy-role" has 47 unused permissions
When I view the least-privilege recommendation
Then the system generates a scoped IAM policy JSON with only the 12 permissions used in the last 90 days
  And a diff view shows removed vs. retained permissions
  And a "Push as PR" button is available for the policy update

Given no privilege escalation paths are found
When the simulation completes
Then the system displays "No escalation paths detected" with a green status
  And the CIEM validation gate scores PASS (100%)
```

**Edge Cases**
- Circular escalation paths (A -> B -> A): detect and flag as "cyclic dependency"
- Service-linked roles with immutable policies: mark as "non-remediable" with explanation
- Cross-account escalation: include assumed-role chains across account boundaries
- 1000+ principals: paginate graph, enable search/filter by principal name or risk score

**Functional Requirements**
- FR-036: Escalation graph supports BFS/DFS traversal with cycle detection
- FR-037: Least-privilege policy generated based on simulated usage patterns
- FR-038: Permission diff rendered as side-by-side or unified diff
- FR-039: Graph visualization supports zoom, pan, and principal search
- FR-040: Cross-account escalation paths include account ID labels

**Data Model References**: DM-04 (Finding), DM-05 (BlastRadius), DM-06 (Artifact)
**API Endpoint References**: `POST /api/v1/cnapp/ciem/simulate`

---

#### US-009: CDR Detection Coverage Simulation

**As a** SOC Analyst,
**I want** CDR simulation that tests detection coverage and calculates MTTR,
**So that** I can identify detection gaps and improve incident response time.

**Priority**: MUST
**Sprint**: Sprint 5

**Acceptance Criteria**

```gherkin
Given I initiate a CDR simulation
When the simulation completes
Then I see a detection coverage matrix showing:
  - Simulated attack techniques (from MITRE ATT&CK)
  - Detection status per technique: Detected / Missed / Partial
  - Coverage percentage (e.g., 78% of techniques detected)
  And MTTR is calculated for each detected technique

Given the coverage matrix shows T1059.001 (PowerShell) as "Missed"
When I view the gap detail
Then the system shows:
  - Recommended detection rules (Splunk SPL or Elastic KQL)
  - Recommended log sources to enable
  - Estimated MTTR improvement if detection is added

Given overall coverage is below 70%
When I view the CDR summary
Then a "Critical Detection Gaps" alert is shown
  And the Detection Coverage validation gate scores FAIL
  And recommendations are prioritized by MITRE tactic frequency
```

**Edge Cases**
- No SIEM integration configured: simulate coverage based on rule definitions alone
- Technique with multiple detection methods: show all methods with effectiveness ranking
- MTTR calculation with no historical data: estimate based on rule complexity and log volume
- CDR simulation for cloud-native vs. hybrid environments: separate coverage matrices

**Functional Requirements**
- FR-041: Coverage matrix covers MITRE ATT&CK techniques relevant to the threat domain
- FR-042: MTTR calculated as: detection_time + triage_time + containment_time (simulated)
- FR-043: Detection rules generated in Splunk SPL and Elastic KQL formats
- FR-044: Coverage gaps prioritized by technique prevalence in real-world attacks (MITRE frequency data)
- FR-045: CDR results feed into Detection Coverage validation gate (GATE-08)

**Data Model References**: DM-04 (Finding), DM-06 (Artifact), DM-03 (ValidationGate)
**API Endpoint References**: `POST /api/v1/cnapp/cdr/simulate`

---

#### US-010: Compliance Framework Mapping

**As a** Compliance Officer,
**I want** compliance framework mapping across NIST, ISO, SOC2, PCI-DSS,
**So that** I can demonstrate control coverage and identify compliance gaps.

**Priority**: MUST
**Sprint**: Sprint 5

**Acceptance Criteria**

```gherkin
Given a simulation has completed with findings
When I navigate to the Compliance tab
Then I see a framework selector with: NIST CSF 2.0, NIST 800-53 rev5, ISO 27001:2022, SOC2 Type II, PCI-DSS v4.0
  And selecting a framework shows a control-by-control mapping table

Given I select "NIST 800-53 rev5"
When the mapping renders
Then each control family (AC, AU, CM, IA, etc.) shows:
  - Total controls in family
  - Controls addressed by simulation findings
  - Controls with gaps (no finding coverage)
  - Compliance percentage per family
  And overall framework compliance percentage is calculated

Given I select "PCI-DSS v4.0" and the simulation did not cover Requirement 6 (Secure Systems)
When the mapping renders
Then Requirement 6 shows "Not Assessed" with a gray status
  And a recommendation to run a targeted simulation for that requirement is displayed
```

**Edge Cases**
- Finding maps to multiple frameworks: show cross-references in finding detail
- Framework version mismatch: default to latest version, allow version selection
- Custom compliance framework: support user-defined control sets (enterprise plan)
- Overlapping controls across frameworks: deduplicate in unified view

**Functional Requirements**
- FR-046: Compliance mapping engine supports 5 frameworks with full control catalogs
- FR-047: Mapping is bidirectional: finding -> controls and control -> findings
- FR-048: Compliance percentage calculated as: `addressed_controls / total_controls * 100`
- FR-049: Export compliance report as PDF with control evidence and gap analysis
- FR-050: Compliance results feed into Compliance Mapping validation gate (GATE-10)

**Data Model References**: DM-10 (CSPMConfigRule), DM-04 (Finding), DM-03 (ValidationGate)
**API Endpoint References**: `POST /api/v1/cnapp/compliance/map`, `GET /api/v1/cnapp/compliance/frameworks`

---

#### US-011: Vulnerability Management with Risk-Based Prioritization

**As a** Cloud Engineer,
**I want** vulnerability management that correlates CVE+EPSS+KEV with risk-based prioritization,
**So that** I can focus remediation on the vulnerabilities most likely to be exploited.

**Priority**: MUST
**Sprint**: Sprint 5

**Acceptance Criteria**

```gherkin
Given I initiate a vulnerability management simulation
When the simulation completes
Then vulnerabilities are listed with:
  | Field               | Source            |
  | CVE ID              | NVD               |
  | CVSS Score          | NVD               |
  | EPSS Probability    | FIRST.org EPSS    |
  | KEV Status          | CISA KEV catalog  |
  | Risk Priority Score | Composite (0-100) |
  And vulnerabilities are sorted by Risk Priority Score descending

Given CVE-2024-3094 has CVSS 10.0, EPSS 0.97, and is in CISA KEV
When the risk priority is calculated
Then the Risk Priority Score is >= 95 (weighted: CVSS 40%, EPSS 40%, KEV 20%)
  And the vulnerability is tagged as "CRITICAL --- Immediate Action Required"

Given a vulnerability has CVSS 7.5 but EPSS 0.01 and not in KEV
When the risk priority is calculated
Then the Risk Priority Score is moderate (~35-45)
  And the vulnerability is prioritized below higher-EPSS/KEV-listed CVEs
```

**Edge Cases**
- CVE has no EPSS data: use CVSS alone with a penalty modifier (0.8x weight)
- CVE is in KEV but CVSS is LOW: KEV status overrides to minimum MEDIUM priority
- Duplicate CVEs across packages: deduplicate, show all affected packages in one entry
- 10,000+ vulnerabilities: paginate with server-side filtering by severity/EPSS/KEV

**Functional Requirements**
- FR-051: Risk Priority Score formula: `(CVSS_normalized * 0.4) + (EPSS * 100 * 0.4) + (KEV_flag * 20)`
- FR-052: CISA KEV catalog refreshed daily (cached locally)
- FR-053: EPSS scores refreshed daily from FIRST.org API
- FR-054: Vulnerability findings include affected package, version, and fix version
- FR-055: Remediation artifacts generated as dependency update PRs

**Data Model References**: DM-04 (Finding), DM-06 (Artifact)
**API Endpoint References**: `POST /api/v1/cnapp/vulns/simulate`

---

### Module C: Gap Domain Coverage

---

#### US-012: Quantum Harvest Attack Simulation with PQC Migration Roadmap

**As a** Security Architect,
**I want** quantum harvest attack simulation with PQC migration roadmap,
**So that** I can prepare for "harvest now, decrypt later" threats and plan post-quantum cryptography transition.

**Priority**: MUST
**Sprint**: Sprint 6

**Acceptance Criteria**

```gherkin
Given I select "Quantum Harvest Attack" as the threat domain
When the simulation completes
Then I see:
  - Inventory of all cryptographic assets (TLS certs, stored data encryption, key exchanges)
  - Assets vulnerable to harvest-now-decrypt-later (HNDL) attacks
  - Estimated timeline for quantum threat (based on NIST PQC timeline)
  - PQC migration roadmap with phased approach

Given the simulation identifies RSA-2048 key exchange in 3 services
When I view the migration roadmap
Then each service shows:
  - Current algorithm (RSA-2048)
  - Recommended PQC algorithm (CRYSTALS-Kyber for KEM, CRYSTALS-Dilithium for signatures)
  - Migration complexity (Low/Medium/High)
  - Remediation IaC for algorithm upgrade
  And the Cryptographic Hardening validation gate (GATE-01) reflects PQC readiness

Given all cryptographic assets already use PQC-compliant algorithms
When the simulation completes
Then the system displays "PQC Ready" with 100% coverage
  And GATE-01 scores PASS
```

**Edge Cases**
- Hybrid TLS (classical + PQC): mark as "partial migration" with recommended completion steps
- Legacy systems that cannot upgrade: flag as "PQC Exception" requiring compensating controls
- Custom cryptographic implementations: warn "Custom crypto detected --- manual review required"
- Unknown algorithm in config: flag as "Unrecognized --- requires manual classification"

**Functional Requirements**
- FR-056: Cryptographic asset inventory scans TLS configs, KMS keys, encryption-at-rest settings
- FR-057: PQC recommendations align with NIST FIPS 203/204/205 standards
- FR-058: Migration roadmap generates phased plan with priority ordering
- FR-059: Remediation IaC includes algorithm parameter updates for AWS KMS, ACM, CloudFront
- FR-060: Results feed into Cryptographic Hardening gate (GATE-01)

**Data Model References**: DM-01 (Simulation), DM-04 (Finding), DM-06 (Artifact), DM-03 (ValidationGate)
**API Endpoint References**: `POST /api/v1/simulations`

---

#### US-013: Deepfake Identity Fraud Simulation

**As a** Red Team Lead,
**I want** deepfake identity fraud simulation testing FIDO2/passkey defenses,
**So that** I can validate that authentication systems resist synthetic media attacks.

**Priority**: SHOULD
**Sprint**: Sprint 6

**Acceptance Criteria**

```gherkin
Given I select "Deepfake Identity Fraud" as the threat domain
When the simulation completes
Then I see attack scenarios for:
  - Video injection for KYC/identity verification bypass
  - Voice cloning for vishing (voice phishing) attacks
  - Synthetic document generation for onboarding fraud
  And each scenario includes MITRE technique mapping (T1566, T1528)

Given the simulation tests FIDO2/passkey authentication
When liveness detection is configured
Then the simulation validates:
  - Passkey enrollment process resistance to injection
  - Liveness detection bypass attempts (pre-recorded video, 3D mask)
  - Fallback authentication path security (SMS OTP, email link)
  And the Identity Chain Integrity gate (GATE-02) reflects deepfake resilience

Given FIDO2 is not configured in the environment
When the simulation completes
Then the system flags "No phishing-resistant authentication detected"
  And recommends FIDO2/passkey deployment with implementation guide
  And GATE-02 scores FAIL for deepfake resilience
```

**Edge Cases**
- Environment uses proprietary biometric: simulate generic liveness bypass; flag for manual review
- Multiple authentication paths with mixed security: score each path independently
- FIDO2 configured but fallback allows SMS OTP: flag fallback as "bypass path"
- No identity verification system present: skip KYC scenarios, focus on auth testing

**Functional Requirements**
- FR-061: Deepfake attack scenarios cover video, voice, and document vectors
- FR-062: FIDO2/passkey validation checks enrollment, authentication, and recovery flows
- FR-063: Liveness detection test includes replay, injection, and presentation attack scenarios
- FR-064: Fallback authentication paths evaluated for downgrade attack resistance
- FR-065: Results feed into Identity Chain Integrity gate (GATE-02)

**Data Model References**: DM-01 (Simulation), DM-04 (Finding), DM-03 (ValidationGate)
**API Endpoint References**: `POST /api/v1/simulations`

---

#### US-014: Supply Chain Firmware Attack Simulation

**As a** Security Architect,
**I want** supply chain firmware attack simulation with SBOM+ validation,
**So that** I can identify firmware-level supply chain risks and validate software provenance.

**Priority**: SHOULD
**Sprint**: Sprint 7

**Acceptance Criteria**

```gherkin
Given I select "Supply Chain Firmware Attack" as the threat domain
When the simulation completes
Then I see:
  - SBOM (Software Bill of Materials) analysis with dependency tree
  - Firmware integrity validation against known-good hashes
  - Dependency confusion and typosquatting risk assessment
  - CI/CD pipeline tampering simulation results

Given the SBOM shows a dependency with no provenance attestation
When I view the finding
Then the system displays:
  - Package name, version, and source registry
  - "No SLSA provenance attestation found" warning
  - Recommended action: "Pin dependency hash, add provenance check to CI/CD"
  And the Supply Chain Verification gate (GATE-05) reflects the gap

Given all dependencies have SLSA Level 3 provenance
When the simulation completes
Then GATE-05 scores PASS
  And the system displays "Supply chain integrity verified"
```

**Edge Cases**
- SBOM not available: generate partial SBOM from available package manifests
- Transitive dependency vulnerability (depth > 5): show full chain with depth indicator
- Private registry dependencies: flag as "unverifiable provenance" unless registry is allow-listed
- SBOM format mismatch (CycloneDX vs SPDX): support both formats with auto-detection

**Functional Requirements**
- FR-066: SBOM parsing supports CycloneDX and SPDX formats
- FR-067: Firmware hash validation against known-good baseline database
- FR-068: Dependency confusion simulation checks public/private registry naming conflicts
- FR-069: CI/CD pipeline analysis covers GitHub Actions, GitLab CI, Jenkins
- FR-070: SLSA provenance level assessment (Level 0-4)

**Data Model References**: DM-01 (Simulation), DM-04 (Finding), DM-06 (Artifact), DM-03 (ValidationGate)
**API Endpoint References**: `POST /api/v1/simulations`

---

#### US-015: Autonomous AI Agent Attack Simulation

**As a** SOC Analyst,
**I want** autonomous AI agent attack simulation with circuit breaker validation,
**So that** I can test defenses against weaponized AI agents and verify containment mechanisms.

**Priority**: SHOULD
**Sprint**: Sprint 7

**Acceptance Criteria**

```gherkin
Given I select "Autonomous AI Agent Attack" as the threat domain
When the simulation completes
Then I see attack scenarios for:
  - Self-propagating AI worms exploiting tool-use APIs
  - Prompt injection chains across interconnected AI agents
  - AI agent privilege escalation via function calling abuse
  And each scenario shows containment validation results

Given the simulation tests circuit breaker mechanisms
When AI agent containment is evaluated
Then the system validates:
  - Token budget limits enforced per agent
  - Tool-use scope restrictions (file system, network, API access)
  - Human-in-the-loop gates for destructive actions
  - Kill switch functionality and response time
  And the AI/ML Model Integrity gate (GATE-06) reflects containment effectiveness

Given no circuit breaker is configured
When the simulation completes
Then the system flags "No AI agent containment mechanisms detected"
  And recommends implementing: token limits, tool scope restrictions, HITL gates
  And GATE-06 scores FAIL
```

**Edge Cases**
- AI agent system with custom orchestration: simulate generic attack patterns; flag for manual review
- Multiple AI agent frameworks (LangChain, AutoGPT, CrewAI): test each framework's containment
- AI agent with internet access: highest risk tier; simulate data exfiltration via tool use
- Circuit breaker with high latency (>5s response): flag as "insufficient containment speed"

**Functional Requirements**
- FR-071: AI agent attack scenarios cover 5 attack vectors: worm propagation, prompt injection, privilege escalation, data exfiltration, resource abuse
- FR-072: Circuit breaker validation measures: token limits, scope restrictions, HITL, kill switch
- FR-073: Containment response time measured and compared against SLA (target: <1s)
- FR-074: Results include recommended guardrail configurations for major AI frameworks
- FR-075: Results feed into AI/ML Model Integrity gate (GATE-06)

**Data Model References**: DM-01 (Simulation), DM-04 (Finding), DM-03 (ValidationGate)
**API Endpoint References**: `POST /api/v1/simulations`

---

#### US-016: OT/ICS Attack Simulation with Digital Twin

**As an** OT Security Engineer,
**I want** OT/ICS attack simulation against digital twin with Modbus/DNP3 whitelisting,
**So that** I can validate industrial control system defenses without risking production systems.

**Priority**: SHOULD
**Sprint**: Sprint 8

**Acceptance Criteria**

```gherkin
Given I select "OT/ICS Convergence Attack" as the threat domain
When the simulation completes
Then I see:
  - IT/OT bridge attack paths (from corporate network to ICS zone)
  - PLC manipulation scenarios with safety-instrumented system (SIS) bypass attempts
  - Purdue model compliance assessment (Levels 0-5)
  - Protocol whitelisting validation for Modbus TCP and DNP3

Given the simulation identifies a path from Level 4 (IT) to Level 1 (Basic Control)
When I view the attack path
Then the path shows:
  - Each Purdue level traversed with the exploit technique used
  - Points where segmentation should have blocked traversal
  - Safety-instrumented system bypass risk assessment
  And the OT/ICS Safety Assurance gate (GATE-07) reflects segmentation gaps

Given Modbus TCP whitelisting is properly configured
When the simulation validates protocol controls
Then the system confirms:
  - Only authorized function codes are allowed (read: FC01-04, write: FC05-06,15-16)
  - Source IP allowlisting is enforced
  - Anomalous function codes are blocked and logged
  And the finding states "Protocol whitelisting: COMPLIANT"
```

**Edge Cases**
- No OT/ICS environment defined: simulation runs in "advisory mode" with generic Purdue model
- Legacy PLC with no firmware update capability: flag as "perpetual vulnerability" with compensating control recommendations
- Dual-homed historian server bridging IT/OT: highest-risk finding with blast radius including both zones
- DNP3 Secure Authentication v5 configured: validate certificate-based auth implementation

**Functional Requirements**
- FR-076: Digital twin simulation models Purdue levels 0-5 with network segmentation
- FR-077: Modbus TCP function code whitelisting validation (FC01-FC16 classification)
- FR-078: DNP3 protocol validation includes Secure Authentication version check
- FR-079: SIS bypass simulation tests independent safety layer isolation
- FR-080: Results feed into OT/ICS Safety Assurance gate (GATE-07)

**Data Model References**: DM-01 (Simulation), DM-04 (Finding), DM-05 (BlastRadius), DM-03 (ValidationGate)
**API Endpoint References**: `POST /api/v1/simulations`

---

#### US-017: LLMjacking Detection with AI Spend Anomaly Monitoring

**As a** Cloud Engineer,
**I want** LLMjacking detection with AI spend anomaly monitoring,
**So that** I can detect unauthorized use of cloud AI resources and prevent cost abuse.

**Priority**: SHOULD
**Sprint**: Sprint 8

**Acceptance Criteria**

```gherkin
Given I select "LLMjacking Detection" as the threat domain
When the simulation completes
Then I see:
  - API key exposure risk assessment (environment variables, code repos, logs)
  - Model proxy hijacking scenarios (attacker proxying requests through stolen keys)
  - Resource theft patterns (crypto mining via LLM inference, token laundering)
  - AI spend anomaly detection rules

Given the simulation detects exposed API keys in 2 locations
When I view the findings
Then each location shows:
  - Where the key was found (e.g., "GitHub repo commit history", "CloudWatch log group")
  - Key type and permissions scope
  - Estimated exposure window
  - Remediation: key rotation command and secret manager migration IaC

Given I view the AI spend anomaly detection rules
When the rules are rendered
Then I see CloudWatch/Stackdriver alert configurations for:
  - Spend exceeding 2x daily baseline
  - Requests from unexpected IP ranges
  - Unusual model usage patterns (e.g., GPU-intensive models from CPU-only workloads)
  And rules are exportable as IaC (Terraform for CloudWatch Alarms)
```

**Edge Cases**
- Multiple AI providers (OpenAI + Anthropic + Bedrock): assess each provider independently
- API key with admin scope: highest severity; recommend immediate rotation
- Spend anomaly in shared account: correlate with IAM principal to identify abuser
- No AI services in use: simulation returns "No AI services detected --- N/A"

**Functional Requirements**
- FR-081: API key exposure scan covers: environment variables, code repos, CI/CD secrets, log groups
- FR-082: Spend anomaly detection rules generated for AWS CloudWatch, GCP Monitoring, Azure Monitor
- FR-083: Baseline spend calculation uses 30-day rolling average
- FR-084: Key rotation remediation includes IaC for secrets manager migration
- FR-085: LLMjacking findings include estimated financial impact of detected abuse

**Data Model References**: DM-01 (Simulation), DM-04 (Finding), DM-06 (Artifact)
**API Endpoint References**: `POST /api/v1/simulations`

---

#### US-018: Federated Identity Abuse Simulation

**As an** Identity Architect,
**I want** federated identity abuse simulation (Golden SAML, OIDC token binding),
**So that** I can test federated trust chains against nation-state TTPs (APT29 patterns).

**Priority**: SHOULD
**Sprint**: Sprint 8

**Acceptance Criteria**

```gherkin
Given I select "Federated Identity Abuse" as the threat domain
When the simulation completes
Then I see attack scenarios for:
  - Golden SAML: forging SAML assertions using compromised signing certificate
  - OIDC token forgery: exploiting weak token binding or missing audience validation
  - Federation trust abuse: pivot from compromised IdP to all relying parties
  And each scenario maps to APT29 TTPs (T1606.002, T1550.001)

Given the simulation identifies that SAML signing certificate is stored in ADFS server
When I view the finding
Then the finding shows:
  - Attack chain: Compromise ADFS -> Extract signing cert -> Forge SAML -> Access any RP
  - Blast radius: all relying parties trusting the IdP (enumerated)
  - Remediation: HSM-backed certificate, certificate rotation, SAML assertion monitoring
  And the Identity Chain Integrity gate (GATE-02) reflects federation trust security

Given OIDC token binding is properly configured with DPoP (Demonstrating Proof-of-Possession)
When the simulation validates token binding
Then the system confirms:
  - DPoP headers validated on all token endpoints
  - Token replay detection is active
  - Audience restriction is enforced per relying party
  And the finding states "OIDC Token Binding: COMPLIANT"
```

**Edge Cases**
- Multiple IdPs (Okta + Azure AD + Ping): simulate each IdP's trust chain independently
- SAML with encrypted assertions: test whether encryption compensates for signing cert risk
- IdP-initiated vs SP-initiated SSO: different attack surface for each flow
- Federated identity with MFA: test MFA bypass via session token theft post-authentication

**Functional Requirements**
- FR-086: Golden SAML simulation covers ADFS, Azure AD, Okta, and PingFederate
- FR-087: OIDC validation checks audience, issuer, nonce, DPoP, and token binding
- FR-088: Federation trust chain enumeration lists all relying parties per IdP
- FR-089: Remediation includes HSM migration IaC and certificate rotation procedures
- FR-090: APT29 TTP mapping references MITRE ATT&CK Group G0016

**Data Model References**: DM-01 (Simulation), DM-04 (Finding), DM-05 (BlastRadius), DM-03 (ValidationGate)
**API Endpoint References**: `POST /api/v1/simulations`

---

### Module D: Enterprise Features

---

#### US-019: Multi-Tenant Workspace Management with White-Label Branding

**As an** MSSP,
**I want** multi-tenant workspace management with white-label branding,
**So that** I can manage multiple client environments with my own branding.

**Priority**: MUST
**Sprint**: Sprint 9

**Acceptance Criteria**

```gherkin
Given I am a Platform Admin with MSSP plan
When I create a new workspace for a client
Then the workspace is fully isolated:
  - Separate simulation data, findings, artifacts
  - Separate user membership and RBAC
  - Separate API keys and integrations
  - No data leakage between workspaces

Given I configure white-label branding for workspace "AcmeSec"
When I set branding options
Then I can customize:
  | Setting            | Detail                           |
  | Logo               | Upload SVG/PNG (max 200KB)       |
  | Primary Color      | Hex color picker                 |
  | Company Name       | Displayed in header and reports  |
  | Favicon            | Upload ICO/PNG (max 50KB)        |
  | Email From Name    | Custom sender name for notifications |
  And all client-facing views and exported reports use the custom branding

Given a workspace member accesses the platform
When they view the interface
Then they see only the branding configured for their workspace
  And no OmniSec branding is visible (full white-label)
```

**Edge Cases**
- Workspace with no branding configured: show default OmniSec branding
- Logo upload exceeds size limit: reject with "File too large --- max 200KB" error
- Admin deletes workspace with active simulations: block deletion; require all simulations to be archived first
- Cross-workspace data query by admin: only via super-admin role with audit logging

**Functional Requirements**
- FR-091: Workspace isolation enforced at database level (row-level security or schema isolation)
- FR-092: White-label branding stored per workspace with logo, colors, company name
- FR-093: Exported reports (PDF) rendered with workspace branding
- FR-094: Workspace deletion requires archival of all simulation data first
- FR-095: Super-admin role can view workspace list and member counts but not workspace data

**Data Model References**: DM-09 (Workspace)
**API Endpoint References**: `GET /api/v1/workspaces`, `POST /api/v1/workspaces`, `PUT /api/v1/workspaces/{id}/branding`

---

#### US-020: RBAC with SSO and API Key Management

**As a** Platform Admin,
**I want** RBAC with SSO (Auth0/Okta) and API key management,
**So that** I can control access with enterprise-grade identity governance.

**Priority**: MUST
**Sprint**: Sprint 9

**Acceptance Criteria**

```gherkin
Given I configure SSO for my workspace
When I select Auth0 or Okta as the provider
Then I can configure:
  - SSO domain / tenant URL
  - Client ID and Client Secret
  - SAML or OIDC protocol
  And users can log in via SSO with automatic workspace assignment

Given I configure RBAC roles
When I assign roles to workspace members
Then the following roles are available:
  | Role                | Permissions                                                |
  | Viewer              | Read simulations, findings, reports                        |
  | Analyst             | Viewer + run simulations                                   |
  | Engineer            | Analyst + push PRs, manage integrations                    |
  | Approver            | Engineer + approve simulations for deployment              |
  | Admin               | Approver + manage workspace members, branding, settings    |
  | Super Admin         | Admin + manage all workspaces (MSSP only)                  |

Given I generate an API key with "Analyst" scope
When the key is used to call `POST /api/v1/simulations`
Then the simulation is created and attributed to the API key owner
  And the key cannot call `POST /api/v1/integrations/github/pr` (requires Engineer role)
  And API key usage is logged in the audit log
```

**Edge Cases**
- SSO provider outage: fallback to email/password if configured; otherwise show "SSO unavailable" with retry
- User removed from IdP but active in OmniSec: sync on next login attempt; deactivate stale sessions
- API key leaked: revoke immediately via admin panel; invalidate all active sessions for that key
- Role change mid-simulation: changes take effect on next API call; in-flight operations complete with original role

**Functional Requirements**
- FR-096: SSO integration supports SAML 2.0 and OIDC protocols
- FR-097: RBAC enforced at API middleware level with JWT claims validation
- FR-098: API keys scoped to specific RBAC roles
- FR-099: API key rotation without downtime (new key active before old key expires)
- FR-100: Session management with configurable idle timeout (default: 30 minutes)

**Data Model References**: DM-09 (Workspace)
**API Endpoint References**: `POST /api/v1/auth/sso/configure`, `POST /api/v1/auth/api-keys`

---

#### US-021: 1-Click Fix PRs to GitHub/GitLab

**As a** DevOps Engineer,
**I want** 1-click fix PRs pushed to GitHub/GitLab from simulation findings,
**So that** I can remediate issues directly in my code repository without manual copy-paste.

**Priority**: MUST
**Sprint**: Sprint 9

**Acceptance Criteria**

```gherkin
Given a simulation finding has a remediation artifact (Terraform/CloudFormation/OPA)
When I click "Push as PR" on the artifact
Then the system:
  - Creates a branch named `omnisec/fix/{finding-id}`
  - Commits the remediation IaC to the target file path
  - Opens a PR with:
    | PR Field     | Content                                    |
    | Title        | "[OmniSec] Fix: {finding title}"           |
    | Body         | Finding description, severity, MITRE techniques, compliance references |
    | Labels       | "security", "auto-remediation"             |
    | Reviewers    | Configured default reviewers for workspace |
  And the artifact status updates to "pushed"
  And the PR URL is displayed to the user

Given the GitHub/GitLab integration is not configured
When I click "Push as PR"
Then the system shows "Integration not configured" with a link to settings
  And the artifact remains in "generated" status

Given the PR creation fails (e.g., branch already exists)
When the error occurs
Then the system retries with a suffixed branch name (`omnisec/fix/{finding-id}-2`)
  And if retry fails, the error is displayed with "Copy to Clipboard" fallback
```

**Edge Cases**
- Target file does not exist in repo: create new file in PR with appropriate directory structure
- Repository is archived/read-only: fail gracefully with "Repository is read-only" message
- Multiple findings with same target file: batch into single PR with multiple commits
- GitLab self-hosted instance: support custom base URL configuration
- PR requires approval from CODEOWNERS: respect repository rules; do not auto-merge

**Functional Requirements**
- FR-101: GitHub integration via GitHub App (preferred) or Personal Access Token
- FR-102: GitLab integration via Project Access Token or Group Access Token
- FR-103: PR body includes: finding details, severity, MITRE ATT&CK references, compliance mapping
- FR-104: Branch naming convention: `omnisec/fix/{finding-id}`
- FR-105: PR creation recorded in audit log with artifact ID, repo URL, PR URL

**Data Model References**: DM-06 (Artifact), DM-04 (Finding), DM-07 (AuditEntry)
**API Endpoint References**: `POST /api/v1/integrations/github/pr`, `POST /api/v1/integrations/gitlab/mr`

---

#### US-022: SIEM Forwarding for Simulation Findings

**As a** SOC Manager,
**I want** simulation findings forwarded to Splunk/Elastic SIEM,
**So that** simulated threats are visible alongside real-time detections in our security monitoring.

**Priority**: SHOULD
**Sprint**: Sprint 10

**Acceptance Criteria**

```gherkin
Given I configure a SIEM integration (Splunk or Elastic)
When I provide the SIEM endpoint and authentication
Then the system validates connectivity with a test event
  And saves the integration configuration for the workspace

Given a simulation completes with findings
When I click "Forward to SIEM" (or auto-forwarding is enabled)
Then each finding is sent to the SIEM as a structured event:
  - Splunk: HTTP Event Collector (HEC) with JSON payload
  - Elastic: Elasticsearch Bulk API with ECS-compatible schema
  And each event includes: finding ID, severity, MITRE techniques, blast radius summary, simulation ID
  And delivery confirmation is logged in the audit log

Given the SIEM endpoint is unreachable
When forwarding is attempted
Then the system retries 3 times with exponential backoff
  And if all retries fail, findings are queued for retry (max 24 hours)
  And the user is notified "SIEM forwarding failed --- findings queued for retry"
```

**Edge Cases**
- SIEM rate limit hit: throttle to SIEM's documented limits; queue excess events
- Splunk HEC token expired: surface "Authentication failed" with link to re-configure
- Elastic index does not exist: auto-create index with OmniSec mapping template
- Findings contain PII: apply data masking rules configured per workspace before forwarding
- Duplicate forwarding (user clicks twice): deduplicate by finding ID + simulation ID

**Functional Requirements**
- FR-106: Splunk integration via HEC (HTTP Event Collector) with JSON format
- FR-107: Elastic integration via Bulk API with ECS (Elastic Common Schema) mapping
- FR-108: Auto-forwarding configurable per workspace (on/off, severity threshold)
- FR-109: Retry queue with 24-hour TTL for failed deliveries
- FR-110: Data masking rules configurable per workspace (regex-based field redaction)

**Data Model References**: DM-04 (Finding), DM-06 (Artifact), DM-07 (AuditEntry)
**API Endpoint References**: `POST /api/v1/integrations/siem/forward`

---

#### US-023: Auto-Create Remediation Tickets in Jira/ServiceNow

**As a** Project Manager,
**I want** remediation tickets auto-created in Jira/ServiceNow,
**So that** security findings are tracked in our existing project management workflow.

**Priority**: SHOULD
**Sprint**: Sprint 10

**Acceptance Criteria**

```gherkin
Given I configure a Jira or ServiceNow integration
When I provide the instance URL, project key, and credentials
Then the system validates connectivity by listing available projects
  And saves the integration configuration

Given a simulation completes with findings
When auto-ticketing is enabled (or I click "Create Ticket")
Then a ticket is created for each CRITICAL/HIGH finding:
  | Jira Field       | Content                                       |
  | Summary          | "[OmniSec] {finding title}"                   |
  | Description      | Finding details, MITRE mapping, remediation steps |
  | Priority         | Maps: CRITICAL->Highest, HIGH->High, MEDIUM->Medium |
  | Labels           | "omnisec", "security", severity                |
  | Assignee         | Configured default assignee or unassigned       |
  | Custom Fields    | Simulation ID, Finding ID, Confidence Score     |
  And the ticket URL is stored in the artifact record

Given I configure auto-ticketing with severity threshold "HIGH"
When a simulation produces 2 CRITICAL, 3 HIGH, and 5 MEDIUM findings
Then tickets are created for the 2 CRITICAL and 3 HIGH findings only
  And MEDIUM findings are skipped with note "Below severity threshold"
```

**Edge Cases**
- Jira project does not exist: fail with "Project not found" and list available projects
- ServiceNow assignment group not found: create ticket unassigned with warning
- Duplicate ticket (same finding re-simulated): check for existing ticket by finding ID custom field; update instead of create
- 50+ findings in one simulation: batch ticket creation with rate limiting per API provider
- Custom Jira workflow with required fields: surface "Required field missing" with field name

**Functional Requirements**
- FR-111: Jira integration via Jira REST API v3 with OAuth 2.0 or API token
- FR-112: ServiceNow integration via REST API with basic auth or OAuth 2.0
- FR-113: Severity-to-priority mapping configurable per workspace
- FR-114: Duplicate detection by finding ID custom field before creating new ticket
- FR-115: Batch creation with rate limiting (Jira: 10 req/s, ServiceNow: 5 req/s)

**Data Model References**: DM-04 (Finding), DM-06 (Artifact), DM-07 (AuditEntry)
**API Endpoint References**: `POST /api/v1/integrations/ticketing/create`

---

### Module E: Cross-Agent Communication

---

#### US-024: View Cross-Agent Communication Bus

**As a** Security Architect,
**I want to** see the full cross-agent communication bus with typed messages (info/solution/alert/spawn),
**So that** I can understand how agents collaborate and where key decisions are made.

**Priority**: MUST
**Sprint**: Sprint 2

**Acceptance Criteria**

```gherkin
Given a simulation is running
When I view the Communication Bus panel
Then I see a real-time scrolling feed of all agent messages with:
  | Field      | Display                                      |
  | Timestamp  | HH:MM:SS.ms                                  |
  | From       | Agent ID and codename                        |
  | To         | Target agent ID or "broadcast"               |
  | Type       | Color-coded badge: info=cyan, solution=green, alert=red, spawn=yellow |
  | Content    | Message summary (expandable for full detail)  |
  And the feed auto-scrolls to the latest message

Given I want to filter messages
When I select a message type filter (e.g., "alert" only)
Then only messages of that type are displayed
  And the filter state persists until changed

Given I want to filter by agent
When I click an agent in the roster
Then the comm bus shows only messages from/to that agent
  And a "Clear Filter" button restores the full feed

Given the simulation produces 200+ messages
When I scroll the comm bus
Then virtual scrolling is used (only visible messages are rendered)
  And scroll performance remains smooth (60fps)
```

**Edge Cases**
- Agent sends broadcast message to all: show "-> ALL" in the "To" field
- Message content exceeds 500 characters: truncate with "Show more" toggle
- Rapid burst of messages (10+ in 1 second): batch DOM updates via requestAnimationFrame
- SSE connection drops: reconnect within 5 seconds; show "Reconnecting..." indicator

**Functional Requirements**
- FR-116: Communication bus displays all inter-agent messages in chronological order
- FR-117: Message types: info, solution, alert, spawn --- each with distinct color
- FR-118: Filter by message type and/or agent (combinable)
- FR-119: Virtual scrolling for 500+ messages
- FR-120: SSE stream with automatic reconnection (5-second timeout)

**Data Model References**: DM-08 (CommBusMessage)
**API Endpoint References**: `GET /api/v1/simulations/{id}/comm-bus`, `GET /api/v1/simulations/{id}/comm-bus/stream`

---

#### US-025: Immutable Exportable Audit Log

**As an** Auditor,
**I want** an immutable, exportable audit log of all agent decisions and communications,
**So that** I can verify compliance and trace every action taken during a simulation.

**Priority**: MUST
**Sprint**: Sprint 3

**Acceptance Criteria**

```gherkin
Given a simulation has completed
When I navigate to the Audit Log tab
Then I see a chronological log of all events:
  | Field       | Content                                        |
  | Timestamp   | ISO 8601 with millisecond precision             |
  | Actor       | Agent ID, User ID, or "system"                 |
  | Actor Type  | "agent" / "user" / "system"                    |
  | Action      | e.g., "simulation.started", "agent.spawned", "finding.created", "approval.granted" |
  | Detail      | JSON object with action-specific context        |
  And the log is append-only (no entries can be modified or deleted)

Given I want to export the audit log
When I click "Export" and select a format (JSON, CSV, or PDF)
Then the full audit log is downloaded in the selected format
  And the export includes a SHA-256 hash of the log contents for integrity verification

Given a user attempts to modify an audit log entry via API
When the modification request is received
Then the API returns 403 Forbidden with "Audit log is immutable"
  And the modification attempt is itself logged as a security event
```

**Edge Cases**
- Audit log for long simulation (1000+ entries): paginate with server-side cursor
- Export of large audit log (>10MB): generate async and notify when ready for download
- Clock skew between agents: use server-side timestamp for all entries
- Audit log retention policy: configurable per workspace (default: 1 year)

**Functional Requirements**
- FR-121: Audit log stored in append-only table (no UPDATE or DELETE permissions)
- FR-122: All agent state transitions, messages, findings, and user actions recorded
- FR-123: Export formats: JSON, CSV, PDF with SHA-256 integrity hash
- FR-124: Pagination with cursor-based navigation (50 entries per page default)
- FR-125: Retention policy configurable per workspace plan (free: 30 days, pro: 1 year, enterprise: unlimited)

**Data Model References**: DM-07 (AuditEntry)
**API Endpoint References**: `GET /api/v1/simulations/{id}/audit-log`, `POST /api/v1/simulations/{id}/audit-log/export`

---

## Sprint Mapping

| Sprint | Duration | Module | User Stories | Focus |
|---|---|---|---|---|
| Sprint 1 | 2 weeks | B | US-001 | Simulation engine foundation, agent pipeline, domain picker |
| Sprint 2 | 2 weeks | B, E | US-002, US-003, US-024 | Agent anatomy viewer, exploit chains, comm bus |
| Sprint 3 | 2 weeks | B, E | US-004, US-005, US-006, US-025 | 12-gate validation, specialist spawn, confidence score, audit log |
| Sprint 4 | 2 weeks | A | US-007, US-008 | CSPM simulation (2800+ rules), CIEM privilege escalation |
| Sprint 5 | 2 weeks | A | US-009, US-010, US-011 | CDR coverage, compliance mapping, vuln management |
| Sprint 6 | 2 weeks | C | US-012, US-013 | Quantum harvest, deepfake identity |
| Sprint 7 | 2 weeks | C | US-014, US-015 | Supply chain firmware, autonomous AI agent attack |
| Sprint 8 | 2 weeks | C | US-016, US-017, US-018 | OT/ICS, LLMjacking, federated identity abuse |
| Sprint 9 | 2 weeks | D | US-019, US-020, US-021 | Multi-tenant workspaces, RBAC/SSO, GitHub/GitLab PRs |
| Sprint 10 | 2 weeks | D | US-022, US-023 | SIEM forwarding, Jira/ServiceNow tickets |

### Priority Summary

| Priority | Count | User Stories |
|---|---|---|
| MUST | 15 | US-001 through US-004, US-006 through US-011, US-012, US-019 through US-021, US-024, US-025 |
| SHOULD | 10 | US-005, US-013 through US-018, US-022, US-023 |
| COULD | 0 | --- |

### Critical Path

```
Sprint 1 (Sim Engine)
  -> Sprint 2 (Anatomy + Exploits + CommBus)
    -> Sprint 3 (Validation + Confidence + Audit)
      -> Sprint 4 (CSPM + CIEM) + Sprint 6 (Quantum + Deepfake) [parallel]
        -> Sprint 5 (CDR + Compliance + Vulns) + Sprint 7 (Supply Chain + AI Agent) [parallel]
          -> Sprint 8 (OT/ICS + LLMjacking + FedID)
            -> Sprint 9 (Multi-tenant + RBAC + PRs)
              -> Sprint 10 (SIEM + Ticketing)
```

Sprints 4+6 and 5+7 can run in parallel with separate teams, as Module A (CNAPP) and Module C (Gap Domains) share the simulation engine interface but have no direct code dependencies.

---

## Non-Functional Requirements

| Requirement | Target | Measurement |
|---|---|---|
| Simulation Latency | < 60 seconds (p95) | End-to-end pipeline timer |
| UI Response Time | < 100ms | Lighthouse Performance audit |
| Agent Anatomy Latency | < 200ms | SSE event delivery measurement |
| Concurrent Tenants | 100+ | Load test with isolated workspaces |
| Audit Log Immutability | 100% | No UPDATE/DELETE on audit table; DB trigger enforcement |
| Uptime SLA | 99.9% | Monthly availability measurement |
| MTTR for Platform | < 4 hours | Incident response tracking |
| Data Retention | 30d (free) / 1y (pro) / unlimited (enterprise) | Storage policy enforcement |
| API Rate Limit | 100 req/min per workspace | API gateway throttling |
| Export Performance | < 30 seconds for 10K-entry audit log | Export generation timer |

---

## Glossary

| Term | Definition |
|---|---|
| Agent Swarm | The set of AI agents (ORCH, SCOUT, EXPLOIT, DEFEND, VALID, REPORT) that collaborate to analyze a threat domain |
| Blast Radius | The set of resources, data, and users impacted by a successful exploit chain |
| CNAPP | Cloud-Native Application Protection Platform (CSPM + CIEM + CDR + Vulnerability Management) |
| Comm Bus | The cross-agent communication channel carrying typed messages (info, solution, alert, spawn) |
| Confidence Score | Weighted composite score (0-100%) derived from 12 validation gates |
| CSPM | Cloud Security Posture Management --- configuration rule checking |
| CIEM | Cloud Infrastructure Entitlement Management --- identity and access risk |
| CDR | Cloud Detection and Response --- threat detection coverage analysis |
| DeepDiver | A specialist agent spawned mid-simulation for focused analysis |
| EPSS | Exploit Prediction Scoring System (FIRST.org) |
| Golden SAML | Attack technique where a forged SAML assertion grants unauthorized access |
| HNDL | Harvest Now, Decrypt Later --- quantum computing threat vector |
| KEV | Known Exploited Vulnerabilities catalog (CISA) |
| LLMjacking | Unauthorized use of stolen LLM API credentials for resource abuse |
| MITRE ATT&CK | Adversarial Tactics, Techniques, and Common Knowledge framework |
| MTTR | Mean Time to Respond (detection + triage + containment) |
| PQC | Post-Quantum Cryptography |
| Purdue Model | Reference architecture for industrial network segmentation (Levels 0-5) |
| RBAC | Role-Based Access Control |
| SBOM | Software Bill of Materials |
| SIS | Safety-Instrumented System (OT/ICS) |
| SLSA | Supply chain Levels for Software Artifacts (provenance framework) |
| SSE | Server-Sent Events (real-time streaming protocol) |
| Validation Gate | One of 12 independent verification checkpoints in the simulation pipeline |
