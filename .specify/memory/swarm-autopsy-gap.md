# Swarm Autopsy vs Cloud Copilot — Gap Analysis

**Created**: 2026-03-25
**Author**: Gap Analysis Agent
**Scope**: Evaluate architectural differences, reusable assets, new build requirements, and strategic recommendations for adding Swarm Autopsy alongside the existing Cloud Copilot codebase.

---

## 1. Architecture Gap

### Fundamental Divergence

| Dimension | Cloud Copilot | Swarm Autopsy |
|---|---|---|
| **Architecture** | Multi-tier SPA + API + DB | Single-file client-side app |
| **Frontend** | Next.js 15 / React 19 / Tailwind CSS | Vanilla HTML5 / CSS3 / JS |
| **Backend** | FastAPI + SQLAlchemy + SQLite | None (Claude API called from browser) |
| **Database** | SQLite via SQLAlchemy ORM (19 models) | None (ephemeral in-memory state) |
| **Deployment** | Docker / monorepo (`apps/api` + `apps/web`) | Single HTML file |
| **Auth** | JWT-based workspace/user auth | API key input (Claude key) |
| **State management** | Server-side DB + SWR client cache | In-memory JS objects |
| **Build toolchain** | TypeScript, Next.js bundler, Python venv | None (no build step) |
| **AI integration** | Bedrock/Claude via backend proxy | Direct Claude API from browser (6-agent swarm) |
| **Lines of code** | ~65K across 445 files | Target: ~3-5K in 1 file |

**Verdict**: These are fundamentally different products with zero shared runtime infrastructure. Cloud Copilot is a multi-tenant SaaS platform; Swarm Autopsy is a self-contained browser tool. There is no incremental migration path between them.

---

## 2. Reusable Components

### 2.1 Potentially Reusable (Concept/Logic Level)

These cannot be reused as-is (wrong language, wrong runtime, DB dependencies), but their **logic and data structures** can inform Swarm Autopsy's design.

| Cloud Copilot Asset | File | Reuse Potential | Adaptation Required |
|---|---|---|---|
| **MITRE ATT&CK mapping** | `detection_service.py` (lines 64-73) | **High** — The `_MITRE` dict maps rule IDs to tactics/techniques (8 mappings). Swarm Autopsy needs MITRE mapping for 9 threat domains. | Extract mapping logic. Re-implement as JS object. Expand from 8 rules to cover all 9 SA threat domains. |
| **Severity scoring model** | `detection_service.py` (lines 76-81, 97-99) | **Medium** — `_SEV_WEIGHT` dict and `_risk_score()` function provide a severity-to-numeric-weight model. | Port to JS. Swarm Autopsy may need different weight curves for IaC-focused analysis. |
| **Alert data structure** | `detection_service.py` (lines 123-153) | **Medium** — The `_alert()` function defines a standardized schema: id, rule_id, title, description, severity, confidence, tactic, technique, risk_score, affected_resources, evidence. | Use as reference schema for agent output format. Adapt for IaC context. |
| **Attack path graph traversal** | `attack_path_service.py` (BFS blast radius, lines 134-182) | **Low-Medium** — BFS traversal logic for computing blast radius from a node. Conceptually relevant to Swarm Autopsy's attack path agent. | Would need complete rewrite in vanilla JS. No DB dependency possible. Input would be agent-generated graph, not DB query results. |
| **Prompt template model** | `prompt_registry.py` | **Medium** — Versioned prompt template concept (name, version, template, model_id, category). Useful pattern for Swarm Autopsy's 6-agent prompt management. | No ORM needed. Implement as JS config object with agent-specific prompts. |
| **Root cause clustering** | `drift_service.py` (lines 99-135) | **Low** — Pattern-based grouping of findings by resource_type + title keywords. | Different domain. Swarm Autopsy clusters by IaC misconfiguration pattern, not by cloud finding titles. |
| **CVE/KEV detection** | `detection_service.py` (lines 36-61) | **Low** — CISA KEV CVE set and regex matching. | Swarm Autopsy focuses on IaC misconfigurations, not CVE scanning. May be useful if vulnerability agent is added later. |

### 2.2 Not Reusable

| Cloud Copilot Asset | Reason |
|---|---|
| All 61+ React/TSX components | Swarm Autopsy is vanilla JS; no React runtime |
| All 38+ SWR hooks | SWR is a React data-fetching library |
| All SQLAlchemy models (19) | No database in Swarm Autopsy |
| All FastAPI routers (27+) | No backend server |
| All async services (33+) | Python asyncio + SQLAlchemy; wrong language and runtime |
| Tailwind CSS config | Single HTML file uses inline/embedded styles |
| Auth system (JWT, workspaces) | Swarm Autopsy has no user auth beyond API key |
| SLA/compliance engine | Domain-specific to CSPM, not IaC analysis |
| AWS Scanner integration | Swarm Autopsy analyzes user-provided IaC, not live AWS |

### 2.3 Reuse Summary

| Category | Count | Reuse Type |
|---|---|---|
| Direct code reuse | **0** | None (incompatible runtimes) |
| Logic/pattern port | **5-6** | Manual rewrite in vanilla JS |
| Data structure reference | **3-4** | Schema inspiration only |
| Zero relevance | **~430 files** | Complete mismatch |

**Effective reuse rate: < 2% by file count, ~5-10% by conceptual value.**

---

## 3. New Components Required (Build from Scratch)

### 3.1 Core Swarm Engine

| Component | Description | Complexity | Estimated LOC |
|---|---|---|---|
| **Agent Orchestrator** | Manages 6-agent lifecycle: spawn, execute, collect, terminate | High | 400-600 |
| **Communication Bus** | Inter-agent message passing (pub/sub or direct) | High | 200-300 |
| **Specialist Spawner** | Dynamically creates sub-agents for domain-specific tasks | Medium | 150-250 |
| **Agent Anatomy Engine** | Defines agent structure: role, capabilities, memory, tools | Medium | 200-300 |
| **Validation Gate Controller** | Orchestrates 12 validation gates between agent phases | High | 300-400 |
| **Claude API Client** | Browser-based Claude API integration with streaming | Medium | 150-200 |
| **Rate Limiter / Token Tracker** | Manages API rate limits and token budget across 6 agents | Medium | 100-150 |

### 3.2 Agent Implementations (6 Agents)

| Agent | Domain Responsibility | Complexity |
|---|---|---|
| **Recon Agent** | IaC parsing, resource inventory, dependency mapping | High |
| **Threat Modeler** | 9 threat domain analysis, MITRE ATT&CK mapping | High |
| **Validator Agent** | 12 validation gate execution, finding verification | High |
| **Remediation Agent** | Fix generation, IaC output (Terraform/CloudFormation) | High |
| **Reporter Agent** | Summary generation, risk scoring, executive output | Medium |
| **Coordinator Agent** | Swarm orchestration, conflict resolution, consensus | High |

### 3.3 Threat Domain Analyzers (9 Domains)

Each domain needs its own analysis prompt chain and validation criteria. These are all new:

1. Identity & Access Management
2. Network Security
3. Data Protection / Encryption
4. Logging & Monitoring
5. Compute Security
6. Container / Serverless Security
7. Storage Security
8. Secrets Management
9. Compliance & Governance

### 3.4 UI Components (Vanilla JS)

| Component | Description |
|---|---|
| **API Key Input** | Secure Claude API key entry with validation |
| **IaC Upload / Paste** | File upload or text paste for Terraform/CFN/Pulumi |
| **Swarm Visualization** | Real-time display of agent activity, message flow |
| **Agent Status Panel** | Per-agent status, progress, token usage |
| **Finding Cards** | Threat findings with severity, MITRE mapping, evidence |
| **Attack Path Diagram** | Visual attack chain rendering (SVG/Canvas) |
| **IaC Output Viewer** | Syntax-highlighted remediation code display |
| **Validation Gate Status** | Progress through 12 gates with pass/fail indicators |
| **Export Controls** | Download results as JSON/PDF/Markdown |

### 3.5 Output Generators

| Generator | Description |
|---|---|
| **IaC Remediation Output** | Generate corrected Terraform/CloudFormation/Pulumi |
| **MITRE ATT&CK Report** | Map findings to MITRE techniques with evidence |
| **Executive Summary** | Non-technical risk summary with scores |
| **JSON Export** | Machine-readable full analysis output |

---

## 4. Dependency Analysis

### Direct Dependencies: None

Swarm Autopsy has **zero runtime dependencies** on Cloud Copilot. It operates as a completely standalone product.

| Dependency Type | From Swarm Autopsy → Cloud Copilot | Status |
|---|---|---|
| API calls | None | No backend to call |
| Shared database | None | No database |
| Shared auth | None | Different auth model |
| Shared npm packages | None | No npm in Swarm Autopsy |
| Shared Python packages | None | No Python in Swarm Autopsy |
| Shared UI framework | None | Vanilla JS vs React |
| Shared deployment | None | Different deployment models |

### Indirect Dependencies

| Type | Detail |
|---|---|
| **Domain knowledge** | Both products operate in the cloud security space. Developers need cloud security expertise for both. |
| **Claude API** | Both use Anthropic's Claude (Cloud Copilot via Bedrock proxy; Swarm Autopsy via direct API). Shared understanding of prompt engineering patterns. |
| **MITRE ATT&CK** | Both reference the MITRE framework. A shared MITRE mapping data file could be maintained. |

---

## 5. Future Integration Points

While the products are independent today, these integration opportunities exist:

| Integration Point | Description | Effort | Value |
|---|---|---|---|
| **IaC findings → Cloud Copilot ingestion** | Swarm Autopsy output (JSON) could be imported as CanonicalFindings into Cloud Copilot | Medium | High — unifies pre-deploy and runtime findings |
| **Cloud Copilot findings → Swarm Autopsy context** | Export Cloud Copilot runtime findings as context for Swarm Autopsy IaC analysis | Medium | Medium — helps prioritize IaC fixes based on real incidents |
| **Shared MITRE mapping library** | Extract MITRE ATT&CK mappings into a shared JSON file used by both products | Low | Medium — consistency across products |
| **Prompt registry as service** | Cloud Copilot's prompt_registry could serve prompts to Swarm Autopsy agents | High | Low — over-engineering for a single-file app |
| **Attack path comparison** | Compare Swarm Autopsy's predicted attack paths with Cloud Copilot's observed paths | High | High — validates IaC analysis against runtime reality |
| **Unified dashboard** | Cloud Copilot dashboard page embedding Swarm Autopsy results | Medium | Medium — single pane of glass for security teams |
| **Shared severity model** | Standardize severity weights and risk scoring across both products | Low | Medium — consistent risk communication |

### Recommended First Integration

**IaC findings ingestion** — Build a simple JSON export from Swarm Autopsy that matches Cloud Copilot's `CanonicalFinding` schema. This lets teams run IaC analysis pre-deploy, then track those findings alongside runtime detections in Cloud Copilot.

---

## 6. Risk Assessment

### 6.1 Scope Change Risks

| Risk | Severity | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **Team context switching** | High | High | Developers switching between React/Python and vanilla JS reduces velocity on both products | Assign dedicated owner(s) to Swarm Autopsy; minimize overlap |
| **Cloud Copilot velocity loss** | High | High | Sprints 24-28 backlog (portfolio, design system, prompts, attack paths, drift) stalls if attention shifts | Complete Sprint 24-28 milestones before starting Swarm Autopsy, or staff separately |
| **Scope creep in Swarm Autopsy** | Medium | High | 6-agent swarm + 9 domains + 12 gates is a large surface area for a "single HTML file" | Start with 2-3 agents and 3-4 domains; expand iteratively |
| **Claude API cost overrun** | Medium | Medium | 6 concurrent agents consuming tokens per analysis could be expensive; no backend to cache | Implement strict token budgets per agent; cache repeated analyses in localStorage |
| **Browser performance** | Medium | Medium | Running 6 parallel Claude API calls + rendering results in a single HTML file may hit browser limits | Use Web Workers for agent execution; sequential agent execution as fallback |
| **Single-file maintainability** | High | High | 3-5K lines of JS/HTML/CSS in one file becomes unmaintainable beyond MVP | Accept this for MVP; plan migration to a minimal build step (esbuild) for v2 |
| **Security of client-side API keys** | High | Medium | Claude API key exposed in browser memory; no server-side proxy | Document the risk clearly; recommend users use ephemeral/scoped keys |
| **Competing product identity** | Medium | Low | Two products in same repo confuses contributors and investors about company focus | Clear README separation; separate branding; distinct product directories |

### 6.2 Timeline Impact Matrix

| Scenario | Cloud Copilot Impact | Swarm Autopsy Timeline |
|---|---|---|
| **Same team, sequential** | Sprints 24-28 delayed 4-6 weeks | Ships after Sprint 28 completion |
| **Same team, interleaved** | Each sprint takes 1.5-2x longer | Ships incrementally but both products slow |
| **Dedicated Swarm Autopsy dev** | No impact to Cloud Copilot | 3-4 week MVP (2-3 agents), 8-10 weeks full (6 agents) |
| **Outsourced Swarm Autopsy** | No impact | Depends on contractor ramp-up; risk of quality mismatch |

---

## 7. Recommendation

### Build as Separate Directory in Same Repo (Monorepo)

**Recommended structure**:

```
cloud-copilot/
  apps/
    api/          # Existing FastAPI backend
    web/          # Existing Next.js frontend
    swarm-autopsy/  # NEW — standalone single-file product
      index.html          # The product (single file)
      README.md           # Standalone documentation
      shared/
        mitre-mapping.json  # Shared MITRE data (also consumed by api/)
      tests/
        test-swarm.html     # Browser-based tests
```

### Rationale

| Factor | Same Repo (Monorepo) | Separate Repo |
|---|---|---|
| **Shared MITRE data** | Easy — single source of truth | Requires duplication or git submodule |
| **Future integration** | Easy — shared CI/CD, coordinated releases | Harder — cross-repo coordination |
| **Team overhead** | Lower — one repo to clone, one PR process | Higher — context switching between repos |
| **Independence** | Maintained via separate `apps/` directory | Maximum isolation |
| **Deployment** | Independent deploy pipelines per `apps/` dir | Naturally independent |
| **Git history noise** | Minor — separate directory, clear commits | None |

### Execution Plan

1. **Phase 1 (Week 1-2)**: Build Swarm Autopsy MVP with 2 agents (Recon + Threat Modeler) and 3 threat domains in `apps/swarm-autopsy/index.html`
2. **Phase 2 (Week 3-4)**: Add remaining 4 agents, expand to 9 threat domains, implement 12 validation gates
3. **Phase 3 (Week 5-6)**: IaC output generation, MITRE ATT&CK report, export functionality
4. **Phase 4 (Week 7-8)**: Integration bridge — JSON export matching `CanonicalFinding` schema for Cloud Copilot ingestion
5. **Ongoing**: Extract shared `mitre-mapping.json` consumed by both `detection_service.py` and `swarm-autopsy/index.html`

### Critical Decision

**Do not interleave Swarm Autopsy work with Sprints 24-28.** Cloud Copilot's Sprint 24-28 backlog (portfolio dashboard, design system, prompt registry, attack paths, drift detection) represents committed product roadmap. Swarm Autopsy should either:

- Be staffed with a dedicated developer, or
- Be scheduled after Sprint 28 completion

Attempting to build both simultaneously with the same team will deliver neither product well.
