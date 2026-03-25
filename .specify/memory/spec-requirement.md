# Cloud Posture Copilot — Full Product Scope & Requirements

## Source: WIZ Project .pages (Founder Blueprint Document)

---

## Vision Statement

**Cloud Posture Copilot** — AWS-native Cloud Security Operations Platform
*(Powered by AWS-native security signals + our value-add intelligence layer)*

- NOT a "cloud security tool" / "AWS scanner" / "cheap Wiz clone"
- WE ARE: Managed Cloud Security Posture & Risk Operations for AWS
- Helps SMBs, SaaS companies, and MSPs continuously monitor findings, prioritize real risks, identify root causes, map issues to compliance, and drive remediation through user-friendly workflows

### Core Strategy
- Primary focus = AWS (Azure/GCP after AWS PMF)
- Core service offering = deep CSPM layer
- Value-add = Unified experience + prioritization + root cause + descriptive + prescriptive analysis
- Roadmap later = data + identity + workloads + code context

### Competitive Position
- Wiz is broader/more mature: code-to-runtime, graph-based prioritization, identity + workload + data + multi-cloud
- Our strategy: Deep AWS-first wedge, not competing head-on
- Combine deterministic intelligence + AI-guided analysis / RCA

---

## 7 Product Domains (Scope Definition)

### DOMAIN A: Critical Exposure & Misconfiguration (Must-have MVP)
- S3 bucket public access, encryption, block public access
- Security groups open to world (22, 3389, 0-65535)
- Publicly accessible RDS, EBS/RDS snapshots
- Lambda function authentication
- Load balancer unrestricted, internet-facing
- Blast radius analysis
- Deduplication
- Strong sales narrative, easy wins, high impact

### DOMAIN B: Control Baseline & Compliance Failure
- Hygiene gaps: MFA disabled, not enabled, cross-region issues
- Log file recording requirements off
- KMS key defaults, encryption gaps
- No delete protection
- Weak audit, blind spots
- FSBP, SOC2, ISO 27001 mapping
- SLA tracking, accept/reject/exceptions
- Executive summaries & dashboards

### DOMAIN C: Identity & Access Risk (CIEM-lite)
- IAM users, wildcard permissions
- Cross-account access, stale credentials
- Human vs automated role assumption
- Privilege escalation, dangerous permissions
- Federation specifics, misuse detection
- Premium feature: toxic combinations, least-privilege recommendations
- MVP/initial: IAM Access Analyzer integration

### DOMAIN D: Workload & Runtime Security
- EC2/ECR/Lambda vulnerability scanning
- ECR image scanning
- CVE evaluation
- Assurance angle, package vulnerabilities
- AMIs, old/deployed images
- Checkpoint/gold image standards

### DOMAIN E: Data Security & Privacy
- PII/sensitive data detection (Macie later)
- Shadow data, backup concerns
- Non-encrypted data stores
- S3 bucket policy principals
- Data classification

### DOMAIN F: Attack-Chain Lite
- Relationship-aware prioritization
- Attack path visualization
- Security graph (strategic)
- Drift + root cause v2

### DOMAIN G: Prevention & Code Context
- Terraform, SG rule approvals
- Infrastructure as Code scanning
- Module bypass detection
- Code context integration (Phase 3+)

---

## 3 Commercial Product SKUs

### SKU 1: Deep CSPM Ops (Entry Tier / Phase 1)
- **Buyer**: SMB SaaS, lean DevOps teams
- Exposure findings, coverage assurance
- Dashboards, weekly reports
- Sellable product

### SKU 2: Compliance & Diagnostic Pack (Mid-market)
- Root cause analysis, diagnostic intelligence
- Compliance mapping
- MSP / vCISO Console (best GTM entry)
- Multi-tenant, white-label, portfolio dashboards

### SKU 3: Contextual Risk Pack (Phase 3+)
- IAM Access Analyzer deep integration
- Attack chain analysis
- Full identity + data + workload context

---

## Phased Product Roadmap

### Phase 1: Deep CSPM Ops (MVP)
- Goal: Freeze scope, launch as sellable product
- Focus: Misconfiguration, security baseline, entry product
- Output: Ops Platform
- Competitors: Prowler/ScoutSuite (open-source), Orca, Drata, vCISO tools

### Phase 2: Compliance + Intelligence
- CIEM-lite, ECR/Lambda scanning
- Sensitive data + storage awareness
- Attack path relationship mapping
- Drift + root cause v2
- MSP / Workflow Pack
- Multi-tenant + governance workflows

### Phase 3: Unified CNAPP
- Code-to-runtime surface
- K8s, developer context
- AI-guided analysis / RCA
- Multi-cloud (Azure/GCP)
- Contextual Risk Pack

---

## Engineering Architecture

### Data Sources (Signal Ingestion)
- AWS Security Hub (CSPM primary)
- AWS Config
- Amazon GuardDuty
- AWS Inspector (later)
- Macie (later)
- IAM Access Analyzer
- Trusted Advisor (selective)
- AWS Organizations (org-wide)
- CloudTrail / CloudWatch metadata
- API collection

### Deterministic Intelligence (Product Moat)
- Risk scoring v1 (without AI dependency)
- Domain classification
- Coverage analysis
- Root cause v1
- Blast radius
- Control baseline checks

### AI Architecture
- AI Safe Layer (critical)
- No direct model SDK calls outside designated providers
- AI Data Model (locked): stores every generated insight
- Required fields: workspace_id, input_context_hash
- ai_feedback table (accepted, edited)
- Prompt Registry (production templates)
- Provider Strategy: Amazon Bedrock primary
- Output Contracts (non-negotiable): structured JSON schemas
- Safety: never claim certainty beyond data, INSUFFICIENT_CONTEXT handling

### Backend Standards
- Python 3.11+
- FastAPI + SQLAlchemy async
- Canonical model + normalization
- Job/event architecture
- Health endpoints
- AssumeRole validation
- Security Hub connector
- GuardDuty enabled-state checks

### Frontend Standards
- Next.js + TypeScript + Tailwind
- Design system style guidelines
- Neutral base, clean typography
- Fixed left sidebar navigation
- Empty/loading/error states (polished)
- Sort/search UX laws
- Frontend data contracts

---

## UI Pages Required (Gold Standard)

### Page 1-3: Core Dashboard
- Executive Dashboard (2-column zone)
- Operator Core dashboard
- Compliance overview

### Page 4: Executive Summary
- Risk zone, trend, portfolio view

### Page 5-6: Findings
- Findings list with detail pages
- Root cause chips, timestamp labels
- AI feedback bars

### Page 7: Security Graph
- Relationship visualization

### Page 8: Compliance Center
- FrameworkScoreCard
- ControlFamilyHeatmap
- ImpactTable
- ComplianceExceptions
- Do not imply legal guarantee

### Page 9: Reports Center
- Generate reports (PDF)
- Exec + engineering + MSP use cases
- Type selector, status badge
- Includes AI Summary (yes/no toggle)

### Page 10: Settings / Admin
- AWS accounts management
- AI entitlement flags (display only early)
- Tenant/workspace configuration

### MSP / vCISO Features
- Portfolio Dashboard: which clients at risk? unresolved criticals? SLA breaches?
- Client Workspace Switcher: fast context switching
- Scorecard View: client-friendly reports
- Inventory (Master): full asset/finding inventory

### Component Library
- RootCauseChip
- TimestampLabel
- AIFeedbackBar
- CreateDrawer
- Deterministic logic defaults
- Full-screen default
- Helpful/unhelpful feedback

---

## Sprint-by-Sprint Master Build Plan

### Sprint 0: Foundation
- Infrastructure/docker bootstrap
- Job lifecycle
- Health endpoint
- Tenant/workspace/user foundation (RBAC)

### Sprint 1: SSOT Bootstrap
- Backend skeleton
- Startup sequence

### Sprint 2: Tenant / Workspace / Account Core
- Status visible, account management

### Sprint 3: Security Ingestion + Canonical Model
- Turn fragmented findings into canonical model
- Security Hub + Config + GuardDuty source ingestion

### Sprint 4: Deterministic Intelligence
- Risk scoring + coverage + root cause v1

### Sprint 5: Workflow & Reporting
- States + tasks + exceptions + SLA
- Assignment, safe/obvious insights
- Insight persistence
- Demo and pilot readiness

### Sprint 6: AI Safe Layer v1
- AI cards/panels
- Saved views basic

### Sprint 7: MVP UI Hardening
- Dashboard + detail pages
- App shell, shared packages

### Sprint 8+: Advanced Phases
- MSP / vCISO Pack: multi-client + white-label + portfolio
- Advanced Intelligence: drift + root cause v2
- Attack-Chain Lite: relationship-aware prioritization
- Multi-cloud: Azure/GCP after AWS PMF
- Prevention & Code Context

---

## Non-Negotiable Engineering Guardrails

1. Cursor/AI IDE rules: must only be used for explicit actions with criteria
2. Make it enterprise-grade
3. Locked data model standard
4. Allow/forbid file boundaries
5. No random schemas, shared types
6. No god-files
7. Sprint-by-sprint build order
8. Review checklist for every PR
9. AI-specific review checklist
10. Safe build prompts
11. What to reject immediately: edits to unrelated files, breaks shared types

---

## Key References
- https://docs.aws.amazon.com/securityhub/latest/userguide/
- https://www.wiz.io/platform
- AWS FSBP standard
- AWS Organizations setup
- AWS Access Analyzer
- AWS Config developer guide
