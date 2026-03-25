# Swarm Autopsy --- Autonomous Threat Agent Intelligence Engine

**Created**: 2026-03-25
**Status**: Draft
**Scope**: New standalone product (scope change from Cloud Copilot CSPM platform)
**Architecture**: Client-side only, single HTML5 file, NO backend
**Go-Live Target**: Q3 2026 (3 phases, 6 sprints)
**Relationship to Cloud Copilot**: Sibling product under the same org; shares no runtime infrastructure with the CSPM platform. Future integration point: Swarm Autopsy threat analysis results can feed into Cloud Copilot's attack-path and drift-detection modules (Sprint 27-28 of CSPM roadmap).

---

## Table of Contents

1. [Product Overview](#product-overview)
2. [Architecture & Constraints](#architecture--constraints)
3. [Data Models](#data-models)
4. [Agent Specifications](#agent-specifications)
5. [API Contracts](#api-contracts)
6. [Phase 1: Core Agent Swarm (Sprint 1-2)](#phase-1--core-agent-swarm-sprint-1-2)
7. [Phase 2: Validation & Anatomy (Sprint 3-4)](#phase-2--validation--anatomy-sprint-3-4)
8. [Phase 3: Full Domain Coverage & Polish (Sprint 5-6)](#phase-3--full-domain-coverage--polish-sprint-5-6)
9. [Edge Cases & Error Handling](#edge-cases--error-handling)
10. [Success Metrics](#success-metrics)
11. [Non-Functional Requirements](#non-functional-requirements)
12. [Glossary](#glossary)

---

## Product Overview

**Swarm Autopsy** is an autonomous multi-agent threat intelligence simulation engine that decomposes complex cloud security threats across 9 domains using a 6-agent AI swarm powered by Anthropic Claude. It is a **client-side only** single-page HTML5 application --- no backend, no database, no frameworks. The user provides a Claude API key at runtime, selects a threat domain, and the swarm agents execute a sequential pipeline producing reconnaissance, exploit synthesis, defensive controls (IaC + detection rules), 12-gate validation, and an executive report.

### Core Value Proposition

- Simulate full threat lifecycle analysis in under 60 seconds
- Generate actionable IaC (Terraform/CloudFormation) and detection rules
- Validate defenses through 12 independent validation gates
- Map all findings to MITRE ATT&CK framework
- Zero infrastructure --- runs entirely in the browser

### Target Users

| Persona | Need |
|---|---|
| Cloud Security Engineer | Threat modeling with automated defensive output |
| Red Team Operator | Kill chain analysis and blast radius estimation |
| vCISO / MSP Analyst | Client-facing threat posture reports with validation scores |
| Security Architect | IaC policy generation and control gap identification |

---

## Architecture & Constraints

### Technology Stack

| Layer | Technology |
|---|---|
| Markup | HTML5 (single file) |
| Styling | CSS3 (embedded, CSS Grid + Custom Properties) |
| Logic | Vanilla JavaScript ES2022 (no transpilation) |
| AI Provider | Anthropic Claude API (claude-sonnet-4-20250514) |
| Typography | IBM Plex Mono (monospace) + Bebas Neue (headings) via Google Fonts |
| Deployment | Single `.html` file, any static host or local `file://` |

### Hard Constraints

| Constraint | Limit |
|---|---|
| API Budget | $500/month maximum Claude API spend |
| Credentials | API key held in JS memory only; never written to localStorage/cookies/disk |
| Backend | None. Zero server-side code. |
| Database | None. All state is ephemeral in-memory during session. |
| Frameworks | None. No React, Vue, Angular, jQuery, or build tools. |
| File Count | Single HTML file (CSS + JS embedded) |
| RAM | <50MB for up to 20 concurrent agent instances |
| UI Response | <100ms for any user interaction |
| Full Simulation | <60 seconds end-to-end for a single threat domain |

### Layout

Three-panel CSS Grid:

```
[Left Sidebar: 260px] | [Main Canvas: 1fr] | [Right Panel: 300px]
```

- Left sidebar: agent roster, threat domain selector, simulation controls
- Main canvas: active agent output, kill chain visualization, IaC code blocks
- Right panel: agent anatomy viewer, validation gate status, communication bus log

### Visual Style

- Background: near-black (#0a0a0f) with scanline overlay effect
- Primary accent: electric cyan (#00f0ff)
- Warning: amber (#ffb800)
- Error: red (#ff3040)
- Success: green (#00ff88)
- Typography: IBM Plex Mono for body/code, Bebas Neue for headings/labels
- Scanline: repeating-linear-gradient overlay at 2px intervals, 0.03 opacity

---

## Data Models

### DM-01: Agent

```typescript
interface Agent {
  id: string;                          // e.g. "ORCH-01"
  codename: string;                    // e.g. "SwarmMaster"
  role: AgentRole;                     // enum: orchestrator | scout | exploit | defend | validate | report | deepdiver
  status: AgentStatus;                 // enum: idle | thinking | streaming | complete | error
  workingMemory: WorkingMemory;
  episodicMemory: EpisodicMemoryEntry[];
  goalStack: Goal[];
  perceptionBuffer: PerceptionEvent[];
  actionLog: ActionEntry[];
  tokenUsage: { input: number; output: number; total: number };
  startedAt: number | null;            // Unix ms
  completedAt: number | null;
  errorMessage: string | null;
}
```

### DM-02: WorkingMemory

```typescript
interface WorkingMemory {
  currentObjective: string;
  contextWindow: string[];             // last N observations relevant to current task
  scratchpad: Record<string, unknown>; // agent-local temporary data
  upstreamInputs: MessageEnvelope[];   // messages received from prior agents
}
```

### DM-03: EpisodicMemoryEntry

```typescript
interface EpisodicMemoryEntry {
  timestamp: number;
  event: string;                       // human-readable description
  source: string;                      // agent ID or "user" or "system"
  data: unknown;                       // structured payload
}
```

### DM-04: Goal

```typescript
interface Goal {
  id: string;
  description: string;
  status: "pending" | "active" | "complete" | "failed";
  subGoals: Goal[];
  priority: number;                    // 1 = highest
}
```

### DM-05: MessageEnvelope

```typescript
interface MessageEnvelope {
  id: string;                          // UUID
  from: string;                        // agent ID
  to: string;                          // agent ID or "broadcast"
  type: MessageType;                   // enum below
  payload: unknown;
  timestamp: number;
  correlationId: string;               // links messages in same simulation run
}

type MessageType =
  | "task_assignment"
  | "recon_result"
  | "kill_chain"
  | "defense_package"
  | "validation_result"
  | "report_section"
  | "error"
  | "status_update"
  | "spawn_request"
  | "spawn_ack";
```

### DM-06: ThreatDomain

```typescript
interface ThreatDomain {
  id: string;                          // e.g. "quantum", "ai-poisoning"
  name: string;                        // human label
  description: string;
  mitreTactics: string[];              // MITRE ATT&CK tactic IDs
  defaultAttackVectors: string[];
  enabled: boolean;                    // false if not yet implemented
}
```

### DM-07: ValidationGate

```typescript
interface ValidationGate {
  id: string;                          // e.g. "VG-01"
  name: string;                        // e.g. "Cryptographic Hardening"
  category: string;
  score: "PASS" | "FAIL" | "PARTIAL" | "PENDING";
  weight: number;                      // 0-100, contribution to composite score
  findings: ValidationFinding[];
  evaluatedAt: number | null;
}

interface ValidationFinding {
  description: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  recommendation: string;
  mitreMapping: string | null;         // ATT&CK technique ID
}
```

### DM-08: SimulationRun

```typescript
interface SimulationRun {
  id: string;                          // UUID
  threatDomainId: string;
  status: "initializing" | "running" | "complete" | "error" | "cancelled";
  agents: Agent[];
  communicationBus: MessageEnvelope[];
  validationGates: ValidationGate[];
  report: ReportOutput | null;
  startedAt: number;
  completedAt: number | null;
  totalTokens: number;
  estimatedCost: number;               // USD
}
```

### DM-09: ReportOutput

```typescript
interface ReportOutput {
  executiveSummary: string;
  threatOverview: string;
  attackVectors: AttackVector[];
  killChain: KillChainStep[];
  blastRadius: BlastRadiusAssessment;
  defensiveControls: DefensePackage;
  validationSummary: ValidationSummary;
  mitreMapping: MitreMapping[];
  recommendations: Recommendation[];
  generatedAt: number;
}

interface AttackVector {
  id: string;
  name: string;
  description: string;
  likelihood: "very_high" | "high" | "medium" | "low" | "very_low";
  impact: "critical" | "high" | "medium" | "low";
  mitreTechniqueId: string;
}

interface KillChainStep {
  phase: string;                       // recon | weaponize | deliver | exploit | install | c2 | action
  description: string;
  indicators: string[];
  detectionOpportunities: string[];
}

interface BlastRadiusAssessment {
  directImpact: string[];
  lateralMovement: string[];
  dataExfiltrationRisk: "critical" | "high" | "medium" | "low";
  estimatedRecoveryHours: number;
}

interface DefensePackage {
  terraformModules: IaCBlock[];
  cloudFormationSnippets: IaCBlock[];
  detectionRules: DetectionRule[];
  playbookSteps: string[];
}

interface IaCBlock {
  name: string;
  description: string;
  code: string;
  provider: "terraform" | "cloudformation";
}

interface DetectionRule {
  name: string;
  description: string;
  query: string;                       // detection query (Sigma/KQL/SPL format)
  severity: "critical" | "high" | "medium" | "low";
  mitreTechniqueId: string;
  dataSource: string;
}

interface ValidationSummary {
  overallScore: number;                // 0-100
  passCount: number;
  failCount: number;
  partialCount: number;
  gateResults: ValidationGate[];
}

interface MitreMapping {
  techniqueId: string;
  techniqueName: string;
  tactic: string;
  relevance: string;
}

interface Recommendation {
  priority: number;
  title: string;
  description: string;
  effort: "low" | "medium" | "high";
  impact: "critical" | "high" | "medium" | "low";
}
```

### DM-10: PerceptionEvent

```typescript
interface PerceptionEvent {
  timestamp: number;
  type: "api_response" | "user_input" | "agent_message" | "system_event";
  data: unknown;
}
```

### DM-11: ActionEntry

```typescript
interface ActionEntry {
  timestamp: number;
  action: string;                      // human-readable
  target: string;                      // what was acted upon
  result: "success" | "failure";
  detail: string;
}
```

---

## Agent Specifications

### AGENT-01: ORCH-01 (SwarmMaster) --- Orchestrator

**Responsibility**: Receives user threat domain selection, decomposes the threat into sub-tasks, dispatches tasks to downstream agents in sequence, monitors pipeline health, handles errors and retries.

**Claude System Prompt Contract**: The system prompt must instruct Claude to:
1. Decompose the selected threat domain into 3-7 investigation sub-tasks
2. Output structured JSON with `taskId`, `assignedAgent`, `objective`, `context`
3. Never generate defensive controls (that is DEFEND-01's job)
4. Emit a `task_assignment` message for each sub-task

**Input**: User-selected `ThreatDomain` + optional user context string
**Output**: Array of `MessageEnvelope` with type `task_assignment`

### AGENT-02: SCOUT-01 (PathFinder) --- Reconnaissance

**Responsibility**: For each assigned recon task, enumerate attack vectors, entry points, and reconnaissance techniques relevant to the threat domain. Map findings to MITRE ATT&CK.

**Input**: `task_assignment` from ORCH-01
**Output**: `recon_result` containing `AttackVector[]` and initial MITRE mappings

### AGENT-03: EXPLOIT-01 (ExploitSynth) --- Kill Chain & Blast Radius

**Responsibility**: Synthesize recon data into a full kill chain (7 phases), estimate blast radius, identify lateral movement paths, and calculate data exfiltration risk.

**Input**: `recon_result` from SCOUT-01
**Output**: `kill_chain` containing `KillChainStep[]` + `BlastRadiusAssessment`

### AGENT-04: DEFEND-01 (ShieldWeaver) --- Controls & IaC

**Responsibility**: Generate defensive controls including Terraform modules, CloudFormation snippets, detection rules (Sigma format), and incident response playbook steps.

**Input**: `kill_chain` from EXPLOIT-01
**Output**: `defense_package` containing `DefensePackage`

### AGENT-05: VALID-01 (GateKeeper) --- 12-Gate Validation

**Responsibility**: Evaluate the defense package against all 12 validation gates. Each gate scores PASS/FAIL/PARTIAL with findings and recommendations.

**Input**: Full pipeline context (recon + kill chain + defense package)
**Output**: `validation_result` containing `ValidationGate[]` + `ValidationSummary`

### AGENT-06: REPORT-01 (ReportAgent) --- Synthesis & Executive Summary

**Responsibility**: Synthesize all upstream outputs into a cohesive `ReportOutput` with executive summary, full MITRE mapping, prioritized recommendations, and exportable format.

**Input**: All upstream `MessageEnvelope` messages
**Output**: `report_section` containing `ReportOutput`

### AGENT-07: DeepDiver (Spawned Specialist)

**Responsibility**: On-demand specialist agent spawned by ORCH-01 when a domain requires deeper analysis. Receives a narrow objective and returns a focused analysis.

**Spawn Trigger**: ORCH-01 sends `spawn_request`; system creates a new agent instance
**Input**: `spawn_request` with `{ objective, context, parentTaskId }`
**Output**: `recon_result` or `kill_chain` (depending on objective)
**Lifecycle**: Completes task, sends result, then terminates (status -> complete)

---

## API Contracts

### AC-01: Anthropic Claude API Request

All agent-to-Claude interactions use the Anthropic Messages API via `fetch()`.

```typescript
// Request shape sent to https://api.anthropic.com/v1/messages
interface ClaudeRequest {
  model: "claude-sonnet-4-20250514";
  max_tokens: number;                  // per-agent budget (see AC-02)
  system: string;                      // agent-specific system prompt
  messages: Array<{
    role: "user" | "assistant";
    content: string;
  }>;
  stream: true;                        // always stream for UI responsiveness
}

// Headers
// x-api-key: <user-provided key>
// anthropic-version: 2023-06-01
// content-type: application/json
// anthropic-dangerous-direct-browser-access: true
```

### AC-02: Per-Agent Token Budgets

| Agent | max_tokens | Rationale |
|---|---|---|
| ORCH-01 | 2,048 | Task decomposition is compact |
| SCOUT-01 | 4,096 | Recon needs detailed enumeration |
| EXPLOIT-01 | 4,096 | Kill chain + blast radius |
| DEFEND-01 | 8,192 | IaC code generation is verbose |
| VALID-01 | 4,096 | Gate evaluation structured output |
| REPORT-01 | 8,192 | Full synthesis report |
| DeepDiver | 4,096 | Focused deep-dive |

**Total per simulation (6 agents)**: ~30,720 max output tokens
**Estimated cost per run**: ~$0.08-$0.15 (assuming ~10K input + ~20K output tokens at Sonnet pricing)
**Monthly budget at $500**: ~3,300-6,250 simulation runs

### AC-03: Cross-Agent Communication Bus

The communication bus is an in-memory array of `MessageEnvelope` objects. No network calls --- agents read from and write to the shared array.

```typescript
interface CommunicationBus {
  messages: MessageEnvelope[];
  subscribe(agentId: string, types: MessageType[], callback: (msg: MessageEnvelope) => void): void;
  publish(envelope: MessageEnvelope): void;
  getHistory(correlationId: string): MessageEnvelope[];
  getMessagesFor(agentId: string): MessageEnvelope[];
}
```

### AC-04: Agent Lifecycle API (Internal)

```typescript
interface AgentRuntime {
  create(config: AgentConfig): Agent;
  start(agentId: string, input: MessageEnvelope[]): Promise<void>;
  cancel(agentId: string): void;
  getStatus(agentId: string): AgentStatus;
  destroy(agentId: string): void;
  spawn(parentId: string, objective: string, context: unknown): Agent; // DeepDiver creation
}
```

---

## Phase 1 --- Core Agent Swarm (Sprint 1-2)

**Goal**: Deliver the 6-agent sequential pipeline with Claude API integration, basic communication bus, and functional UI shell with the three-panel layout.

### User Stories

#### US-1.1 --- API Key Entry (Priority: P0)

As a security analyst, I want to enter my Anthropic Claude API key in a secure input field, so that the swarm agents can call the Claude API from my browser without any backend.

**Why this priority**: The entire application is non-functional without API key entry. This is a hard gate.

**Independent Test**: Open the HTML file, see an API key input field, enter a valid key, confirm the key is accepted and the "Start Simulation" button becomes enabled.

**Acceptance Scenarios**:

1. **Given** the application loads, **When** no API key is entered, **Then** the simulation controls are disabled and a prompt reads "Enter your Claude API key to begin".
2. **Given** the user enters an API key, **When** they click "Validate", **Then** the app sends a minimal test request to the Claude API and shows a green checkmark on success or a red error on failure.
3. **Given** a validated API key, **When** the user refreshes the page, **Then** the key is gone (not persisted to any storage) and must be re-entered.
4. **Given** the API key input field, **When** inspected in DOM, **Then** the input type is "password" and the value is not visible in any DOM attribute.

**Edge Cases**:
- Empty string submitted: show inline error "API key is required"
- Malformed key (not starting with `sk-ant-`): show inline error "Invalid key format"
- Network error during validation: show "Could not reach Anthropic API. Check your network."
- Key with trailing/leading whitespace: auto-trim before validation

---

#### US-1.2 --- Threat Domain Selection (Priority: P0)

As a security analyst, I want to select a threat domain from the available 9 domains, so that the swarm simulation focuses on a specific threat category.

**Why this priority**: Domain selection is the primary user input that drives the entire simulation.

**Independent Test**: With a valid API key, see a grid of 9 threat domain cards in the left sidebar, click one, confirm it highlights and the "Start Simulation" button activates.

**Acceptance Scenarios**:

1. **Given** a valid API key, **When** viewing the left sidebar, **Then** 9 threat domain cards are displayed with name, icon, and short description.
2. **Given** Phase 1 release, **When** viewing domains, **Then** only "Cloud Misconfig" and "Supply Chain" are enabled; the other 7 show a "Coming in Phase 3" badge and are not selectable.
3. **Given** the user selects "Cloud Misconfig", **When** the card is clicked, **Then** it receives a cyan border highlight, the main canvas shows domain details, and "Start Simulation" is enabled.
4. **Given** a domain is selected, **When** the user clicks a different domain, **Then** the previous selection is deselected and the new one is highlighted.

**Edge Cases**:
- User clicks a disabled domain: show tooltip "This domain will be available in Phase 3"
- User double-clicks a domain rapidly: treat as single selection (debounce)

---

#### US-1.3 --- Simulation Execution (Priority: P0)

As a security analyst, I want to click "Start Simulation" and watch the 6-agent pipeline execute sequentially, so that I receive a complete threat analysis without manual intervention.

**Why this priority**: This is the core product loop. Without sequential execution, no output is produced.

**Independent Test**: Select a domain, click Start, observe agents activating one by one in the left sidebar (ORCH -> SCOUT -> EXPLOIT -> DEFEND -> VALID -> REPORT), see streaming output in the main canvas, and a "Simulation Complete" state at the end.

**Acceptance Scenarios**:

1. **Given** a valid API key and selected domain, **When** the user clicks "Start Simulation", **Then** ORCH-01 activates (status: thinking), the left sidebar shows a green pulse on ORCH-01, and streaming output begins in the main canvas.
2. **Given** ORCH-01 completes, **When** it publishes `task_assignment` messages, **Then** SCOUT-01 automatically activates and begins processing.
3. **Given** the pipeline is running, **When** each agent completes, **Then** its status in the sidebar changes to "complete" (checkmark icon) and the next agent activates within 500ms.
4. **Given** all 6 agents complete, **When** REPORT-01 finishes, **Then** the simulation status changes to "complete", total time and token usage are displayed, and estimated cost is shown.
5. **Given** a running simulation, **When** the user clicks "Cancel", **Then** the current API request is aborted, all agents are set to "idle", and partial results remain visible.

**Edge Cases**:
- Claude API returns 429 (rate limit): retry with exponential backoff (1s, 2s, 4s), max 3 retries, then show error
- Claude API returns 500/503: show "Claude API is temporarily unavailable. Retry?"
- Claude returns malformed JSON in structured output: ORCH-01 attempts one re-prompt asking for valid JSON; if still malformed, mark task as failed and continue pipeline with degraded output
- Browser tab loses focus during simulation: simulation continues (no visibility API dependency)
- User closes tab during simulation: all state is lost (acceptable per ephemeral constraint)

---

#### US-1.4 --- Agent Streaming Output (Priority: P1)

As a security analyst, I want to see each agent's output stream in real time as Claude generates it, so that I understand the analysis as it unfolds rather than waiting for batch completion.

**Why this priority**: Streaming is critical for the <100ms perceived UI responsiveness target and user trust.

**Independent Test**: Start a simulation, observe text appearing character-by-character in the main canvas as each agent's Claude response streams in.

**Acceptance Scenarios**:

1. **Given** an agent is active, **When** Claude streams tokens, **Then** the main canvas renders each token within 50ms of receipt.
2. **Given** streaming output, **When** the output contains a code block (IaC), **Then** the code block is syntax-highlighted in real time.
3. **Given** streaming output, **When** the user scrolls up to read earlier output, **Then** auto-scroll pauses; a "Jump to latest" button appears at the bottom.
4. **Given** an agent completes streaming, **When** the next agent starts, **Then** a visual divider with the new agent's name and codename appears before its output.

---

#### US-1.5 --- Communication Bus Viewer (Priority: P1)

As a security analyst, I want to see the inter-agent message bus in the right panel, so that I understand how agents communicate and what data flows between them.

**Why this priority**: Transparency of agent communication is a key differentiator and trust-building feature.

**Independent Test**: During simulation, the right panel shows a chronological log of typed messages (task_assignment, recon_result, etc.) with sender/receiver labels and expandable payloads.

**Acceptance Scenarios**:

1. **Given** an agent publishes a message, **When** the message is added to the bus, **Then** it appears in the right panel within 100ms with sender ID, receiver ID, message type badge, and timestamp.
2. **Given** a message in the bus log, **When** the user clicks it, **Then** an expandable section shows the full JSON payload with syntax highlighting.
3. **Given** 20+ messages in the bus, **When** viewing the log, **Then** it scrolls smoothly and older messages remain accessible.

---

#### US-1.6 --- Agent Status Roster (Priority: P1)

As a security analyst, I want to see all 6 agents listed in the left sidebar with real-time status indicators, so that I know which agent is currently active, which have completed, and which are pending.

**Why this priority**: Status visibility is essential for the user to understand simulation progress.

**Independent Test**: Left sidebar shows 6 agent cards with codenames, each showing idle/thinking/streaming/complete/error status with appropriate visual treatment.

**Acceptance Scenarios**:

1. **Given** the simulation has not started, **When** viewing the agent roster, **Then** all 6 agents show "idle" status with dim styling.
2. **Given** an agent is calling Claude, **When** the API request is in flight, **Then** the agent card shows a pulsing cyan indicator and "thinking..." label.
3. **Given** an agent is streaming output, **When** tokens are arriving, **Then** the agent card shows an animated streaming indicator.
4. **Given** an agent encounters an error, **When** the error occurs, **Then** the agent card shows a red indicator with the error type (e.g., "API Error", "Timeout").
5. **Given** all agents complete, **When** the simulation is done, **Then** all 6 agents show green checkmarks and their execution time.

---

#### US-1.7 --- Three-Panel Layout Shell (Priority: P1)

As a security analyst, I want the application to render in a three-panel layout (sidebar | canvas | right panel) with the specified visual style, so that the interface is functional and visually coherent.

**Why this priority**: The layout is the structural foundation for all UI features.

**Independent Test**: Open the HTML file in Chrome, confirm three panels render at correct widths (260px | 1fr | 300px), scanline overlay is visible, fonts load correctly.

**Acceptance Scenarios**:

1. **Given** the page loads, **When** rendered at 1440px+ viewport, **Then** three panels are visible with the correct proportions.
2. **Given** the page loads, **When** inspecting computed styles, **Then** IBM Plex Mono is applied to body text and Bebas Neue to headings.
3. **Given** the page loads, **When** viewing the background, **Then** a subtle scanline overlay effect is visible at 2px intervals.
4. **Given** a viewport under 1024px, **When** viewing the page, **Then** the right panel collapses to a toggleable overlay and the sidebar becomes a hamburger menu.

**Edge Cases**:
- Google Fonts CDN unreachable: CSS falls back to `monospace` and `sans-serif`
- Print view: scanline overlay is hidden in `@media print`

---

### Phase 1 Data Flow

```
User Input (API Key + Domain)
        |
        v
  [ORCH-01: SwarmMaster]
  - Decomposes threat into sub-tasks
  - Publishes task_assignment messages
        |
        v
  [SCOUT-01: PathFinder]
  - Enumerates attack vectors
  - Publishes recon_result
        |
        v
  [EXPLOIT-01: ExploitSynth]
  - Builds kill chain
  - Estimates blast radius
  - Publishes kill_chain
        |
        v
  [DEFEND-01: ShieldWeaver]
  - Generates IaC + detection rules
  - Publishes defense_package
        |
        v
  [VALID-01: GateKeeper]
  - Runs 12-gate validation
  - Publishes validation_result
        |
        v
  [REPORT-01: ReportAgent]
  - Synthesizes executive report
  - Publishes report_section
        |
        v
  [UI: Simulation Complete]
```

---

## Phase 2 --- Validation & Anatomy (Sprint 3-4)

**Goal**: Implement the full 12-gate validation engine with detailed scoring, the Agent Anatomy Viewer for inspecting agent internals, and on-demand DeepDiver agent spawning.

### User Stories

#### US-2.1 --- 12-Gate Validation Dashboard (Priority: P0)

As a security analyst, I want to see all 12 validation gates with PASS/FAIL/PARTIAL scores after a simulation completes, so that I understand the strength and gaps of the generated defenses.

**Why this priority**: Validation is the quality assurance layer; without it, generated defenses are unverified.

**Independent Test**: After a simulation completes, the right panel (or a dedicated tab in main canvas) shows 12 gates, each with a colored badge (green/red/yellow), score, and expandable findings.

**Acceptance Scenarios**:

1. **Given** a completed simulation, **When** viewing the validation dashboard, **Then** all 12 gates are listed with their name, score (PASS/FAIL/PARTIAL), and weight.
2. **Given** a gate scored FAIL, **When** the user expands it, **Then** they see specific findings with severity, description, recommendation, and MITRE mapping.
3. **Given** all 12 gates evaluated, **When** viewing the summary, **Then** a composite score (0-100) is displayed as a radial gauge with color coding (green >70, yellow 40-70, red <40).
4. **Given** the validation dashboard, **When** hovering over a gate, **Then** a tooltip shows the gate's evaluation criteria.

**The 12 Validation Gates**:

| Gate ID | Gate Name | Weight | Evaluates |
|---|---|---|---|
| VG-01 | Cryptographic Hardening | 10 | Encryption at rest/transit, key management, certificate lifecycle |
| VG-02 | Attack Surface Reduction | 10 | Exposed services, open ports, unnecessary permissions |
| VG-03 | IaC Policy Correctness | 8 | Terraform/CF syntax validity, security best practices |
| VG-04 | Detection Completeness | 8 | Coverage of kill chain phases by detection rules |
| VG-05 | Automated Response Speed | 7 | Playbook contains automated containment steps |
| VG-06 | Blast Radius Containment | 9 | Segmentation, isolation, blast radius limiting controls |
| VG-07 | Lateral Movement Prevention | 9 | Network segmentation, zero-trust controls |
| VG-08 | Credential Lifecycle | 8 | Rotation, MFA, least-privilege, credential storage |
| VG-09 | Cross-Account Coverage | 6 | Multi-account controls, organization-wide policies |
| VG-10 | Continuous Monitoring | 7 | Logging, alerting, anomaly detection coverage |
| VG-11 | IR Playbook Completeness | 9 | Incident response steps for each attack phase |
| VG-12 | Red-Team Pass Rate | 9 | Simulated adversary would be detected/blocked |

---

#### US-2.2 --- Agent Anatomy Viewer (Priority: P1)

As a security analyst, I want to inspect any agent's internal state (working memory, episodic memory, goal stack, perception buffer, action log), so that I understand how the agent reached its conclusions.

**Why this priority**: Explainability is critical for trust in AI-generated security analysis.

**Independent Test**: Click an agent in the left sidebar roster, see the right panel switch to an anatomy viewer showing 5 tabs: Working Memory, Episodic Memory, Goal Stack, Perception, Actions.

**Acceptance Scenarios**:

1. **Given** a completed agent, **When** the user clicks its card in the sidebar, **Then** the right panel switches to the anatomy viewer for that agent.
2. **Given** the anatomy viewer, **When** viewing Working Memory, **Then** the current objective, context window entries, and scratchpad contents are displayed.
3. **Given** the anatomy viewer, **When** viewing the Goal Stack, **Then** goals are displayed as a nested tree with status badges (pending/active/complete/failed).
4. **Given** the anatomy viewer, **When** viewing Episodic Memory, **Then** a timeline of events is displayed chronologically with source labels and expandable data.
5. **Given** the anatomy viewer, **When** viewing Actions, **Then** a log of actions is displayed with timestamp, target, result (success/failure), and detail.

---

#### US-2.3 --- DeepDiver Agent Spawning (Priority: P1)

As a security analyst, I want ORCH-01 to spawn specialist DeepDiver agents when a threat domain requires deeper analysis, so that the simulation can go deeper on specific sub-topics without overloading a single agent.

**Why this priority**: Spawning enables depth-first analysis without breaking the sequential pipeline.

**Independent Test**: During a simulation, observe ORCH-01 deciding to spawn a DeepDiver (visible in the bus log), see the new agent appear in the sidebar roster, complete its task, and terminate.

**Acceptance Scenarios**:

1. **Given** ORCH-01 determines a sub-task needs deep analysis, **When** it publishes a `spawn_request`, **Then** a new DeepDiver agent appears in the sidebar with a unique ID (e.g., "DEEP-01").
2. **Given** a spawned DeepDiver, **When** it completes its task, **Then** its result is published to the bus and its status changes to "complete".
3. **Given** the maximum agent limit (20), **When** ORCH-01 tries to spawn another agent, **Then** the spawn is rejected and a warning appears in the bus log: "Agent limit reached (20). Skipping deep dive."
4. **Given** a spawned DeepDiver, **When** the user clicks it in the roster, **Then** the anatomy viewer shows its working memory including the parent task context.

**Edge Cases**:
- DeepDiver API call fails: result is omitted from pipeline, ORCH-01 logs a warning, pipeline continues
- Multiple DeepDivers spawned simultaneously: execute sequentially (not parallel) to respect API rate limits
- DeepDiver takes >30 seconds: timeout and terminate with partial result

---

#### US-2.4 --- Validation Gate Detail & Remediation Guidance (Priority: P2)

As a security analyst, I want each failed validation gate to include specific remediation steps and IaC snippets, so that I can act on the gaps immediately.

**Why this priority**: Actionable output is the difference between an audit report and a useful tool.

**Independent Test**: Expand a FAIL gate, see remediation steps with code snippets that can be copied to clipboard.

**Acceptance Scenarios**:

1. **Given** a FAIL gate with findings, **When** the user expands a finding, **Then** a remediation section shows step-by-step guidance with IaC code.
2. **Given** a remediation code block, **When** the user clicks "Copy", **Then** the code is copied to clipboard and a "Copied!" toast appears.
3. **Given** a PARTIAL gate, **When** expanded, **Then** the findings distinguish between what passed and what needs attention.

---

## Phase 3 --- Full Domain Coverage & Polish (Sprint 5-6)

**Goal**: Enable all 9 threat domains, add documentation, export functionality, and production polish.

### User Stories

#### US-3.1 --- All 9 Threat Domains Enabled (Priority: P0)

As a security analyst, I want all 9 threat domains to be selectable and produce domain-specific analysis, so that I can simulate threats across the full taxonomy.

**Why this priority**: Full domain coverage is the complete product promise.

**Independent Test**: All 9 domain cards are selectable. Running a simulation on each produces domain-appropriate attack vectors, kill chains, and defenses.

**Acceptance Scenarios**:

1. **Given** Phase 3 release, **When** viewing the domain selector, **Then** all 9 domains are enabled and selectable.
2. **Given** each domain, **When** a simulation completes, **Then** the attack vectors, kill chain, and defenses are specific to that domain (not generic).
3. **Given** the "Quantum" domain, **When** simulated, **Then** the output references post-quantum cryptography, Harvest Now Decrypt Later, quantum key distribution.
4. **Given** the "AI Poisoning" domain, **When** simulated, **Then** the output references training data poisoning, model supply chain, adversarial inputs.
5. **Given** the "Deepfake" domain, **When** simulated, **Then** the output references synthetic media detection, voice cloning, identity verification bypass.
6. **Given** the "Agentic AI" domain, **When** simulated, **Then** the output references tool-use abuse, prompt injection, autonomous agent compromise.
7. **Given** the "OT/ICS" domain, **When** simulated, **Then** the output references SCADA, PLCs, Purdue model, safety instrumented systems.
8. **Given** the "LLMjacking" domain, **When** simulated, **Then** the output references stolen API keys, proxy abuse, credential stuffing for AI services.
9. **Given** the "Federated Identity" domain, **When** simulated, **Then** the output references SAML/OIDC attacks, token forgery, IdP compromise.

**9 Threat Domains (Full List)**:

| ID | Name | Key Topics |
|---|---|---|
| TD-01 | Quantum Computing Threats | PQC, HNDL, QKD, crypto agility |
| TD-02 | AI Model Poisoning | Training data attacks, backdoors, supply chain |
| TD-03 | Deepfake & Synthetic Media | Voice cloning, video synthesis, identity bypass |
| TD-04 | Software Supply Chain | Dependency confusion, typosquatting, build pipeline |
| TD-05 | Agentic AI Threats | Tool-use abuse, prompt injection, autonomous compromise |
| TD-06 | OT/ICS Security | SCADA, PLCs, Purdue model, safety systems |
| TD-07 | LLMjacking | Stolen API keys, proxy abuse, cost exploitation |
| TD-08 | Federated Identity Attacks | SAML/OIDC, token forgery, IdP compromise |
| TD-09 | Cloud Misconfiguration | S3 exposure, IAM sprawl, network misconfig |

---

#### US-3.2 --- Report Export (Priority: P1)

As a security analyst, I want to export the complete simulation report as a structured document, so that I can share it with stakeholders who are not using the tool.

**Why this priority**: Report export enables the tool to produce artifacts consumed outside the browser session.

**Independent Test**: After simulation, click "Export Report", receive a downloadable file containing the full analysis.

**Acceptance Scenarios**:

1. **Given** a completed simulation, **When** the user clicks "Export JSON", **Then** a JSON file is downloaded containing the full `ReportOutput` structure.
2. **Given** a completed simulation, **When** the user clicks "Export Markdown", **Then** a `.md` file is downloaded with formatted sections for executive summary, kill chain, defenses, validation, and recommendations.
3. **Given** the exported report, **When** opened, **Then** it includes simulation metadata: domain, timestamp, agent execution times, token usage, estimated cost.

---

#### US-3.3 --- Simulation History (In-Session) (Priority: P2)

As a security analyst, I want to run multiple simulations in a single session and switch between their results, so that I can compare threat analyses across domains.

**Why this priority**: Comparison across domains is valuable for comprehensive threat modeling.

**Independent Test**: Run two simulations (Cloud Misconfig, then Supply Chain). A tab bar shows both runs. Clicking between them restores the full output.

**Acceptance Scenarios**:

1. **Given** a completed simulation, **When** the user starts a new simulation, **Then** the previous results are preserved in a tab bar above the main canvas.
2. **Given** 2+ completed simulations, **When** the user clicks a tab, **Then** the canvas, bus log, and validation dashboard restore to that simulation's data.
3. **Given** 10 simulations in a session, **When** viewing the tab bar, **Then** tabs are scrollable horizontally and the active tab is highlighted.

**Edge Cases**:
- Memory usage with 10+ simulations: oldest simulation data is summarized (full ReportOutput kept, streaming logs trimmed) if heap approaches 50MB
- Tab close: confirm dialog "Discard results for [domain]?"

---

#### US-3.4 --- Cost Tracking & Budget Guard (Priority: P1)

As a security analyst, I want to see cumulative API cost for my session and receive a warning when approaching budget limits, so that I do not accidentally overspend.

**Why this priority**: The $500/month constraint makes cost visibility essential.

**Independent Test**: After each simulation, the header shows cumulative session cost. Setting a budget threshold triggers a warning dialog before the next run.

**Acceptance Scenarios**:

1. **Given** any simulation completes, **When** viewing the header, **Then** the cumulative token count and estimated USD cost for the session are displayed.
2. **Given** the user sets a session budget (e.g., $5.00) via settings, **When** the cumulative cost reaches 80% of the budget, **Then** a yellow warning banner appears: "You've used 80% of your session budget."
3. **Given** the cumulative cost reaches 100% of the budget, **When** the user tries to start a new simulation, **Then** a blocking dialog appears: "Session budget exhausted. Increase your budget or start a new session."

---

#### US-3.5 --- MITRE ATT&CK Mapping Visualization (Priority: P2)

As a security analyst, I want to see a visual MITRE ATT&CK matrix highlighting the techniques covered by the simulation, so that I can identify coverage gaps.

**Why this priority**: MITRE ATT&CK is the industry standard; visual mapping increases report credibility.

**Independent Test**: After simulation, a MITRE matrix view highlights covered techniques with color-coded cells.

**Acceptance Scenarios**:

1. **Given** a completed simulation, **When** the user opens the MITRE view, **Then** a matrix grid shows tactics (columns) and techniques (rows) with highlighted cells for mapped techniques.
2. **Given** a highlighted technique, **When** the user hovers over it, **Then** a tooltip shows the technique name, ID, and which agent identified it.
3. **Given** the MITRE view, **When** detection rules exist for a technique, **Then** the cell shows a shield icon indicating defensive coverage.

---

#### US-3.6 --- IaC Code Block Interaction (Priority: P1)

As a security engineer, I want to copy individual Terraform or CloudFormation code blocks from the defense package, so that I can paste them directly into my infrastructure repository.

**Why this priority**: Copy-to-clipboard for IaC is the primary actionable output path.

**Independent Test**: In the defense output section, each IaC block has a "Copy" button, a language label (Terraform/CF), and syntax highlighting.

**Acceptance Scenarios**:

1. **Given** the defense package output, **When** viewing IaC blocks, **Then** each block shows a language tag, description, and "Copy to Clipboard" button.
2. **Given** the user clicks "Copy", **When** the clipboard is updated, **Then** a toast notification "Copied to clipboard" appears for 2 seconds.
3. **Given** Terraform code blocks, **When** rendered, **Then** HCL syntax is highlighted with appropriate colors.
4. **Given** CloudFormation code blocks, **When** rendered, **Then** YAML/JSON syntax is highlighted.

---

## Edge Cases & Error Handling

### EH-01: Network Failures

| Scenario | Behavior |
|---|---|
| Complete network loss during simulation | Pause pipeline, show "Network disconnected. Simulation paused." Resume on reconnect (retry last failed request). |
| DNS resolution failure for api.anthropic.com | Show "Cannot reach Anthropic API. Check DNS and firewall settings." |
| CORS error | Show "CORS error detected. Ensure your API key supports browser access (anthropic-dangerous-direct-browser-access header)." |
| SSL certificate error | Show "SSL error connecting to Anthropic API." |

### EH-02: API Errors

| Scenario | Behavior |
|---|---|
| 401 Unauthorized | Clear API key validation state. Show "API key is invalid or expired. Please re-enter." |
| 429 Rate Limited | Exponential backoff: 1s, 2s, 4s. Max 3 retries. Then show "Rate limited by Anthropic. Wait 60 seconds and retry." |
| 500/503 Server Error | Retry once after 2s. If still failing: "Claude API is temporarily unavailable." |
| Request timeout (>30s no response) | Abort request. Show "Request timed out. The threat domain may be too complex. Try again or select a simpler domain." |
| Streaming interrupted mid-response | Attempt to parse partial JSON. If parseable, continue pipeline with degraded data + warning. If not parseable, mark agent as error. |

### EH-03: Data Validation

| Scenario | Behavior |
|---|---|
| Agent returns non-JSON when JSON expected | Re-prompt once: "Your response must be valid JSON. Re-generate." If still invalid, extract text content as best-effort and continue. |
| Agent returns empty response | Re-prompt once. If still empty, mark agent as error, skip to next agent in pipeline. |
| Agent returns response exceeding token budget | Accept the truncated response (Anthropic API handles this). Log warning. |
| Kill chain missing required phases | VALID-01 flags in VG-04 (Detection Completeness) as PARTIAL or FAIL. |

### EH-04: Browser Environment

| Scenario | Behavior |
|---|---|
| LocalStorage/SessionStorage disabled | Application works (no persistence needed). No error shown. |
| JavaScript disabled | Show `<noscript>` message: "Swarm Autopsy requires JavaScript." |
| Viewport < 768px | Collapse to single-column layout with tabs for sidebar/canvas/right panel. |
| Heap memory approaching 50MB | Trim oldest simulation's streaming logs. Show "Memory optimized: oldest streaming logs cleared." |
| Browser crashes / tab refresh | All state lost. Show welcome screen. Acceptable per design. |

### EH-05: Agent Pipeline Failures

| Scenario | Behavior |
|---|---|
| ORCH-01 fails completely | Simulation cannot proceed. Show "Orchestrator failed. Unable to decompose threat. Please retry." |
| SCOUT-01 fails | EXPLOIT-01 receives empty recon. It generates a generic kill chain with warning: "Recon data unavailable. Analysis is based on general threat model." |
| DEFEND-01 fails | VALID-01 evaluates with no defense package. All gates score FAIL. REPORT-01 notes the gap. |
| VALID-01 fails | REPORT-01 generates report without validation scores. Warning: "Validation was not completed." |
| REPORT-01 fails | Raw pipeline outputs remain visible. "Report generation failed. Review individual agent outputs above." |

---

## Success Metrics

### Product Metrics

| Metric | Target | Measurement Method |
|---|---|---|
| Simulation completion rate | >95% | Completed simulations / started simulations |
| End-to-end simulation time | <60 seconds | Timestamp delta from Start click to Report complete |
| Average validation composite score | >55/100 | Mean composite score across all completed simulations |
| IaC code block copy rate | >40% of sessions | Sessions where at least one IaC block was copied |
| Session duration | >10 minutes | Time from page load to last interaction |
| Multi-domain exploration rate | >30% of sessions | Sessions with 2+ different domain simulations |

### Performance Metrics

| Metric | Target | Measurement Method |
|---|---|---|
| UI interaction latency | <100ms | Time from click/keystroke to visual response |
| Streaming token render latency | <50ms per token | Time from SSE event to DOM update |
| Page load time (cold) | <3 seconds on 50Mbps | First contentful paint + Google Fonts load |
| Memory usage (single simulation) | <30MB | Chrome DevTools heap snapshot |
| Memory usage (10 simulations) | <50MB | Chrome DevTools heap snapshot |

### Cost Metrics

| Metric | Target | Measurement Method |
|---|---|---|
| Cost per simulation | <$0.15 | Total tokens * Sonnet pricing |
| Monthly budget utilization | <$500 | Cumulative session costs |
| Token efficiency (output/input ratio) | >1.5 | Output tokens / input tokens |

### Quality Metrics

| Metric | Target | Measurement Method |
|---|---|---|
| IaC syntax validity | >90% | Terraform `validate` / CF lint pass rate on generated code |
| MITRE mapping accuracy | >85% | Spot-check: mapped techniques are relevant to the domain |
| Detection rule relevance | >80% | Spot-check: rules would trigger on described attack patterns |
| Kill chain coherence | >90% | Spot-check: phases logically follow from recon data |

---

## Non-Functional Requirements

### NFR-01: Security

1. API key must never be written to `localStorage`, `sessionStorage`, `cookies`, IndexedDB, or any persistent storage.
2. API key must be held in a JavaScript closure, not on `window` or any globally accessible object.
3. The HTML file must set `<meta http-equiv="Content-Security-Policy">` restricting `script-src` to `'self'` and `connect-src` to `https://api.anthropic.com https://fonts.googleapis.com https://fonts.gstatic.com`.
4. No third-party analytics, tracking, or telemetry scripts.
5. All Claude API responses are treated as untrusted content; any rendered HTML must be escaped.

### NFR-02: Accessibility

1. All interactive elements must be keyboard-navigable (Tab order, Enter/Space activation).
2. Color is never the sole indicator of state (icons and labels accompany color badges).
3. Minimum contrast ratio of 4.5:1 for body text against background.
4. ARIA labels on agent status indicators and validation gate badges.
5. Screen reader announcements for simulation state changes.

### NFR-03: Browser Compatibility

1. Primary target: Chrome 120+, Firefox 120+, Edge 120+, Safari 17+.
2. ES2022 features used: top-level await, private class fields, structuredClone. No transpilation.
3. No IE11 support.

### NFR-04: Performance Budgets

1. HTML file size: <500KB (including embedded CSS + JS, excluding fonts).
2. First Contentful Paint: <2 seconds on broadband.
3. No layout shifts after initial render (CLS = 0).
4. No main-thread blocking >50ms (Long Tasks API).

### NFR-05: Offline Capability

1. Once the HTML file and fonts are loaded, the only network dependency is the Anthropic API.
2. The UI shell (layout, agent roster, domain cards) renders fully without any network call.
3. If cached by a service worker or browser cache, the app opens instantly.

---

## Glossary

| Term | Definition |
|---|---|
| Agent | An autonomous AI unit with a specific role in the threat analysis pipeline. Each agent calls Claude once per simulation. |
| Swarm | The collection of all agents operating together on a single threat simulation. |
| Communication Bus | An in-memory message queue connecting agents. All inter-agent data flows through typed MessageEnvelope objects. |
| Threat Domain | A category of security threat (e.g., Quantum, Supply Chain) that defines the scope of a simulation. |
| Validation Gate | One of 12 independent quality checks applied to the defense package. Each gate evaluates a specific security dimension. |
| Kill Chain | A 7-phase model of an attack lifecycle: recon, weaponize, deliver, exploit, install, C2, action on objectives. |
| Blast Radius | The estimated scope of damage from a successful exploit, including lateral movement and data exfiltration potential. |
| IaC | Infrastructure as Code. Machine-readable definitions of cloud infrastructure (Terraform HCL or AWS CloudFormation YAML/JSON). |
| DeepDiver | A specialist agent spawned on-demand by ORCH-01 for focused analysis of a narrow sub-topic. |
| Anatomy Viewer | A UI panel showing an agent's internal cognitive state: memory, goals, perceptions, and actions. |
| Composite Score | A weighted aggregate (0-100) of all 12 validation gate scores, representing overall defense quality. |
| Scanline | A visual CSS overlay effect mimicking CRT monitor scan lines, applied to the application background. |
| Ephemeral State | All application state exists only in browser memory for the current session. Refresh = reset. |
| MITRE ATT&CK | Industry-standard framework for classifying adversary tactics, techniques, and procedures (TTPs). |
| Sigma | An open standard for writing detection rules that can be converted to various SIEM query languages. |

---

## Appendix A: Phase-Sprint Mapping

| Phase | Sprints | Scope | Domains Enabled |
|---|---|---|---|
| Phase 1 | Sprint 1-2 | 6 agents + Claude API + comm bus + layout | Cloud Misconfig, Supply Chain |
| Phase 2 | Sprint 3-4 | 12-gate validation + anatomy viewer + spawning | (same 2) |
| Phase 3 | Sprint 5-6 | All 9 domains + export + history + polish | All 9 |

## Appendix B: Prompt Engineering Contract

Each agent's system prompt must follow this template:

```
You are {CODENAME} ({AGENT_ID}), a specialized security analysis agent in the Swarm Autopsy threat intelligence system.

ROLE: {role description}
THREAT DOMAIN: {domain name and context}
UPSTREAM DATA: {summary of data from prior agents}

OUTPUT FORMAT: You MUST respond with valid JSON matching this schema:
{JSON schema for this agent's output type}

CONSTRAINTS:
- Stay within your role. Do not generate outputs assigned to other agents.
- All MITRE ATT&CK references must use valid technique IDs (T####.###).
- IaC code must be syntactically valid for the specified provider.
- If you lack sufficient context, state "INSUFFICIENT_CONTEXT" for that field rather than fabricating data.
```

## Appendix C: File Structure (Single HTML)

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="...">
  <title>Swarm Autopsy</title>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;700&family=Bebas+Neue&display=swap" rel="stylesheet">
  <style>
    /* ~150-200 lines: CSS Grid layout, custom properties, scanline overlay,
       agent cards, validation gates, typography, responsive breakpoints */
  </style>
</head>
<body>
  <!-- ~100-150 lines: semantic HTML structure for 3-panel layout -->
  <script type="module">
    /* ~2000-3000 lines organized as ES2022 classes:
       - AgentRuntime (create, start, cancel, spawn)
       - CommunicationBus (publish, subscribe, history)
       - ClaudeClient (stream, abort, cost tracking)
       - ValidationEngine (12 gates)
       - UIRenderer (DOM updates, streaming, anatomy viewer)
       - SimulationController (orchestration state machine)
       - DomainRegistry (9 threat domains with prompts)
       - CostTracker (token counting, budget guards)
    */
  </script>
</body>
</html>
```
