# Swarm Autopsy — Sprint-by-Sprint Build Plan

## Product: Autonomous Threat Agent Intelligence Engine
## Architecture: Single HTML file, client-side only, Vanilla JS ES2022, Claude API
## Timeline: 3 Phases / 6 Sprints (2-week sprints)

---

## Phase 1 — MVP (Sprints 1-2)

---

### Sprint 1: Foundation + Agent Engine

**Goal:** Establish the single-file scaffold, global state management, agent state machine, and the first orchestrator agent with full Claude API integration.

#### Deliverables

| # | Deliverable | Acceptance Criteria | Story Points |
|---|-------------|-------------------|--------------|
| 1.1 | Single HTML file scaffold | File loads in Chrome/Firefox/Safari with no errors; contains `<style>`, `<script>`, and markup sections | 2 |
| 1.2 | 3-panel CSS grid layout | Grid renders as `260px | 1fr | 300px`; responsive collapse at `<900px` to stacked layout; no horizontal scroll at 1280px+ | 3 |
| 1.3 | Typography setup | IBM Plex Mono loaded from Google Fonts for body/code; Bebas Neue loaded for headings/stats; fallback stack defined | 1 |
| 1.4 | Scanline overlay effect | CSS `::after` pseudo-element on `body` renders animated scanline; toggleable via `STATE.visualEffects` flag; does not block pointer events | 2 |
| 1.5 | Global STATE object | `window.STATE` initialised with `{ agents: Map, messages: [], solutions: [], validationGates: [], running: false, currentDomain: null, startTime: null }`; frozen shape via Object.seal in dev | 3 |
| 1.6 | Agent state machine | Each agent transitions through `idle -> running -> done \| error`; invalid transitions throw; state change fires `CustomEvent('agent-state-change')` on `document` | 5 |
| 1.7 | `callClaude()` function | Accepts `{ model, systemPrompt, userMessage, maxTokens, temperature }`; returns parsed JSON or text; handles 429/500 with exponential backoff (max 3 retries); streams via `ReadableStream` if `stream: true` | 5 |
| 1.8 | ORCH-01 (SwarmMaster) agent | System prompt loaded; receives threat domain input; outputs structured JSON with `{ threatModel, agentPlan, priorityOrder }`; result stored in `STATE.agents.get('ORCH-01').output` | 5 |
| 1.9 | Header stats bar | Displays 4 live counters: Active Agents, Messages, Solutions, Gates Passed; updates on `state-change` events; uses CSS `counter()` or direct DOM update | 3 |
| 1.10 | Threat domain selector | `<select>` dropdown with 9 domain options; fires `domain-selected` event; disabled while `STATE.running === true` | 2 |
| 1.11 | Run Autopsy button | Click triggers full state reset via `resetState()`; sets `STATE.running = true`; starts ORCH-01; disabled during run; shows spinner | 3 |
| 1.12 | Agent roster panel (left column) | Lists all registered agents with ID, name, status badge (idle/running/done/error); updates reactively on `agent-state-change` events | 3 |

**Total Story Points: 37**

#### Files / Functions to Create

```
swarm-autopsy.html          (single file — all code lives here)

// Inside <script>:
// --- State Management ---
function createInitialState()        // Returns fresh STATE object
function resetState()                // Clears and re-initialises STATE
function sealState(state)            // Object.seal for shape enforcement

// --- Agent Engine ---
function createAgent(id, name, systemPrompt, config)   // Factory
function transitionAgent(agentId, newState)             // State machine
function runAgent(agentId, input)                       // Execute agent
function getAgentOutput(agentId)                        // Read result

// --- Claude API ---
async function callClaude({ model, systemPrompt, userMessage, maxTokens, temperature, stream })
async function callClaudeWithRetry(params, retries=3)   // Backoff wrapper

// --- UI Rendering ---
function renderStatsBar()            // Header counters
function renderAgentRoster()         // Left panel
function renderDomainSelector()      // Dropdown
function bindRunButton()             // Button handler

// --- Events ---
// CustomEvent: 'agent-state-change'   { detail: { agentId, from, to } }
// CustomEvent: 'domain-selected'      { detail: { domain } }
// CustomEvent: 'state-reset'          { detail: {} }
```

#### Dependencies
- None (first sprint)

#### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Claude API rate limits during dev | Medium | High | Implement backoff in Sprint 1; cache responses locally during testing |
| CSS grid inconsistency in Safari | Low | Medium | Test early; add `-webkit` prefixes |
| Google Fonts FOUT/FOIT | Low | Low | Use `font-display: swap`; define fallback stack |

---

### Sprint 2: Full Agent Pipeline + Communication Bus

**Goal:** Implement all 6 agents, wire the sequential pipeline, build the cross-agent communication bus, and display solutions.

#### Deliverables

| # | Deliverable | Acceptance Criteria | Story Points |
|---|-------------|-------------------|--------------|
| 2.1 | SCOUT-01 (PathFinder) agent | System prompt defined; receives ORCH-01 output; returns `{ attackPaths: [...], entryPoints: [...], lateralMoves: [...] }`; stored in agent output | 3 |
| 2.2 | EXPLOIT-01 (ExploitSynth) agent | System prompt defined; receives SCOUT-01 paths; returns `{ exploitChains: [...], cves: [...], payloads: [...] }`; each chain has severity score | 3 |
| 2.3 | DEFEND-01 (ShieldWeaver) agent | System prompt defined; receives EXPLOIT-01 chains; returns `{ mitigations: [...], iacPatches: [...], detectionRules: [...] }`; each mitigation maps to an exploit | 3 |
| 2.4 | VALID-01 (GateKeeper) agent | System prompt defined; receives all prior agent outputs; returns `{ gates: [...], overallScore: number, passed: boolean }`; validates defence coverage | 5 |
| 2.5 | REPORT-01 (ReportAgent) agent | System prompt defined; receives entire pipeline context; returns structured markdown report with executive summary, technical details, remediation steps | 3 |
| 2.6 | Sequential pipeline orchestration | `runPipeline()` executes ORCH -> SCOUT -> EXPLOIT -> DEFEND -> VALID -> REPORT in order; each agent receives prior agent's output; pipeline halts on agent error; total time tracked | 5 |
| 2.7 | Cross-agent communication bus (right panel) | Right column displays scrollable message feed; each message shows `{ timestamp, fromAgent, toAgent, type, summary }`; auto-scrolls to latest | 5 |
| 2.8 | Message type color coding | `info` = cyan `#00ffd5`, `solution` = green `#39ff14`, `alert` = red `#ff3131`, `spawn` = yellow `#ffe066`; type badge rendered next to each message | 2 |
| 2.9 | Solution panel (bottom center) | Collapsible panel below main content; lists all solutions with title, confidence, associated agent; clickable to expand full detail | 3 |
| 2.10 | Working memory updates per agent | Each agent's working memory (`currentTask`, `findings`, `hypotheses`) updated in real-time during execution; visible in agent roster on hover/click | 3 |

**Total Story Points: 35**

#### Files / Functions to Create

```
// Inside <script> (additions to swarm-autopsy.html):

// --- Agent Definitions ---
function createScoutAgent()          // SCOUT-01 factory + prompt
function createExploitAgent()        // EXPLOIT-01 factory + prompt
function createDefendAgent()         // DEFEND-01 factory + prompt
function createValidAgent()          // VALID-01 factory + prompt
function createReportAgent()         // REPORT-01 factory + prompt

// --- Pipeline ---
async function runPipeline(domain)   // Sequential orchestration
function buildAgentInput(agentId, priorOutputs)  // Input assembly
function handlePipelineError(agentId, error)     // Error recovery

// --- Communication Bus ---
function postMessage({ from, to, type, content })  // Send message
function renderCommBus()             // Right panel rendering
function scrollCommBus()             // Auto-scroll to bottom
function filterMessages(type)        // Filter by message type

// --- Solutions ---
function addSolution(solution)       // Push to STATE.solutions
function renderSolutionPanel()       // Bottom panel
function expandSolution(index)       // Detail view

// --- Working Memory ---
function updateWorkingMemory(agentId, key, value)   // Per-agent memory
function renderWorkingMemory(agentId)                // Tooltip/panel
```

#### Dependencies
- Sprint 1: STATE object, agent state machine, `callClaude()`, UI scaffold

#### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Pipeline latency exceeds 60s target | High | High | Parallelize SCOUT + EXPLOIT where possible in Phase 3; reduce `maxTokens` |
| Agent output schema mismatch between stages | Medium | High | Define JSON schemas per agent; validate output before passing downstream |
| Comm bus DOM thrashing with rapid messages | Medium | Medium | Batch DOM updates with `requestAnimationFrame`; use document fragment |

---

## Phase 2 — Full Feature (Sprints 3-4)

---

### Sprint 3: 12-Gate Validation Engine

**Goal:** Implement the full 12-gate validation framework with scoring, regex parsing, UI board, and confidence calculation.

#### Deliverables

| # | Deliverable | Acceptance Criteria | Story Points |
|---|-------------|-------------------|--------------|
| 3.1 | Gate definitions data structure | Array of 12 gate objects with `{ id, name, description, category, weight, threshold }`; immutable via `Object.freeze` | 2 |
| 3.2 | Gate 1: Cryptographic Hardening | Validates PQC readiness, key rotation policy, cipher suite selection; scored PASS/FAIL/PARTIAL | 2 |
| 3.3 | Gate 2: Identity Chain Integrity | Validates MFA enforcement, session management, credential rotation; scored PASS/FAIL/PARTIAL | 2 |
| 3.4 | Gate 3: Lateral Movement Containment | Validates network segmentation, micro-segmentation, zero-trust policies; scored PASS/FAIL/PARTIAL | 2 |
| 3.5 | Gate 4: Data Exfiltration Prevention | Validates DLP controls, egress filtering, encryption-at-rest/in-transit; scored PASS/FAIL/PARTIAL | 2 |
| 3.6 | Gate 5: Supply Chain Verification | Validates SBOM presence, dependency signing, provenance attestation; scored PASS/FAIL/PARTIAL | 2 |
| 3.7 | Gate 6: AI/ML Model Integrity | Validates model signing, input validation, adversarial robustness; scored PASS/FAIL/PARTIAL | 2 |
| 3.8 | Gate 7: OT/ICS Safety Assurance | Validates Purdue model compliance, safety-instrumented systems, protocol whitelisting; scored PASS/FAIL/PARTIAL | 2 |
| 3.9 | Gate 8: Detection Coverage | Validates SIEM rule coverage, log completeness, alert fidelity >95%; scored PASS/FAIL/PARTIAL | 2 |
| 3.10 | Gate 9: Incident Response Readiness | Validates playbook existence, MTTR targets, communication plan; scored PASS/FAIL/PARTIAL | 2 |
| 3.11 | Gate 10: Compliance Mapping | Validates NIST CSF, ISO 27001, SOC2 control mapping; scored PASS/FAIL/PARTIAL | 2 |
| 3.12 | Gate 11: Recovery & Resilience | Validates backup strategy, RTO/RPO targets, chaos engineering; scored PASS/FAIL/PARTIAL | 2 |
| 3.13 | Gate 12: Red-Team Pass Rate | Validates simulated attack success rate <5%, purple team coverage; scored PASS/FAIL/PARTIAL | 2 |
| 3.14 | Regex parsing of VALID-01 output | Parse VALID-01 text output using regex patterns to extract gate results: `/GATE[-_](\d{1,2}):\s*(PASS|FAIL|PARTIAL)/gi`; fallback to JSON parsing if structured | 3 |
| 3.15 | Validation board UI | Grid of 12 gate cards; each shows name, status icon (check/x/warning), progress bar (0-100%); color-coded: PASS=green, FAIL=red, PARTIAL=amber | 5 |
| 3.16 | Overall confidence score | Weighted average of all 12 gates (0-100%); displayed as large radial progress indicator; color shifts from red (<40%) to amber (<70%) to green (>=70%) | 3 |
| 3.17 | Gate evidence display | Click a gate card to expand and show evidence text, relevant agent findings, and remediation suggestions | 3 |

**Total Story Points: 39**

#### Files / Functions to Create

```
// Inside <script> (additions to swarm-autopsy.html):

// --- Gate Definitions ---
const VALIDATION_GATES = Object.freeze([...])    // 12 gate configs
function getGateById(gateId)                      // Lookup helper
function getGateWeight(gateId)                    // Weight accessor

// --- Gate Scoring ---
function scoreGate(gateId, agentOutputs)          // Evaluate single gate
function scoreAllGates(agentOutputs)              // Evaluate all 12
function parseGateResults(validatorOutput)         // Regex + JSON parser
function calculateConfidence(gateResults)          // Weighted average

// --- Validation UI ---
function renderValidationBoard()                  // 12-card grid
function renderGateCard(gate, result)             // Single gate card
function renderConfidenceScore(score)             // Radial indicator
function renderGateEvidence(gateId)               // Expandable detail
function animateProgressBar(element, target)      // Smooth fill animation

// --- CSS additions ---
// .gate-card, .gate-card--pass, .gate-card--fail, .gate-card--partial
// .confidence-radial, .confidence-radial__fill
// .evidence-panel, .evidence-panel--expanded
```

#### Dependencies
- Sprint 2: VALID-01 agent, pipeline outputs, solution panel

#### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| VALID-01 output format inconsistent across domains | High | High | Define strict output schema in system prompt; add fallback regex patterns |
| Regex parsing misses edge cases | Medium | Medium | Unit test regex against 20+ sample outputs; add JSON fallback |
| Gate weights need tuning per domain | Low | Medium | Default equal weights; expose config object for per-domain overrides in Sprint 5 |

---

### Sprint 4: Agent Anatomy Viewer + Spawn

**Goal:** Build the agent introspection panel showing live cognitive state, implement episodic memory, goal stacks, action loop visualization, and manual agent spawning.

#### Deliverables

| # | Deliverable | Acceptance Criteria | Story Points |
|---|-------------|-------------------|--------------|
| 4.1 | Agent anatomy panel | Click any agent in roster to open detail panel; shows 5 sections: Working Memory, Episodic Memory, Goal Stack, Perception, Action Loop; panel slides in from left or overlays center | 5 |
| 4.2 | Working memory display | Shows `currentTask`, `findings[]`, `hypotheses[]`, `confidence`; updates in real-time during agent execution via `CustomEvent('memory-update')` | 3 |
| 4.3 | Episodic memory (FIFO, max 6) | Circular buffer of max 6 entries per agent; each entry has `{ timestamp, event, outcome, insight }`; oldest entry evicted on overflow; rendered as vertical timeline | 3 |
| 4.4 | Goal stack with priority ordering | Stack data structure (LIFO) with priority field; goals pushed by ORCH-01; popped on completion; rendered as draggable list (visual only, not user-reorderable) | 3 |
| 4.5 | Perception section | Shows agent's current input context summary, token count, relevant prior messages; updates on each agent turn | 2 |
| 4.6 | Action loop visualization | 4-stage ring: SENSE -> THINK -> PLAN -> ACT; active stage highlighted with pulse animation; transitions on `CustomEvent('action-loop-step')` | 5 |
| 4.7 | Live memory updates during simulation | All anatomy sections update as the pipeline runs; no full re-render — incremental DOM patches only; `<100ms` update latency | 3 |
| 4.8 | Manual specialist spawn button | "Spawn DeepDiver" button in anatomy panel; creates DEEP-01 agent with focused sub-prompt from selected agent's context; agent added to roster | 3 |
| 4.9 | Spawn message to comm bus | Spawn event posts `{ type: 'spawn', from: parentAgent, content: 'Spawned DEEP-01 for [task]' }` to comm bus; yellow highlight | 1 |
| 4.10 | Agent count update on spawn | Header stats bar "Active Agents" counter increments; roster adds new entry with `running` state; DEEP-01 runs and produces output appended to solutions | 2 |

**Total Story Points: 30**

#### Files / Functions to Create

```
// Inside <script> (additions to swarm-autopsy.html):

// --- Agent Anatomy ---
function renderAnatomyPanel(agentId)              // Full anatomy view
function toggleAnatomyPanel(agentId)              // Open/close
function renderWorkingMemorySection(agentId)      // WM display
function renderEpisodicMemory(agentId)            // Timeline view
function renderGoalStack(agentId)                 // Priority list
function renderPerception(agentId)                // Context summary
function renderActionLoop(agentId)                // 4-stage ring

// --- Episodic Memory ---
function pushEpisodicMemory(agentId, entry)       // FIFO push
function getEpisodicMemory(agentId)               // Read buffer
const EPISODIC_MAX = 6                            // Buffer size

// --- Goal Stack ---
function pushGoal(agentId, goal)                  // Push with priority
function popGoal(agentId)                         // Pop highest priority
function peekGoal(agentId)                        // Read top
function renderGoalItem(goal)                     // Single goal element

// --- Action Loop ---
const ACTION_STAGES = ['SENSE','THINK','PLAN','ACT']
function advanceActionLoop(agentId)               // Next stage
function renderActionRing(agentId, activeStage)   // SVG ring

// --- Spawn ---
function spawnDeepDiver(parentAgentId, context)   // Create DEEP-01
function buildDeepDiverPrompt(parentContext)       // Sub-prompt assembly
function registerSpawnedAgent(agent)               // Add to STATE.agents

// --- Events ---
// CustomEvent: 'memory-update'       { detail: { agentId, key, value } }
// CustomEvent: 'action-loop-step'    { detail: { agentId, stage } }
// CustomEvent: 'agent-spawned'       { detail: { parentId, childId } }
```

#### Dependencies
- Sprint 2: Agent roster, comm bus, working memory
- Sprint 3: Validation results (displayed in anatomy context)

#### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Anatomy panel DOM complexity causes jank | Medium | Medium | Use `requestAnimationFrame` for updates; batch mutations; consider virtual scrolling for episodic memory |
| DeepDiver spawn adds unpredictable API cost | Medium | High | Cap spawns at 2 per simulation; show token estimate before spawn |
| Action loop timing doesn't match actual agent processing | Low | Low | Use heuristic timing based on streaming tokens; not exact match |

---

## Phase 3 — Polish (Sprints 5-6)

---

### Sprint 5: All 9 Threat Domains + IaC Output

**Goal:** Configure all 9 domain-specific system prompts, implement IaC code output formatting, detection rule generation, and MITRE ATT&CK mapping.

#### Deliverables

| # | Deliverable | Acceptance Criteria | Story Points |
|---|-------------|-------------------|--------------|
| 5.1 | Domain 1: Quantum Harvest (NIST PQC) | System prompts for all 6 agents tuned to quantum computing threats; references NIST PQC standards (CRYSTALS-Kyber, CRYSTALS-Dilithium); SCOUT identifies Harvest Now Decrypt Later paths | 3 |
| 5.2 | Domain 2: AI Model Poisoning | Prompts cover training data poisoning, backdoor injection, model supply chain attacks; EXPLOIT generates adversarial perturbation chains | 3 |
| 5.3 | Domain 3: Deepfake Identity Attack | Prompts cover synthetic media for auth bypass, voice cloning for vishing, video injection for KYC fraud; DEFEND covers liveness detection countermeasures | 3 |
| 5.4 | Domain 4: Supply Chain Compromise | Prompts cover dependency confusion, typosquatting, CI/CD pipeline compromise, build system tampering; references SolarWinds and 3CX patterns | 3 |
| 5.5 | Domain 5: Agentic AI Weaponization | Prompts cover autonomous exploit agents, self-propagating AI worms, prompt injection at scale; DEFEND covers AI guardrails and containment | 3 |
| 5.6 | Domain 6: OT/ICS Convergence | Prompts cover IT/OT bridge attacks, PLC manipulation, safety-instrumented system bypass; references Purdue model and IEC 62443 | 3 |
| 5.7 | Domain 7: LLMjacking | Prompts cover stolen API key abuse, model proxy hijacking, resource theft for crypto mining via LLM inference; DEFEND covers key rotation and usage anomaly detection | 3 |
| 5.8 | Domain 8: Federated Identity (APT29) | Prompts cover Golden SAML, token forging, federated trust abuse; references APT29 TTPs and SolarWinds identity chain attacks | 3 |
| 5.9 | Domain 9: Cloud Misconfiguration (ScarletEel) | Prompts cover exposed credentials, overly permissive IAM, public S3/storage, lateral movement via cloud APIs; references ScarletEel campaign patterns | 3 |
| 5.10 | Domain prompt registry | `DOMAIN_PROMPTS` map keyed by domain ID; each entry contains 6 agent-specific system prompt overrides; selectable via dropdown | 2 |
| 5.11 | IaC output: Terraform HCL | DEFEND-01 and REPORT-01 output Terraform HCL blocks for remediation; rendered with syntax highlighting in solution panel; copy-to-clipboard button | 5 |
| 5.12 | IaC output: CloudFormation YAML | Same as 5.11 but for CloudFormation YAML format; user toggle between Terraform and CloudFormation | 3 |
| 5.13 | Detection rule output | DEFEND-01 outputs CloudTrail Insights queries and GuardDuty custom threat intel rules; rendered in dedicated "Detection Rules" tab in solution panel | 3 |
| 5.14 | MITRE ATT&CK mapping | EXPLOIT-01 tags each exploit chain with MITRE ATT&CK technique IDs (e.g., T1078, T1190); rendered as clickable badges linking to attack.mitre.org | 3 |

**Total Story Points: 43**

#### Files / Functions to Create

```
// Inside <script> (additions to swarm-autopsy.html):

// --- Domain Prompts ---
const DOMAIN_PROMPTS = new Map()                   // Domain -> agent prompts
function registerDomain(id, name, prompts)         // Domain registration
function getDomainPrompts(domainId, agentId)        // Lookup
function buildDomainContext(domainId)               // Full context object

// Domain-specific prompt builders:
function quantumHarvestPrompts()                   // Domain 1
function aiModelPoisoningPrompts()                 // Domain 2
function deepfakeIdentityPrompts()                 // Domain 3
function supplyChainCompromisePrompts()            // Domain 4
function agenticAIWeaponPrompts()                  // Domain 5
function otIcsConvergencePrompts()                 // Domain 6
function llmJackingPrompts()                       // Domain 7
function federatedIdentityPrompts()                // Domain 8
function cloudMisconfigPrompts()                   // Domain 9

// --- IaC Output ---
function formatTerraformHCL(mitigations)           // Generate Terraform
function formatCloudFormationYAML(mitigations)     // Generate CF
function renderIaCOutput(format, code)             // Syntax-highlighted block
function copyToClipboard(text)                     // Clipboard API wrapper
function toggleIaCFormat(format)                   // Switch Terraform/CF

// --- Detection Rules ---
function formatCloudTrailQuery(detection)          // CloudTrail query string
function formatGuardDutyRule(detection)            // GuardDuty JSON
function renderDetectionRules(rules)               // Detection tab

// --- MITRE ATT&CK ---
function parseMitreTechniques(exploitOutput)       // Extract Txxxx IDs
function renderMitreBadge(techniqueId)             // Clickable badge
function getMitreUrl(techniqueId)                  // URL builder

// --- Syntax Highlighting (minimal) ---
function highlightHCL(code)                        // Terraform keywords
function highlightYAML(code)                       // YAML structure
function highlightJSON(code)                       // JSON structure
```

#### Dependencies
- Sprint 2: Full agent pipeline, agent prompt injection points
- Sprint 3: Validation gates (domain-specific gate weight overrides)

#### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| 9 domains x 6 agents = 54 unique system prompts — quality variance | High | High | Define prompt template structure; reuse common sections; review each domain end-to-end |
| IaC output may contain invalid syntax | Medium | High | Instruct Claude to output valid HCL/YAML in system prompt; add basic syntax validation regex |
| MITRE technique IDs may be hallucinated | Medium | Medium | Validate against known technique ID format (T\d{4}(\.\d{3})?); flag unrecognised IDs |
| Token budget blow-up with domain-specific prompts | Medium | High | Enforce max system prompt length (2000 tokens); compress shared context |

---

### Sprint 6: Documentation + Performance + Polish

**Goal:** Optimize performance, add error handling, keyboard navigation, visual polish, documentation generation, API cost tracking, and final cross-domain testing.

#### Deliverables

| # | Deliverable | Acceptance Criteria | Story Points |
|---|-------------|-------------------|--------------|
| 6.1 | Performance: Pipeline under 60s | End-to-end pipeline completes in <60s for all 9 domains (measured p95); streaming used where possible; parallel API calls where agent dependencies allow | 5 |
| 6.2 | Performance: UI under 100ms | No single DOM update takes >100ms (measured via `Performance.mark/measure`); comm bus uses virtual scrolling for >100 messages; stats bar updates debounced to 16ms | 3 |
| 6.3 | Error handling: API failures | All `callClaude()` calls wrapped in try/catch; 429 -> exponential backoff (1s, 2s, 4s); 500 -> retry 3x then surface error in agent card; network error -> offline banner | 3 |
| 6.4 | Error handling: Agent failures | Failed agent shows red error state; error message in comm bus; pipeline continues with degraded output (skip agent); "Retry Agent" button on failed card | 3 |
| 6.5 | Error handling: Malformed output | JSON.parse wrapped in try/catch; fallback to regex extraction; if both fail, agent marked as `error` with "Output Parse Error" message; raw output preserved for debugging | 2 |
| 6.6 | Keyboard navigation (WCAG 2.1 Level A) | All interactive elements reachable via Tab; Enter/Space activates buttons; Escape closes panels; focus ring visible (2px cyan outline); skip-to-content link; aria-labels on all controls | 5 |
| 6.7 | Visual polish: Animations | Agent state transitions: 300ms ease-out fade; comm bus messages: slide-in from right 200ms; gate cards: flip animation on score reveal; confidence radial: animated fill over 1s | 3 |
| 6.8 | Visual polish: Transitions | Panel open/close: 250ms slide; solution expand: 200ms accordion; hover states: 150ms all properties; reduce-motion media query disables all animations | 2 |
| 6.9 | Documentation suite generation | REPORT-01 outputs: Executive Summary (1 page), Technical Deep-Dive (full detail), Remediation Playbook (step-by-step), Compliance Matrix (controls mapped); all exportable as formatted HTML sections | 5 |
| 6.10 | API token budget tracking | Display tokens used per agent, total tokens per simulation, estimated cost (based on Claude model pricing); shown in footer bar; warn at 80% of configurable budget limit | 3 |
| 6.11 | Token budget per-agent breakdown | Expandable section showing input tokens, output tokens, and cost for each agent call; accessible from stats bar | 2 |
| 6.12 | Final testing: All 9 domains | Each domain run end-to-end 3 times; all 12 gates produce results; no JS errors in console; IaC output renders correctly; MITRE badges link correctly | 5 |
| 6.13 | Loading states & empty states | Skeleton loaders for panels during API calls; empty state illustrations for pre-run state; "No data yet — run an autopsy to begin" messaging | 2 |
| 6.14 | API key input | Secure input field for Anthropic API key; stored in `sessionStorage` (not localStorage); masked display; "Test Connection" button validates key | 2 |

**Total Story Points: 45**

#### Files / Functions to Create

```
// Inside <script> (additions to swarm-autopsy.html):

// --- Performance ---
function measurePipelineTime()                     // Start/stop timer
function markUIUpdate(label)                       // Performance.mark
function debounce(fn, ms)                          // Utility
function throttle(fn, ms)                          // Utility
function virtualScroll(container, items, renderFn) // Virtual list

// --- Error Handling ---
function handleApiError(error, agentId)            // Categorise + display
function handleParseError(rawOutput, agentId)      // Fallback parsing
function retryAgent(agentId)                       // Manual retry
function showOfflineBanner()                       // Network error UI
function degradedPipelineContinue(failedAgentId)   // Skip + continue

// --- Accessibility ---
function initKeyboardNav()                         // Tab order + handlers
function trapFocus(panelElement)                   // Modal focus trap
function announceToScreenReader(message)           // aria-live region
function addSkipLink()                             // Skip-to-content

// --- Visual Polish ---
function animateAgentTransition(agentId, from, to) // State change anim
function animateMessageIn(messageElement)           // Slide-in
function animateGateReveal(gateElement, result)    // Flip card
function animateConfidence(target)                 // Radial fill
function respectReducedMotion()                    // Media query check

// --- Documentation ---
function generateExecutiveSummary(pipelineData)    // 1-page summary
function generateTechnicalReport(pipelineData)     // Full detail
function generateRemediationPlaybook(pipelineData) // Step-by-step
function generateComplianceMatrix(pipelineData)    // Controls matrix
function exportDocumentation(format)               // HTML export

// --- Token Tracking ---
function trackTokenUsage(agentId, inputTokens, outputTokens) // Per-call
function calculateCost(inputTokens, outputTokens, model)      // USD
function renderTokenBudget()                       // Footer bar
function checkBudgetWarning(totalTokens, limit)    // 80% threshold
function renderTokenBreakdown()                    // Per-agent detail

// --- API Key ---
function renderApiKeyInput()                       // Secure input
function storeApiKey(key)                          // sessionStorage
function testApiConnection(key)                    // Validation call
function getApiKey()                               // Retrieve masked

// --- Loading States ---
function renderSkeleton(container)                 // Skeleton loader
function renderEmptyState(container, message)      // Pre-run state
function clearSkeleton(container)                  // Remove loader
```

#### Dependencies
- Sprint 1-5: All prior work (this sprint touches every system)

#### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Performance target (<60s) not achievable for all domains | Medium | High | Profile each domain; identify slowest agents; reduce token counts; consider parallel agent execution where safe |
| WCAG compliance gaps discovered late | Medium | Medium | Run axe-core audit early in sprint; fix critical issues first |
| Token costs higher than expected across 9 domains | Medium | Medium | Default to `claude-sonnet` for non-critical agents; only use `claude-opus` for ORCH-01 and VALID-01 |
| Cross-browser animation jank | Low | Low | Test in Chrome, Firefox, Safari; use `will-change` sparingly; fallback to no-animation |

---

## Summary

| Sprint | Phase | Story Points | Cumulative |
|--------|-------|-------------|------------|
| 1 | MVP | 37 | 37 |
| 2 | MVP | 35 | 72 |
| 3 | Full Feature | 39 | 111 |
| 4 | Full Feature | 30 | 141 |
| 5 | Polish | 43 | 184 |
| 6 | Polish | 45 | 229 |

**Total: 229 story points across 6 sprints**

### Velocity Assumptions
- Team: 1-2 developers
- Sprint length: 2 weeks
- Estimated velocity: 35-45 points per sprint
- Buffer: ~10% per sprint for unplanned work

### Critical Path
```
Sprint 1 (Foundation)
    -> Sprint 2 (Pipeline)
        -> Sprint 3 (Validation) + Sprint 4 (Anatomy) [parallel]
            -> Sprint 5 (Domains)
                -> Sprint 6 (Polish)
```

Sprints 3 and 4 can run in parallel if two developers are available, as they touch different subsystems (validation engine vs. agent introspection).

### Definition of Done (All Sprints)
1. All deliverables meet acceptance criteria
2. No JavaScript errors in console across Chrome, Firefox, Safari
3. Single HTML file loads and runs independently (no build step)
4. Claude API integration functional with valid API key
5. All interactive elements accessible via keyboard
6. Performance budgets met (where applicable to sprint)
