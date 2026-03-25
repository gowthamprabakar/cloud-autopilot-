# Cloud Posture Copilot — Speckit Implementation Plan

## Current State: ~72% of full scope built (Sprints 0-23 complete)

## Remaining Sprints (Priority Order)

---

### Sprint 24 — MSP / vCISO Portfolio Dashboard (HIGH PRIORITY — GTM)
**Why**: Document says "Best GTM entry" — this unlocks the commercial SKU 2 revenue path.
- Portfolio dashboard: cross-workspace risk heatmap
- Client workspace switcher (fast context switch)
- Portfolio-level SLA breach view
- Client scorecard (PDF-exportable)
- White-label foundation (workspace branding settings)

### Sprint 25 — Design System Component Library
**Why**: Document mandates "Gold Standard" reusable components.
- Extract: RootCauseChip, TimestampLabel, AIFeedbackBar
- Build: CreateDrawer (slide-over for new finding/assignment/exception)
- Build: FrameworkScoreCard, ControlFamilyHeatmap
- Ensure all pages use shared component library
- Empty/Loading/Error state consistency pass

### Sprint 26 — AI Prompt Registry & Provider Strategy
**Why**: Document locks this as "NON-NEGOTIABLE" engineering standard.
- Formal prompt_registry table (name, version, template, model, active)
- Prompt versioning + A/B testing scaffold
- Bedrock provider integration (alongside Ollama)
- INSUFFICIENT_CONTEXT handling enforcement
- Output contract schema validation
- ai_feedback loop: accepted/edited/rejected tracking

### Sprint 27 — Attack Path Visualization (Domain F)
**Why**: Attack-chain-lite is differentiation from basic CSPM tools.
- Attack path explorer UI (graph visualization)
- Blast radius visualization (how far can an attacker reach?)
- Relationship-aware finding prioritization
- Interactive security graph enhancements
- Attack path risk scoring

### Sprint 28 — Drift Detection & Root Cause v2
**Why**: "Drift + recurrence" is core intelligence moat.
- Configuration drift detection (compare snapshots over time)
- Recurrence detection (same finding resolved then reopened)
- Root cause v2: multi-finding correlation (why group of findings co-occur)
- Drift alerts in detection engine
- Drift timeline in finding detail view

### Sprint 29 — Data Security Foundation (Domain E)
**Why**: Domain E is 0% complete; needed for compliance buyers.
- Macie integration scaffold (or mock for demo)
- S3 bucket data classification (PII/PHI/PCI labels)
- Unencrypted data store inventory
- Shadow data detection (S3 buckets not in known asset inventory)
- Data sensitivity scoring in causal engine

### Sprint 30 — IAM Access Analyzer Integration (Domain C deep)
**Why**: Premium CIEM feature; differentiates from basic IAM inventory.
- IAM Access Analyzer API integration
- External access findings (resources shared outside account)
- Unused access findings (permissions not used in 90 days)
- Toxic combination detection (dangerous permission pairs)
- Least-privilege recommendations

### Sprint 31 — ECR/Lambda Vulnerability Scanning (Domain D deep)
**Why**: Workload security gap; needed for CNAPP positioning.
- ECR image scan results ingestion (Inspector v2)
- Lambda layer vulnerability tracking
- AMI age/compliance checking
- Container image gold standard validation
- SBOM (Software Bill of Materials) foundation

### Sprint 32 — Prevention & Code Context (Domain G)
**Why**: Phase 3 feature but foundational scaffold should exist.
- Terraform plan analysis scaffold
- IaC drift correlation (Terraform state vs actual)
- SG rule change approval workflow
- Code context links (finding -> IaC file)

### Sprint 33 — Multi-Cloud Foundation
**Why**: Document roadmaps Azure/GCP after AWS PMF.
- Provider abstraction layer
- Azure Security Center connector scaffold
- GCP Security Command Center connector scaffold
- Multi-cloud normalized finding model

---

## Quick Wins (Can be done anytime)

1. **Sort/Search consistency pass** — Ensure all list pages have consistent filter/sort/search
2. **Error state polish** — Ensure all pages handle API errors gracefully
3. **Compliance framework coverage** — Add FSBP, SOC2, ISO 27001 control mappings
4. **Finding detail page enhancement** — Add RootCauseChip, AIFeedbackBar inline
5. **Onboarding wizard polish** — Guided AWS account connection flow

---

## Definition of Done (per Sprint)

1. Backend service + router created
2. Registered in main.py
3. API tested via curl
4. Frontend hooks + page built
5. Added to sidebar nav
6. Verified in browser with screenshot
7. No console errors on the page
