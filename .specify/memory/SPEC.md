# Cloud Posture Copilot — Sprint 24-28 Specification

**Created**: 2026-03-25
**Status**: Draft
**Scope**: Sprints 24-28 (Phase 2 features)
**Baseline**: Sprints 0-23 complete (~72% of full product scope)

---

## Table of Contents

1. [Sprint 24: MSP / vCISO Portfolio Dashboard](#sprint-24--msp--vciso-portfolio-dashboard)
2. [Sprint 25: Design System Component Library](#sprint-25--design-system-component-library)
3. [Sprint 26: AI Prompt Registry & Provider Strategy](#sprint-26--ai-prompt-registry--provider-strategy)
4. [Sprint 27: Attack Path Visualization (Domain F)](#sprint-27--attack-path-visualization-domain-f)
5. [Sprint 28: Drift Detection & Root Cause v2](#sprint-28--drift-detection--root-cause-v2)

---

## Sprint 24 — MSP / vCISO Portfolio Dashboard

**Goal**: Build the multi-tenant portfolio dashboard that lets MSPs and vCISOs monitor all client workspaces from a single view, unlocking the SKU 2 commercial revenue path identified as the best GTM entry point.

### User Stories

#### US-24.1 — Portfolio Risk Overview (Priority: P1)

As an MSP operator, I want a cross-workspace portfolio dashboard showing risk scores, severity distributions, and SLA status for all my client workspaces, so that I can triage which clients need attention without switching contexts.

**Why this priority**: This is the core value proposition of the MSP tier. Without a portfolio view, MSPs must log into each workspace individually.

**Independent Test**: Navigate to `/dashboard/portfolio`, see a table/grid of all client workspaces with risk score, critical/high finding counts, and SLA breach indicators.

**Acceptance Scenarios**:

1. **Given** an MSP user with 5 client workspaces, **When** they navigate to the portfolio dashboard, **Then** they see all 5 workspaces listed with current risk scores and severity breakdowns.
2. **Given** a workspace with SLA breaches, **When** viewing the portfolio, **Then** a red SLA breach badge is visible for that workspace row.
3. **Given** a portfolio with 50+ workspaces, **When** viewing the dashboard, **Then** the page loads in under 3 seconds and supports pagination or virtual scrolling.

---

#### US-24.2 — Client Workspace Switcher (Priority: P1)

As an MSP operator, I want a fast workspace switcher in the app header, so that I can jump between client contexts without navigating back to a portal.

**Why this priority**: Context switching speed is critical for MSP daily operations; this is a usability gate for the entire MSP experience.

**Independent Test**: Click the workspace switcher dropdown in the header, type a client name, select it, and confirm the entire app context reloads to that workspace's data.

**Acceptance Scenarios**:

1. **Given** the app header workspace selector, **When** the user clicks it, **Then** a searchable dropdown appears listing all accessible workspaces.
2. **Given** 20+ workspaces, **When** the user types a partial name, **Then** the list filters in real time (debounced, under 200ms perceived delay).
3. **Given** the user selects a different workspace, **When** the switch completes, **Then** all dashboard data, findings, and navigation reflect the new workspace context.

---

#### US-24.3 — Client Scorecard Export (Priority: P2)

As a vCISO, I want to generate a client-facing scorecard (PDF) for any workspace, so that I can share a branded security posture summary with non-technical stakeholders.

**Why this priority**: Client reporting is the primary revenue justification for MSP/vCISO engagements.

**Independent Test**: From the portfolio dashboard, click "Generate Scorecard" for a workspace, receive a PDF with risk score, top findings, compliance status, and trend chart.

**Acceptance Scenarios**:

1. **Given** a workspace with findings and compliance data, **When** the user clicks "Generate Scorecard", **Then** a PDF is generated within 10 seconds containing risk score, severity breakdown, compliance summary, and 30-day trend.
2. **Given** the generated PDF, **When** opened, **Then** it includes workspace name, generation date, and a professional layout suitable for executive audiences.
3. **Given** a workspace with no findings, **When** a scorecard is generated, **Then** the PDF shows a clean posture summary rather than empty sections.

---

#### US-24.4 — Portfolio SLA Breach View (Priority: P2)

As an MSP operator, I want a dedicated view of all SLA breaches across my portfolio, so that I can prioritize remediation for clients approaching or exceeding their SLA deadlines.

**Why this priority**: SLA adherence is contractually binding for MSPs; a breach view prevents revenue-impacting SLA violations.

**Independent Test**: Navigate to portfolio SLA view, see a sorted list of findings approaching or past SLA across all workspaces.

**Acceptance Scenarios**:

1. **Given** findings with SLA deadlines across 3 workspaces, **When** the user opens the SLA breach view, **Then** they see a unified list sorted by time-to-breach (most urgent first).
2. **Given** the SLA breach list, **When** the user clicks a finding row, **Then** they are navigated to the finding detail page within the correct workspace context.

---

#### US-24.5 — White-Label Foundation (Priority: P3)

As an MSP admin, I want to configure workspace branding (logo, accent color, company name), so that client-facing reports and the client portal carry my brand identity.

**Why this priority**: White-label is a revenue blocker for MSP resale but can ship as foundation settings first, with full theming in a later sprint.

**Independent Test**: Navigate to workspace settings, upload a logo, set an accent color, confirm the logo appears in the scorecard PDF header.

**Acceptance Scenarios**:

1. **Given** the workspace settings page, **When** the admin uploads a logo and sets an accent color, **Then** the settings persist and are retrievable via API.
2. **Given** branding settings configured, **When** a scorecard PDF is generated, **Then** the PDF header displays the custom logo and accent color.

---

### Edge Cases

- What happens when an MSP user has access to 0 workspaces? Show an empty state with onboarding CTA.
- What happens when a workspace has never been scanned? Show "No scan data" instead of zeroed-out risk scores.
- How does the switcher behave if the user's access to a workspace is revoked mid-session? Return 403 on next API call and redirect to portfolio.

### Functional Requirements

- **FR-24.01**: System MUST aggregate risk scores, severity distributions, and SLA status across all workspaces accessible to the authenticated user.
- **FR-24.02**: System MUST support workspace context switching without full page reload (client-side state swap + API refetch).
- **FR-24.03**: System MUST generate PDF scorecards with risk score, severity breakdown, compliance summary, and trend chart.
- **FR-24.04**: System MUST store workspace branding settings (logo URL, accent color, display name).
- **FR-24.05**: System MUST enforce RBAC so that MSP users only see workspaces they have been granted access to.

### Key Entities

- **PortfolioSummary** (virtual/aggregated): workspace_id, workspace_name, risk_score, critical_count, high_count, medium_count, low_count, sla_breaches, last_scan_at
- **WorkspaceBranding**: workspace_id, logo_url, accent_color, display_name, created_at, updated_at

### Backend Deliverables

| Artifact | Path | Description |
|---|---|---|
| Portfolio service | `app/services/portfolio_service.py` | Aggregates risk/SLA data across workspaces |
| Portfolio router | `app/routers/portfolio.py` | API endpoints for portfolio dashboard |
| Scorecard service | `app/services/scorecard_service.py` | Generates PDF scorecards per workspace |
| Workspace branding model | `app/models/workspace_branding.py` | SQLAlchemy model for branding settings |
| Workspace branding router | `app/routers/workspace_branding.py` | CRUD endpoints for branding settings |
| Register in main.py | `app/main.py` | Import and include portfolio + branding routers |

### Frontend Deliverables

| Artifact | Path | Description |
|---|---|---|
| Portfolio dashboard page | `app/dashboard/portfolio/page.tsx` | Cross-workspace risk heatmap and table |
| Workspace switcher component | `components/shell/workspace-switcher.tsx` | Searchable dropdown in app header |
| Scorecard generator dialog | `components/portfolio/scorecard-dialog.tsx` | Trigger PDF generation and download |
| SLA breach view | `components/portfolio/sla-breach-view.tsx` | Unified SLA breach list across workspaces |
| Branding settings section | `components/settings/branding-settings.tsx` | Logo upload + accent color picker |
| usePortfolio hook | `hooks/use-portfolio.ts` | Fetch portfolio summary data |
| useWorkspaceSwitcher hook | `hooks/use-workspace-switcher.ts` | Workspace list + switch logic |

### API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/portfolio/summary` | Returns aggregated risk/SLA summary for all accessible workspaces |
| GET | `/api/v1/portfolio/sla-breaches` | Returns all SLA breaches across portfolio, sorted by urgency |
| POST | `/api/v1/portfolio/scorecard/{workspace_id}` | Generates and returns a PDF scorecard for a workspace |
| GET | `/api/v1/workspaces/switchable` | Returns list of workspaces the user can switch to (id, name, logo) |
| GET | `/api/v1/workspaces/{id}/branding` | Returns branding settings for a workspace |
| PUT | `/api/v1/workspaces/{id}/branding` | Updates branding settings (logo_url, accent_color, display_name) |

### Dependencies

- Requires Sprints 0-7 (tenant/workspace foundation, RBAC, risk scoring, SLA tracking, report generation).
- No dependency on Sprints 25-28.

### Success Criteria

- **SC-24.01**: MSP user can view portfolio of 10+ workspaces with risk scores in under 3 seconds.
- **SC-24.02**: Workspace switch completes in under 1 second (perceived).
- **SC-24.03**: Scorecard PDF generates in under 10 seconds for a workspace with 500+ findings.
- **SC-24.04**: All portfolio endpoints enforce RBAC (no cross-tenant data leakage).

---

## Sprint 25 — Design System Component Library

**Goal**: Extract and build the "Gold Standard" reusable component library mandated by the product spec, ensuring consistent UX patterns across all pages and enabling rapid feature development in subsequent sprints.

### User Stories

#### US-25.1 — RootCauseChip and TimestampLabel Components (Priority: P1)

As a frontend developer, I want standalone RootCauseChip and TimestampLabel components in the shared component library, so that every finding-related page displays root cause tags and timestamps consistently.

**Why this priority**: These components appear on every finding row and detail page; inconsistency here undermines product quality perception.

**Independent Test**: Import RootCauseChip, render it with a root cause string, confirm it displays a styled chip. Import TimestampLabel, render with an ISO timestamp, confirm it shows relative time with a tooltip for absolute time.

**Acceptance Scenarios**:

1. **Given** a RootCauseChip with cause="misconfiguration", **When** rendered, **Then** it displays a colored chip with the label "Misconfiguration" and a color mapped to the cause category.
2. **Given** a TimestampLabel with a timestamp 2 hours ago, **When** rendered, **Then** it displays "2 hours ago" with a tooltip showing the full ISO timestamp.
3. **Given** a TimestampLabel with a null timestamp, **When** rendered, **Then** it displays "N/A" without errors.

---

#### US-25.2 — AIFeedbackBar Component (Priority: P1)

As an operator viewing an AI insight, I want a feedback bar with helpful/unhelpful/edit actions, so that I can provide signal that improves AI output quality over time.

**Why this priority**: AI feedback is a core product loop; a reusable component ensures every AI surface captures feedback consistently.

**Independent Test**: Render AIFeedbackBar with an insight ID, click "Helpful", confirm the API call fires and the button state updates.

**Acceptance Scenarios**:

1. **Given** an AIFeedbackBar for insight_id=123, **When** the user clicks "Helpful", **Then** a POST to `/api/v1/ai/feedback` is sent with `{insight_id: 123, rating: "accepted"}` and the thumbs-up icon fills.
2. **Given** the user clicks "Unhelpful", **When** the feedback is submitted, **Then** a follow-up text area appears for optional written feedback.
3. **Given** an insight with existing feedback, **When** the bar loads, **Then** the previously selected state is pre-filled.

---

#### US-25.3 — CreateDrawer Component (Priority: P2)

As an operator, I want a slide-over drawer for creating new findings, assignments, exceptions, and other entities, so that creation flows do not navigate me away from the current page context.

**Why this priority**: Consistent creation UX reduces cognitive load and keeps operators in context.

**Independent Test**: Trigger CreateDrawer with a form schema, confirm it slides in from the right, submit the form, confirm it closes and the parent list refreshes.

**Acceptance Scenarios**:

1. **Given** a CreateDrawer with title="New Exception" and form fields, **When** opened, **Then** a drawer slides in from the right covering 40% of the viewport width.
2. **Given** the drawer form is submitted with valid data, **When** the API returns success, **Then** the drawer closes and an `onSuccess` callback fires.
3. **Given** the user clicks outside the drawer or presses Escape, **When** there are unsaved changes, **Then** a confirmation dialog asks before closing.

---

#### US-25.4 — FrameworkScoreCard and ControlFamilyHeatmap (Priority: P2)

As a compliance officer, I want a FrameworkScoreCard showing pass/fail/exception counts per framework and a ControlFamilyHeatmap showing control family health, so that compliance status is immediately scannable.

**Why this priority**: Compliance is a primary buyer persona concern; these components elevate the compliance page from data table to executive-grade visualization.

**Independent Test**: Render FrameworkScoreCard with FSBP data (80 passed, 12 failed, 3 exceptions), confirm it shows a donut chart with percentages. Render ControlFamilyHeatmap with control families, confirm cells are color-coded by health.

**Acceptance Scenarios**:

1. **Given** a FrameworkScoreCard with framework="FSBP" and {passed: 80, failed: 12, exceptions: 3}, **When** rendered, **Then** it shows a donut chart, percentage score, and counts for each status.
2. **Given** a ControlFamilyHeatmap with 10 control families, **When** rendered, **Then** each cell is colored green (>90% pass), yellow (70-90%), or red (<70%).
3. **Given** a control family cell is clicked, **When** the click fires, **Then** an `onSelect(familyId)` callback is invoked for drill-down.

---

#### US-25.5 — Empty/Loading/Error State Consistency Pass (Priority: P3)

As a user navigating the application, I want every page to show polished loading skeletons, meaningful empty states with CTAs, and user-friendly error messages, so that the app feels production-grade.

**Why this priority**: State consistency is a quality gate for enterprise sales demos.

**Independent Test**: For each dashboard page, verify: (a) loading shows a skeleton, (b) empty data shows an illustration + CTA, (c) API error shows a retry-able error banner.

**Acceptance Scenarios**:

1. **Given** any dashboard page while data is loading, **When** the API has not responded, **Then** a skeleton loader matching the page layout is shown (not a spinner).
2. **Given** a findings page with 0 findings, **When** rendered, **Then** an empty state illustration is shown with the message "No findings yet" and a CTA to trigger a scan.
3. **Given** an API error on any page, **When** the error is caught, **Then** a banner displays "Something went wrong. [Retry]" with a retry button that re-fetches.

---

### Edge Cases

- What if a component receives unexpected props (e.g., unknown root cause category)? Fall back to a neutral gray chip with the raw string.
- What if the AI feedback endpoint is down? Show the feedback bar but disable buttons with a tooltip "Feedback temporarily unavailable."

### Functional Requirements

- **FR-25.01**: All design system components MUST be exported from a shared `components/ui/` directory.
- **FR-25.02**: Each component MUST accept a `className` prop for style overrides.
- **FR-25.03**: RootCauseChip MUST map cause categories to deterministic colors (not random).
- **FR-25.04**: TimestampLabel MUST use relative time (via `date-fns` or equivalent) with absolute tooltip.
- **FR-25.05**: CreateDrawer MUST support generic form schemas (not hardcoded to a single entity).
- **FR-25.06**: All existing pages MUST be migrated to use the new shared components by the end of the sprint.

### Key Entities

- No new backend entities. This sprint is frontend-only.

### Backend Deliverables

| Artifact | Path | Description |
|---|---|---|
| (none) | -- | This sprint has no backend deliverables |

### Frontend Deliverables

| Artifact | Path | Description |
|---|---|---|
| RootCauseChip | `components/ui/root-cause-chip.tsx` | Colored chip displaying root cause category |
| TimestampLabel | `components/ui/timestamp-label.tsx` | Relative time display with absolute tooltip |
| AIFeedbackBar | `components/ui/ai-feedback-bar.tsx` | Helpful/unhelpful/edit feedback actions for AI insights |
| CreateDrawer | `components/ui/create-drawer.tsx` | Slide-over drawer for entity creation forms |
| FrameworkScoreCard | `components/compliance/framework-score-card.tsx` | Donut chart + counts for a compliance framework |
| ControlFamilyHeatmap | `components/compliance/control-family-heatmap.tsx` | Color-coded grid of control family health |
| EmptyState | `components/ui/empty-state.tsx` | Reusable empty state with illustration + CTA |
| ErrorBanner | `components/ui/error-banner.tsx` | Retryable error banner for API failures |
| SkeletonPage | `components/ui/skeleton-page.tsx` | Generic skeleton loader matching common page layouts |
| Page migration | All `app/dashboard/*/page.tsx` files | Migrate existing pages to use shared components |

### API Endpoints

| Method | Path | Description |
|---|---|---|
| (none) | -- | No new endpoints; AIFeedbackBar uses existing `POST /api/v1/ai/feedback` |

### Dependencies

- Requires Sprint 6 (AI feedback endpoint) for AIFeedbackBar.
- Requires Sprint 7 (existing dashboard pages) for the migration pass.
- No dependency on Sprint 24 (can run in parallel if needed).

### Success Criteria

- **SC-25.01**: All 6 new components render without console errors in Storybook or equivalent isolation.
- **SC-25.02**: Every dashboard page uses shared EmptyState, ErrorBanner, and SkeletonPage components.
- **SC-25.03**: RootCauseChip color mapping is deterministic (same cause = same color every render).
- **SC-25.04**: CreateDrawer supports at least 3 different entity creation flows (finding, assignment, exception).

---

## Sprint 26 — AI Prompt Registry & Provider Strategy

**Goal**: Formalize the AI layer by building a prompt registry table with versioning, integrating Amazon Bedrock as the primary provider alongside Ollama, and enforcing output contract validation and safety handling as non-negotiable engineering standards.

### User Stories

#### US-26.1 — Prompt Registry Management (Priority: P1)

As a platform engineer, I want a formal prompt_registry table storing all production prompt templates with versioning, so that prompt changes are tracked, auditable, and rollback-safe.

**Why this priority**: The product spec marks this as a non-negotiable engineering standard. Without a registry, prompt changes are invisible code changes with no audit trail.

**Independent Test**: Create a prompt via API, update it (new version), confirm both versions exist, activate the older version, confirm AI service uses the active version.

**Acceptance Scenarios**:

1. **Given** a prompt_registry table, **When** a new prompt template is inserted, **Then** it receives version=1 and active=true.
2. **Given** an existing prompt with version=3 active, **When** version=2 is set to active, **Then** version=3 is deactivated and the AI service uses version=2.
3. **Given** the prompt registry API, **When** listing all prompts, **Then** each entry shows name, version, model, template, active status, created_at, and usage_count.

---

#### US-26.2 — Amazon Bedrock Provider Integration (Priority: P1)

As a platform operator, I want the AI service to route inference requests to Amazon Bedrock (Claude models) as the primary provider, with Ollama as a local fallback, so that production workloads use enterprise-grade models.

**Why this priority**: The product spec designates Bedrock as the primary provider. The existing Ollama integration is dev-only.

**Independent Test**: Configure Bedrock credentials, trigger an AI insight generation, confirm the request goes to Bedrock. Disable Bedrock, confirm fallback to Ollama.

**Acceptance Scenarios**:

1. **Given** Bedrock credentials are configured, **When** an AI insight is generated, **Then** the request is routed to the Bedrock Claude model specified in the prompt registry entry.
2. **Given** Bedrock is unreachable, **When** an AI insight is requested, **Then** the system falls back to Ollama (if configured) and logs a warning.
3. **Given** a prompt registry entry with model="anthropic.claude-3-sonnet", **When** executed via Bedrock, **Then** the correct model ID is used in the Bedrock InvokeModel call.

---

#### US-26.3 — Output Contract Schema Validation (Priority: P2)

As a platform engineer, I want all AI responses to be validated against a JSON schema defined in the prompt registry, so that downstream consumers never receive malformed AI output.

**Why this priority**: Output contracts are a non-negotiable engineering standard in the spec. Without schema validation, AI output can silently break UIs.

**Independent Test**: Define a prompt with an output schema, generate an insight, confirm the response matches the schema. Inject a malformed mock response, confirm validation fails and a fallback is returned.

**Acceptance Scenarios**:

1. **Given** a prompt with output_schema defining `{summary: string, severity: string, recommendations: string[]}`, **When** the AI returns a valid response, **Then** it passes schema validation and is stored in ai_insight.
2. **Given** the AI returns a response missing a required field, **When** schema validation runs, **Then** the response is rejected, an INSUFFICIENT_CONTEXT fallback is stored, and an error is logged.
3. **Given** a prompt without an output_schema, **When** the AI returns a response, **Then** it is stored as raw text without schema validation.

---

#### US-26.4 — INSUFFICIENT_CONTEXT Safety Enforcement (Priority: P2)

As a user viewing AI insights, I want the system to clearly indicate when the AI does not have enough context to provide a reliable answer, so that I do not act on uncertain AI output.

**Why this priority**: Safety handling is a non-negotiable standard. The spec requires the AI to never claim certainty beyond data.

**Independent Test**: Trigger insight generation for a finding with minimal context data, confirm the AI response includes an INSUFFICIENT_CONTEXT indicator and the UI shows a warning badge.

**Acceptance Scenarios**:

1. **Given** a finding with only a title and no resource metadata, **When** AI insight generation is triggered, **Then** the AI prompt includes an instruction to return `confidence: "low"` and the response is marked with an INSUFFICIENT_CONTEXT flag if confidence is below threshold.
2. **Given** an insight flagged as INSUFFICIENT_CONTEXT, **When** rendered in the UI, **Then** a yellow warning badge reads "Low confidence — limited context available."
3. **Given** the safety layer, **When** any AI response claims certainty (e.g., "this will definitely..."), **Then** the post-processing strips absolute certainty language.

---

#### US-26.5 — Prompt A/B Testing Scaffold (Priority: P3)

As a platform engineer, I want the ability to run two prompt versions simultaneously with traffic splitting, so that I can measure which prompt version produces better user feedback scores.

**Why this priority**: A/B testing is a scaffold for continuous prompt improvement; foundation only, not full experimentation platform.

**Independent Test**: Set two prompt versions to active with a 50/50 split, generate 10 insights, confirm approximately half use each version, and feedback is tracked per version.

**Acceptance Scenarios**:

1. **Given** two active versions of a prompt with traffic_pct=50 each, **When** 100 insight requests are made, **Then** approximately 50 use each version (within 10% tolerance).
2. **Given** feedback submitted for insights, **When** querying feedback by prompt version, **Then** the system returns average scores grouped by version.

---

### Edge Cases

- What happens if no prompt versions are active for a requested prompt name? Return a 503 with a clear error message.
- What if Bedrock rate limits are hit? Queue the request and retry with exponential backoff (max 3 retries).
- What if the output schema itself is invalid JSON Schema? Reject on prompt creation with a validation error.

### Functional Requirements

- **FR-26.01**: System MUST store prompt templates in a prompt_registry table with fields: id, name, version, template, model, output_schema, active, traffic_pct, created_at, updated_at.
- **FR-26.02**: System MUST route AI requests to Bedrock by default, with Ollama as configurable fallback.
- **FR-26.03**: System MUST validate AI responses against the prompt's output_schema when present.
- **FR-26.04**: System MUST flag AI responses as INSUFFICIENT_CONTEXT when confidence is below a configurable threshold.
- **FR-26.05**: Every AI insight MUST reference the prompt_registry entry (name + version) that generated it.
- **FR-26.06**: System MUST log provider, model, latency, token_count, and success/failure for every AI invocation.

### Key Entities

- **PromptRegistry**: id, name, version, template (text), model (string), output_schema (JSONB), active (bool), traffic_pct (int), created_at, updated_at
- **AIInvocationLog**: id, workspace_id, prompt_name, prompt_version, provider, model, latency_ms, input_tokens, output_tokens, success (bool), error_message, created_at

### Backend Deliverables

| Artifact | Path | Description |
|---|---|---|
| PromptRegistry model | `app/models/prompt_registry.py` | SQLAlchemy model for prompt templates |
| AIInvocationLog model | `app/models/ai_invocation_log.py` | Logging model for AI request telemetry |
| Prompt registry service | `app/services/prompt_registry_service.py` | CRUD + version management + A/B split logic |
| Bedrock provider | `app/integrations/aws/bedrock_provider.py` | Amazon Bedrock InvokeModel integration |
| Provider router | `app/services/ai_provider_router.py` | Routes requests to Bedrock or Ollama based on config |
| Output validator | `app/services/ai_output_validator.py` | JSON Schema validation for AI responses |
| Prompt registry router | `app/routers/prompt_registry.py` | CRUD API for prompt management |
| Update ai_service.py | `app/services/ai_service.py` | Integrate registry lookup, provider routing, output validation |
| Register in main.py | `app/main.py` | Import and include prompt_registry router |

### Frontend Deliverables

| Artifact | Path | Description |
|---|---|---|
| Prompt registry admin page | `app/dashboard/settings/prompts/page.tsx` | List, create, edit, activate prompt versions |
| AI invocation log viewer | `app/dashboard/settings/ai-logs/page.tsx` | View AI invocation telemetry (latency, errors) |
| Confidence badge component | `components/ui/confidence-badge.tsx` | Shows confidence level / INSUFFICIENT_CONTEXT warning |
| usePromptRegistry hook | `hooks/use-prompt-registry.ts` | Fetch and manage prompt registry entries |

### API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/prompts` | List all prompt registry entries (filterable by name, active status) |
| POST | `/api/v1/prompts` | Create a new prompt template (auto-assigns version) |
| GET | `/api/v1/prompts/{id}` | Get a specific prompt registry entry |
| PUT | `/api/v1/prompts/{id}` | Update prompt fields (template, model, output_schema, traffic_pct) |
| POST | `/api/v1/prompts/{id}/activate` | Set this version as active (deactivates other versions of same name) |
| GET | `/api/v1/prompts/{name}/versions` | List all versions of a named prompt |
| GET | `/api/v1/ai/invocations` | Query AI invocation logs (filterable by prompt, provider, success) |

### Dependencies

- Requires Sprint 6 (existing AI service, ai_insight model, ai_feedback model).
- Requires AWS credentials with Bedrock access (bedrock:InvokeModel permission).
- No dependency on Sprints 24-25.

### Success Criteria

- **SC-26.01**: All AI insight generation routes through the prompt registry (no hardcoded prompts in ai_service.py).
- **SC-26.02**: Bedrock integration handles 50 concurrent requests without errors.
- **SC-26.03**: Output schema validation catches 100% of malformed responses (verified with test fixtures).
- **SC-26.04**: INSUFFICIENT_CONTEXT flag is set when AI input context has fewer than 3 data fields.

---

## Sprint 27 — Attack Path Visualization (Domain F)

**Goal**: Build an interactive attack path explorer that visualizes how an attacker could chain vulnerabilities and misconfigurations to reach high-value targets, differentiating Cloud Posture Copilot from basic CSPM tools through relationship-aware risk prioritization.

### User Stories

#### US-27.1 — Attack Path Explorer Graph (Priority: P1)

As a security operator, I want an interactive graph visualization showing attack paths from entry points (public-facing resources) to high-value targets (databases, secrets), so that I can understand the real-world exploitability of my findings.

**Why this priority**: Attack path visualization is the core differentiator of Domain F and the primary value-add over commoditized CSPM scanners.

**Independent Test**: Navigate to `/dashboard/attack-paths`, see a directed graph with nodes (resources) and edges (relationships/vulnerabilities), click a node to see details.

**Acceptance Scenarios**:

1. **Given** an environment with a public S3 bucket linked to an EC2 instance with an IAM role that can access RDS, **When** viewing the attack path explorer, **Then** a directed graph shows: S3 -> EC2 -> IAM Role -> RDS with edge labels describing the relationship.
2. **Given** the graph, **When** the user clicks a node, **Then** a side panel shows resource details, associated findings, and risk score.
3. **Given** a graph with 100+ nodes, **When** rendered, **Then** the graph uses force-directed layout with zoom/pan controls and renders without frame drops.

---

#### US-27.2 — Blast Radius Visualization (Priority: P1)

As a security operator, I want to select any finding or resource and see its blast radius (what else is affected if this is compromised), so that I can prioritize fixes based on actual impact scope.

**Why this priority**: Blast radius transforms abstract severity scores into concrete impact understanding, which is the primary input to remediation prioritization.

**Independent Test**: Click a resource node in the graph, select "Show Blast Radius", see highlighted nodes and edges representing the blast radius with a count of affected resources.

**Acceptance Scenarios**:

1. **Given** a resource node is selected, **When** "Show Blast Radius" is clicked, **Then** all reachable nodes within 3 hops are highlighted with a colored overlay.
2. **Given** the blast radius view, **When** displayed, **Then** a summary panel shows: "X resources reachable, including Y critical assets."
3. **Given** a resource with no downstream connections, **When** blast radius is triggered, **Then** the UI shows "Isolated resource — no downstream impact detected."

---

#### US-27.3 — Relationship-Aware Finding Prioritization (Priority: P2)

As a security operator, I want findings ranked not just by severity but also by their position in attack paths (e.g., a medium-severity finding on a path to a critical database should rank higher), so that I fix the most impactful issues first.

**Why this priority**: This is the intelligence layer that makes attack paths actionable, not just visual.

**Independent Test**: View the findings list, confirm that findings on attack paths to critical assets have a boosted priority score and an "Attack Path" badge.

**Acceptance Scenarios**:

1. **Given** two findings with the same severity, **When** one is on an attack path to a critical RDS instance and the other is isolated, **Then** the attack-path finding has a higher composite risk score.
2. **Given** the findings list, **When** a finding has attack path context, **Then** an "Attack Path" badge is shown with a tooltip: "This finding is on a path to X critical assets."
3. **Given** the risk scoring engine, **When** attack path data is available, **Then** the path_centrality weight is applied per the causal engine's graph_centrality factor.

---

#### US-27.4 — Attack Path Risk Scoring (Priority: P2)

As a security operator, I want each attack path to have a composite risk score based on the severity of findings along the path and the value of the target asset, so that I can compare paths and prioritize remediation.

**Why this priority**: Without path-level scoring, operators cannot compare the relative danger of different attack paths.

**Independent Test**: View the attack paths list, confirm each path shows a score, sort by score, confirm the highest-risk paths involve the most critical targets.

**Acceptance Scenarios**:

1. **Given** an attack path with 3 hops involving a critical + high + medium finding targeting an RDS instance, **When** scored, **Then** the path risk score is calculated as a weighted sum of finding severities times target asset value.
2. **Given** the attack paths list, **When** sorted by risk score descending, **Then** paths targeting critical assets (databases, secrets managers) rank highest.

---

#### US-27.5 — Interactive Graph Enhancements (Priority: P3)

As a security operator, I want to filter the attack path graph by resource type, severity, and domain, so that I can focus on specific risk areas without visual overload.

**Why this priority**: Filtering is a usability enhancement that makes the graph practical for environments with many resources.

**Independent Test**: Apply a filter for "RDS targets only", confirm the graph re-renders showing only paths terminating at RDS resources.

**Acceptance Scenarios**:

1. **Given** the graph filter panel, **When** the user selects resource_type="RDS", **Then** only paths with RDS as a target are shown.
2. **Given** the graph filter panel, **When** the user selects severity="critical", **Then** only paths containing at least one critical finding are shown.

---

### Edge Cases

- What if no attack paths exist (new environment, no relationships)? Show empty state: "No attack paths detected. Ensure Security Hub and Config are ingesting data."
- What if a path has a cycle (e.g., cross-role assumption)? Detect and cap at max depth, display a "cycle detected" indicator.
- What if the graph has 1000+ nodes? Use server-side graph computation and client-side progressive rendering.

### Functional Requirements

- **FR-27.01**: System MUST compute attack paths using the security_graph_node and security_graph_edge models.
- **FR-27.02**: System MUST calculate blast radius as all nodes reachable within N hops (configurable, default 3).
- **FR-27.03**: System MUST score each attack path as a composite of finding severities and target asset criticality.
- **FR-27.04**: System MUST boost finding priority scores when the finding lies on an attack path to a critical asset.
- **FR-27.05**: Graph visualization MUST support zoom, pan, node click, and filter interactions.

### Key Entities

- **AttackPath**: id, workspace_id, source_node_id, target_node_id, hops (JSONB array of node IDs), risk_score, created_at
- **SecurityGraphNode** (existing): id, resource_type, resource_id, metadata
- **SecurityGraphEdge** (existing): id, source_node_id, target_node_id, relationship_type, metadata

### Backend Deliverables

| Artifact | Path | Description |
|---|---|---|
| AttackPath model | `app/models/attack_path.py` | SQLAlchemy model for computed attack paths |
| Attack path service | `app/services/attack_path_service.py` | Graph traversal, path computation, scoring |
| Blast radius service | `app/services/blast_radius_service.py` | BFS/DFS from a node to compute reachable resources |
| Attack path router | `app/routers/attack_paths.py` | API endpoints for paths, blast radius, graph data |
| Update causal_engine.py | `app/services/causal_engine.py` | Integrate path-based priority boost into risk scoring |
| Register in main.py | `app/main.py` | Import and include attack_paths router |

### Frontend Deliverables

| Artifact | Path | Description |
|---|---|---|
| Attack path explorer page | `app/dashboard/attack-paths/page.tsx` | Interactive graph visualization page |
| Graph canvas component | `components/attack-paths/graph-canvas.tsx` | Force-directed graph renderer (e.g., using react-force-graph or d3) |
| Blast radius overlay | `components/attack-paths/blast-radius-overlay.tsx` | Highlights reachable nodes from a selected resource |
| Path detail panel | `components/attack-paths/path-detail-panel.tsx` | Side panel showing path hops, findings, and score |
| Graph filter bar | `components/attack-paths/graph-filter-bar.tsx` | Filter by resource type, severity, domain |
| AttackPathBadge | `components/ui/attack-path-badge.tsx` | Badge for findings list showing attack path membership |
| useAttackPaths hook | `hooks/use-attack-paths.ts` | Fetch attack paths and graph data |
| useBlastRadius hook | `hooks/use-blast-radius.ts` | Fetch blast radius for a given resource |

### API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/attack-paths` | List computed attack paths for the workspace (filterable, sortable by risk_score) |
| GET | `/api/v1/attack-paths/{id}` | Get a specific attack path with full hop details |
| GET | `/api/v1/attack-paths/graph` | Returns nodes + edges for the graph visualization (supports filter params) |
| GET | `/api/v1/resources/{id}/blast-radius` | Compute and return blast radius for a specific resource |
| POST | `/api/v1/attack-paths/compute` | Trigger attack path recomputation for the workspace |

### Dependencies

- Requires Sprint 3 (canonical finding model, security graph models).
- Requires Sprint 4 (causal engine, risk scoring).
- Benefits from Sprint 25 (design system components) but not blocking.

### Success Criteria

- **SC-27.01**: Attack path computation completes in under 30 seconds for an environment with 500 resources and 2000 edges.
- **SC-27.02**: Graph visualization renders 200 nodes without frame drops on a standard laptop.
- **SC-27.03**: Blast radius correctly identifies all reachable nodes (verified against manual graph traversal in tests).
- **SC-27.04**: Findings on attack paths to critical assets have measurably higher risk scores than equivalent isolated findings.

---

## Sprint 28 — Drift Detection & Root Cause v2

**Goal**: Implement configuration drift detection by comparing resource state snapshots over time, and upgrade root cause analysis to v2 with multi-finding correlation that explains why groups of findings co-occur, building the intelligence moat that differentiates the platform.

### User Stories

#### US-28.1 — Configuration Drift Detection (Priority: P1)

As a security operator, I want the system to detect when a resource's configuration changes between scans (e.g., a security group rule is added, encryption is disabled), so that I can identify and investigate unauthorized or accidental changes.

**Why this priority**: Drift detection is the foundation of Sprint 28 and the prerequisite for drift alerts and timeline visualization.

**Independent Test**: Trigger two scans of the same environment where a security group rule was added between scans, confirm the system detects and records the drift event.

**Acceptance Scenarios**:

1. **Given** two consecutive scan snapshots of a security group, **When** a new inbound rule (0.0.0.0/0 on port 22) was added between scans, **Then** a drift event is created with type="rule_added", resource_id, before_state, after_state, and detected_at.
2. **Given** a resource with no configuration changes between scans, **When** drift detection runs, **Then** no drift event is created for that resource.
3. **Given** drift detection across 1000 resources, **When** executed, **Then** it completes within 60 seconds.

---

#### US-28.2 — Recurrence Detection (Priority: P1)

As a security operator, I want the system to detect when a finding that was previously resolved reappears, so that I can identify systemic issues that require a deeper fix rather than repeated patching.

**Why this priority**: Recurrence is a strong signal that the root cause is not being addressed; this directly feeds the root cause v2 engine.

**Independent Test**: Resolve a finding, trigger a new scan where the same issue reappears, confirm the finding is flagged as "recurrent" with a recurrence count.

**Acceptance Scenarios**:

1. **Given** a finding that was resolved, **When** a new scan produces the same finding (matching fingerprint), **Then** the finding is reopened with status="recurrent" and recurrence_count incremented.
2. **Given** a recurrent finding, **When** viewed in the findings list, **Then** a "Recurrent (Nx)" badge is shown where N is the recurrence count.
3. **Given** the recurrence history, **When** the user clicks the badge, **Then** a timeline popover shows each occurrence with dates.

---

#### US-28.3 — Root Cause v2: Multi-Finding Correlation (Priority: P1)

As a security operator, I want the system to identify groups of findings that co-occur due to a shared root cause (e.g., 5 S3 findings all caused by a missing org-level SCP), so that I can fix one root cause instead of 5 individual findings.

**Why this priority**: This is the core intelligence upgrade that transforms the platform from a finding-list tool to a diagnostic tool.

**Independent Test**: Ingest 5 S3 public access findings across different buckets that share the same account-level block public access setting being disabled, confirm the system groups them and identifies the root cause.

**Acceptance Scenarios**:

1. **Given** 5 findings with the same root_cause_category and affecting resources in the same account, **When** root cause v2 analysis runs, **Then** a root_cause_group is created linking all 5 findings with a shared explanation.
2. **Given** a root cause group, **When** viewed, **Then** it shows the group title, shared root cause, affected finding count, and a remediation suggestion that fixes all findings at once.
3. **Given** the findings list, **When** a finding belongs to a root cause group, **Then** a "Root Cause Group (5 findings)" link is shown that navigates to the group detail view.

---

#### US-28.4 — Drift Alerts in Detection Engine (Priority: P2)

As a security operator, I want drift events to generate alerts in the detection engine, so that high-risk configuration changes trigger immediate notifications.

**Why this priority**: Drift without alerting is passive; integrating with the existing detection engine makes drift actionable.

**Independent Test**: Configure a drift alert rule for "security group changes", trigger a drift event, confirm the detection engine fires an alert and the notification appears.

**Acceptance Scenarios**:

1. **Given** a drift alert rule for resource_type="security_group" and drift_type="rule_added", **When** a matching drift event occurs, **Then** the detection engine creates a detection with severity based on the drift risk.
2. **Given** a drift-triggered detection, **When** viewed in the detections dashboard, **Then** it shows the drift context: what changed, before state, after state.
3. **Given** notification preferences, **When** a drift alert fires, **Then** notifications are sent via the existing notification channels (webhook, email).

---

#### US-28.5 — Drift Timeline in Finding Detail View (Priority: P2)

As a security operator, I want to see a timeline of configuration changes on the finding detail page, so that I can correlate when the drift occurred with when the finding was first detected.

**Why this priority**: Temporal correlation between drift and finding creation is powerful diagnostic information.

**Independent Test**: Open a finding detail page for a finding that has associated drift events, confirm a timeline section shows configuration changes with timestamps.

**Acceptance Scenarios**:

1. **Given** a finding detail page for a resource with 3 drift events, **When** rendered, **Then** a "Configuration History" timeline section shows each drift event with timestamp, change type, and before/after summary.
2. **Given** the timeline, **When** a drift event timestamp is close to the finding's first_seen_at, **Then** the drift event is highlighted with a label "Likely trigger."
3. **Given** a finding with no drift events, **When** the detail page renders, **Then** the timeline section shows "No configuration changes detected."

---

### Edge Cases

- What if the before-state snapshot is missing (first scan)? Skip drift detection for that resource on the first scan, record the initial snapshot only.
- What if a root cause group grows to 100+ findings? Cap the display at 20 with a "Show all N findings" expansion.
- What if drift detection produces false positives from expected changes (e.g., autoscaling)? Allow users to mark drift events as "expected" which suppresses future alerts for that pattern.

### Functional Requirements

- **FR-28.01**: System MUST store resource configuration snapshots per scan with a diff-able structure.
- **FR-28.02**: System MUST compute drift by comparing consecutive snapshots of the same resource (keyed by resource_id + region).
- **FR-28.03**: System MUST detect finding recurrence by matching fingerprints of resolved findings against new scan results.
- **FR-28.04**: System MUST group co-occurring findings by shared root_cause_category + account/region to form root cause groups.
- **FR-28.05**: System MUST generate detection engine alerts for drift events matching configured rules.
- **FR-28.06**: System MUST display a configuration history timeline on finding detail pages.

### Key Entities

- **ResourceSnapshot**: id, workspace_id, resource_id, resource_type, region, configuration (JSONB), scan_job_id, captured_at
- **DriftEvent**: id, workspace_id, resource_id, resource_type, drift_type (enum: added, removed, modified), property_path, before_value, after_value, scan_job_id, detected_at
- **RootCauseGroup**: id, workspace_id, title, root_cause_category, shared_explanation, remediation_hint, finding_count, created_at, updated_at
- **RootCauseGroupMember**: id, root_cause_group_id, finding_id

### Backend Deliverables

| Artifact | Path | Description |
|---|---|---|
| ResourceSnapshot model | `app/models/resource_snapshot.py` | SQLAlchemy model for configuration snapshots |
| DriftEvent model | `app/models/drift_event.py` | SQLAlchemy model for detected configuration changes |
| RootCauseGroup model | `app/models/root_cause_group.py` | SQLAlchemy model for correlated finding groups |
| RootCauseGroupMember model | `app/models/root_cause_group_member.py` | Join table linking findings to root cause groups |
| Drift detection service | `app/services/drift_detection_service.py` | Compares snapshots, creates DriftEvents |
| Recurrence detection service | `app/services/recurrence_service.py` | Detects reopened findings, updates recurrence_count |
| Root cause v2 service | `app/services/root_cause_v2_service.py` | Multi-finding correlation and group creation |
| Drift router | `app/routers/drift.py` | API endpoints for drift events and timeline |
| Root cause groups router | `app/routers/root_cause_groups.py` | API endpoints for root cause group management |
| Update detection_service.py | `app/services/detection_service.py` | Add drift-triggered detection rules |
| Update scanner flow | `app/services/scanner_service.py` (or equivalent) | Save ResourceSnapshot after each scan |
| Register in main.py | `app/main.py` | Import and include drift + root_cause_groups routers |

### Frontend Deliverables

| Artifact | Path | Description |
|---|---|---|
| Drift events page | `app/dashboard/drift/page.tsx` | List of drift events with filters (resource type, drift type, date range) |
| Root cause groups page | `app/dashboard/root-cause-groups/page.tsx` | List of root cause groups with finding counts |
| Root cause group detail | `app/dashboard/root-cause-groups/[id]/page.tsx` | Group detail with explanation, findings list, remediation hint |
| Drift timeline component | `components/findings/drift-timeline.tsx` | Timeline visualization of configuration changes on finding detail |
| RecurrenceBadge component | `components/ui/recurrence-badge.tsx` | "Recurrent (Nx)" badge with timeline popover |
| DriftEventCard component | `components/drift/drift-event-card.tsx` | Card showing before/after state diff |
| useDriftEvents hook | `hooks/use-drift-events.ts` | Fetch drift events for a resource or workspace |
| useRootCauseGroups hook | `hooks/use-root-cause-groups.ts` | Fetch root cause groups |
| useRecurrence hook | `hooks/use-recurrence.ts` | Fetch recurrence history for a finding |

### API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/drift/events` | List drift events for the workspace (filterable by resource_type, drift_type, date range) |
| GET | `/api/v1/drift/events/{id}` | Get a specific drift event with full before/after state |
| GET | `/api/v1/resources/{id}/drift-timeline` | Get drift events for a specific resource, ordered by time |
| POST | `/api/v1/drift/events/{id}/mark-expected` | Mark a drift event as expected (suppresses future alerts for pattern) |
| GET | `/api/v1/root-cause-groups` | List root cause groups for the workspace |
| GET | `/api/v1/root-cause-groups/{id}` | Get root cause group detail with member findings |
| POST | `/api/v1/drift/compute` | Trigger drift detection for the latest scan |
| POST | `/api/v1/root-cause-groups/compute` | Trigger root cause v2 analysis |
| GET | `/api/v1/findings/{id}/recurrence` | Get recurrence history for a finding |

### Dependencies

- Requires Sprint 3 (canonical finding model, scanner service, fingerprint-based dedup).
- Requires Sprint 4 (causal engine, root cause v1 weighting).
- Requires Sprint 23 (detection engine) for drift alert integration.
- Benefits from Sprint 25 (RootCauseChip, TimestampLabel) for consistent UI.

### Success Criteria

- **SC-28.01**: Drift detection correctly identifies configuration changes between consecutive scans (verified with 10+ test fixtures).
- **SC-28.02**: Recurrence detection identifies reopened findings with 100% accuracy (matching by fingerprint).
- **SC-28.03**: Root cause v2 groups at least 3 known co-occurring finding patterns (S3 public access, SG over-permissive, encryption disabled).
- **SC-28.04**: Drift-triggered alerts appear in the detections dashboard within 5 seconds of drift computation completing.
- **SC-28.05**: Finding detail page shows configuration history timeline with correct chronological ordering.

---

## Cross-Sprint Dependencies Matrix

| Sprint | Depends On | Depended On By |
|---|---|---|
| Sprint 24 (MSP Portfolio) | Sprints 0-7 (foundation, RBAC, risk scoring, SLA, reports) | Sprint 25 (benefits from shared components) |
| Sprint 25 (Design System) | Sprints 6-7 (AI feedback endpoint, existing pages) | Sprints 27-28 (shared UI components) |
| Sprint 26 (AI Prompt Registry) | Sprint 6 (AI service, ai_insight, ai_feedback models) | Future sprints using AI (all) |
| Sprint 27 (Attack Paths) | Sprints 3-4 (canonical model, security graph, causal engine) | Sprint 28 (benefits from path context for root cause v2) |
| Sprint 28 (Drift & RCA v2) | Sprints 3-4, Sprint 23 (detection engine) | Future intelligence features |

## Assumptions

- Backend follows the established pattern: FastAPI router + service + SQLAlchemy model, registered in `app/main.py`.
- Frontend follows Next.js App Router with pages at `app/dashboard/*/page.tsx` and hooks at `hooks/use-*.ts`.
- All new sidebar nav items are added to `components/shell/sidebar-nav.tsx`.
- RBAC enforcement uses the existing auth middleware (JWT + workspace_id scoping).
- Database migrations are managed with Alembic.
- PDF generation reuses the existing report_service infrastructure from Sprint 5.
- Graph visualization on the frontend uses a library such as react-force-graph, d3-force, or equivalent.

## Definition of Done (per Sprint)

1. Backend service + router created and registered in main.py.
2. Database models created with Alembic migration.
3. API endpoints tested via curl/httpx (happy path + error cases).
4. Frontend hooks + pages built and added to sidebar navigation.
5. Empty/loading/error states handled using Sprint 25 components (or inline if Sprint 25 not complete).
6. No console errors in browser.
7. Verified in browser with screenshot.
8. PR passes review checklist (no god-files, no unrelated edits, shared types respected).
