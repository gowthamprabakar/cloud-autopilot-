---
name: Cloud Posture Copilot — Product Knowledge Base
description: Extracted knowledge from WIZ Project .pages — product vision, architecture, domains, sprint plan, AI rules, and SSOT doc structure
type: project
---

# Cloud Posture Copilot — Knowledge Base Summary

## Product Vision
- **Not** a Wiz clone or random AWS scanner
- Deep CSPM wedge for AWS, architected to evolve into unified platform
- **Core value-add**: Unified experience + prioritization + root cause + descriptive + prescriptive analysis
- **Target buyers**: SMBs, SaaS companies, MSPs
- **Business description**: Helps SMBs/SaaS/MSPs continuously monitor findings, prioritize real risks, identify blind spots, map to compliance, and drive remediation through workflow

## Core Architecture Positioning
- AWS-native signal plane + custom intelligence plane + workflow plane + AI assist plane
- **Signal sources**: Security Hub, AWS Config, GuardDuty, Inspector, Macie (later), IAM Access Analyzer, Trusted Advisor, Organizations, CloudTrail/CloudWatch
- **AI is assistive, grounded, auditable, bounded** — NEVER source of truth
- Deterministic core first; AI augmentation second

## Product Tiers (Commercial)
1. **Baseline** — Entry tier, SMB SaaS/lean DevOps, exposure findings, IAC failures, coverage assurance, dashboards, weekly reports
2. **Ops MVP** — Mid-market, root cause analysis, diagnostics, trend + SLA
3. **MSP / vCISO Consolidator** — Best GTM, multi-tenant, white-label
4. **Quantified Risk Pack** (Phase 3+) — IAM Access Analyzer, inspector enrichment

## 7 Core Domains
1. Asset & Exposure
2. HH & Guardrails (hardening/hygiene)
3. Compliance & Regression
4. Misconfiguration (public S3, open SSH/RDP, open snapshots, EKS endpoint)
5. Drift + Root Cause v2
6. MSP / Workflow Pack
7. Multi-cloud (later)

## Phased Product Roadmap
| Phase | Name | Key Deliverables |
|-------|------|-----------------|
| Phase 0 | Bootstrap | Skeleton, health endpoint, auth stub, CI lint/test |
| Phase 1 | Core Data & Onboarding | Tenant/workspace/user foundation, AWS onboarding, AssumeRole validation, runner abstraction |
| Phase 2 | Security Ingestion v1 | Security Hub + Config + GuardDuty source ingest, canonical model + normalization |
| Phase 3 | Deterministic Intelligence | Risk scoring + coverage + root cause v1, product moat without AI dependency |
| Phase 4 | Workflow & Reports | States + tasks + exceptions + SLA, exec + engineering + MSP reports |
| Phase 5 | AI Safe Layer v1 | AI summaries, insight persistence, safe/obvious outputs |
| Phase 6 | MVP UI Hardening | Dashboard, finding detail, app shell, shared packages |
| Phase 7+ | MSP / vCISO Pack | Multi-client, white-label, portfolio, Attack-Chain Lite |
| Phase 8+ | Multi-cloud | Azure/GCP after AWS PMF |

## Sprint 0 (First Sprint)
- infra/docker
- Next.js skeleton
- Job lifecycle
- Config placeholders
- Health endpoint
- Auth stub
- CI lint/test

## Tech Stack (Locked)
- **Backend**: Python 3.11+, snake_case, layered architecture
- **Frontend**: Next.js + TypeScript + Tailwind + shadcn/ui
- **AI**: Provider abstraction (Bedrock primary, OpenAI for dev speed), prompt registry, structured output first
- **DB**: PostgreSQL with uuid PKs, timestamptz, proper indexes, migrations
- **Jobs**: Async job orchestration for heavy tasks

## Backend Architecture Rules
- routers/controllers → services → repositories/data access → models/schemas
- No AWS SDK calls in API routes
- No scoring logic in routes
- AI services CANNOT write to risk_score, priority_rank, or compliance_state
- No raw source findings written directly into canonical findings

## AI Architecture (Locked)
- No direct model SDK calls outside `services/ai/providers/`
- Prompt registry + versioning required
- Bounded context builders — no raw payload dumps, no entire cloud JSON blobs
- `ai_insights` table: stores every generated artifact (tenant_id, workspace_id, object_type, input_context_hash, confidence)
- `ai_feedback` table: accepted, edited, rejected (Phase 2 mandatory)
- Output schema: structured first, prose second; hypothesis, why_it_matters, evidence_refs, non-empty arrays, no unsupported markdown/HTML

## Frontend Rules
- Executive Overview: Top 10 Actions PROMINENT
- Finding Detail: most trustworthy + usable page
- Coverage Dashboard: blind spots obvious
- AI placement NON-NEGOTIABLE: deterministic evidence shown BEFORE AI on all operator pages
- No floating AI chat-first UX in MVP
- All major pages require loading, empty, error states

## Key Competitive Positioning
- Wiz is broader/more mature (code-to-runtime, graph-based, multi-cloud)
- Our strategy: Deep AWS-first wedge → attack-chain-lite → relationship-aware prioritization → drift + root cause
- NOT trying to compete head-on with Wiz
- Win at: blind spot coverage mapping, SLA tracking, exceptions/acceptance, exec summaries, MSP/multi-tenant client views

## SSOT Document Structure (from Pages doc)
Sections found:
- SECTION 0: Executive Lock + Product Constitution
- Golden Principles (Non-Negotiable)
- Engineering Standards
- Guardrails (Non-Negotiable)
- Data Model
- Event/Job Architecture + Pipelines
- User Stories
- Release Build Order
- Sprint-by-Sprint Master Build Plan
- Module-Level Acceptance Criteria (Gold Standard)
- AI Prompt Registry
- Provider Strategy
- AI Validation & Safety Layer (Critical)
- AI Eval Framework
- Cursor Usage Rules
- Frontend Data Contracts
- Design System Style Guidelines
- Safe Build Prompts
- Review Checklists (general + AI-specific)

## Key Enums / Status Values (from doc fragments)
- Job statuses: UNAUTHORIZED, FORBIDDEN, JOB_LIMITED, JOB_FAILED, INSUFFICIENT_CONTEXT, stale_*
- Finding fields: tenant_id, workspace_id, approved_by, sla_due_at
- IAM ARN pattern: `arn:aws:iam::.+`
- Account numbers: strictly 12 digits

## Vibe-Tools Location
All support repos cloned to: `/Users/prabakarannagarajan/Desktop/cloud copilot /vibe-tools/`
