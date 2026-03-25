# Cloud Posture Copilot — Scope vs Built Gap Analysis

## Legend
- BUILT = Feature exists and functional
- PARTIAL = Some implementation exists but incomplete
- MISSING = Not yet built

---

## Sprint 0-3: Foundation & Ingestion

| Requirement | Status | Notes |
|---|---|---|
| Health endpoint | BUILT | `/health` returns ok |
| Tenant/workspace/user (RBAC) | BUILT | models: tenant, workspace, user; auth router with JWT |
| AWS account onboarding | BUILT | aws_accounts router + service + AssumeRole validation |
| Security Hub connector | BUILT | scanner service ingests Security Hub findings |
| GuardDuty ingestion | BUILT | scanner service |
| Config ingestion | BUILT | scanner service |
| Canonical model + normalization | BUILT | canonical_finding model + normalization_service |
| Deduplication (fingerprint) | BUILT | canonical_finding.fingerprint |
| Job lifecycle | BUILT | job_run + scan_job models |
| TOTP/MFA for users | BUILT | totp router + service |

## Sprint 4: Deterministic Intelligence

| Requirement | Status | Notes |
|---|---|---|
| Risk scoring v1 | BUILT | causal_engine.py (weighted formula) + risk_score_service.py |
| Domain classification | PARTIAL | causal engine has weight categories but no formal domain classifier |
| Coverage analysis | PARTIAL | executive summary has counts but no per-control coverage tracking |
| Root cause v1 | PARTIAL | causal engine does root cause weighting; no dedicated RCA output |
| Blast radius | PARTIAL | causal engine has blast_radius weight; no visual blast radius UI |

## Sprint 5: Workflow & Reporting

| Requirement | Status | Notes |
|---|---|---|
| SLA tracking | BUILT | sla router + risk_score_service SLA compliance |
| Finding assignment | BUILT | assignment_service + finding_assignment model |
| Suppression/exceptions | BUILT | suppression router + service + rule model |
| Reports (PDF generation) | BUILT | reports router + report_service + report_schedule |
| Email digest | BUILT | email_digest router + digest_service |
| Jira integration | BUILT | jira router + service + jira_ticket model |
| Webhook notifications | BUILT | webhooks router + service |
| Audit log | BUILT | audit_log router + service |
| Notifications | BUILT | notifications router + service |

## Sprint 6: AI Safe Layer v1

| Requirement | Status | Notes |
|---|---|---|
| AI insight generation | BUILT | ai router + ai_service |
| AI feedback (accepted/edited) | BUILT | ai_feedback model |
| AI insight persistence | BUILT | ai_insight model |
| Prompt registry | PARTIAL | ai_service has prompts but no formal registry table |
| Provider strategy (Bedrock) | PARTIAL | ollama_service exists; Bedrock integration unclear |
| AI Data Model (locked schema) | BUILT | ai_insight + ai_feedback models with workspace_id |
| Safety layer (INSUFFICIENT_CONTEXT) | PARTIAL | ai_service likely handles; not formally verified |
| Output contracts (structured JSON) | PARTIAL | ai_service returns structured data; schema enforcement unclear |

## Sprint 7: MVP UI Hardening

| Requirement | Status | Notes |
|---|---|---|
| Executive Dashboard | BUILT | /dashboard/executive — risk score gauge, severity bars, SLA, trend |
| Operator/Overview Dashboard | BUILT | /dashboard — overview page |
| Findings list + detail | BUILT | /dashboard/findings |
| Compliance page | BUILT | /dashboard/compliance |
| Security Graph | BUILT | /dashboard/security-graph |
| Settings/Admin | BUILT | /dashboard/settings (7 sub-pages) |
| Team management | BUILT | /dashboard/team |
| Remediation page | BUILT | /dashboard/remediation |
| Reports center | BUILT | /dashboard/reports |
| Suppression page | BUILT | /dashboard/suppression |
| Audit log page | BUILT | /dashboard/audit |
| App shell (sidebar nav) | BUILT | sidebar-nav.tsx with 20+ nav items |
| Empty/loading/error states | PARTIAL | Most pages have loading states; error states may be inconsistent |
| Sort/search UX | PARTIAL | Some pages have filters; not all have consistent search/sort |

## Sprint 8+: Advanced Features

### CIEM (Domain C — Identity & Access Risk)
| Requirement | Status | Notes |
|---|---|---|
| IAM entity inventory | BUILT | ciem_service + /dashboard/ciem |
| Privilege escalation detection | BUILT | 5 patterns + graph edge detection |
| Cross-account trust analysis | BUILT | ciem_service._cross_account_summary |
| IAM risk weight in causal engine | BUILT | 0.20 weight |
| Toxic combinations | MISSING | Not yet implemented |
| Least-privilege recommendations | MISSING | Not yet implemented |
| IAM Access Analyzer integration | MISSING | No integration |

### Vulnerability Management (Domain D — Workload & Runtime)
| Requirement | Status | Notes |
|---|---|---|
| CVE extraction from findings | BUILT | vuln_service with regex |
| EPSS scoring | BUILT | Static EPSS dataset (30+ CVEs) |
| CISA KEV catalog | BUILT | Static KEV set (20 CVEs) |
| CVE inventory dashboard | BUILT | /dashboard/vulns |
| ECR image scanning | MISSING | No ECR-specific scanning |
| Lambda vulnerability scanning | MISSING | No Lambda-specific vuln scanning |
| AMI/gold image validation | MISSING | Not yet built |

### Cloud Detection & Response (Sprint 23)
| Requirement | Status | Notes |
|---|---|---|
| Detection rules engine | BUILT | detection_service.py (8 correlation rules) |
| Detections API | BUILT | routers/detections.py |
| MITRE ATT&CK mapping | BUILT | 8 tactics/techniques mapped |
| Detections dashboard | PARTIAL | /dashboard/detections exists but needs verification |
| Detections sidebar nav | BUILT | In sidebar |

### MSP / vCISO Features (SKU 2/3)
| Requirement | Status | Notes |
|---|---|---|
| Multi-tenant / workspace switching | PARTIAL | Workspace model exists; no multi-tenant portal UI |
| Portfolio dashboard (vCISO) | MISSING | No cross-workspace portfolio view |
| Client workspace switcher | MISSING | No fast-switch UI |
| White-label / branding | MISSING | No white-label support |
| Scorecard view (client-friendly) | MISSING | No scorecard page |
| Weekly client reports | PARTIAL | Email digest exists but not client-branded |

### Data Security (Domain E)
| Requirement | Status | Notes |
|---|---|---|
| PII/sensitive data detection | MISSING | No Macie integration |
| Shadow data detection | MISSING | Not implemented |
| Data classification | MISSING | Not implemented |

### Attack-Chain Lite (Domain F)
| Requirement | Status | Notes |
|---|---|---|
| Attack path visualization | PARTIAL | attack_path model exists; security graph has relationships |
| Relationship-aware prioritization | PARTIAL | causal engine + graph centrality weight |
| Drift detection | MISSING | Not implemented |
| Root cause v2 | MISSING | Only v1 exists |

### Prevention & Code Context (Domain G)
| Requirement | Status | Notes |
|---|---|---|
| Terraform scanning | MISSING | Not implemented |
| IaC context | MISSING | Not implemented |
| SG rule approval workflows | MISSING | Not implemented |

### Design System Components (Gold Standard)
| Requirement | Status | Notes |
|---|---|---|
| RootCauseChip | MISSING | Not a standalone component |
| TimestampLabel | MISSING | Not a standalone component |
| AIFeedbackBar | MISSING | Not a standalone component |
| CreateDrawer | MISSING | Not a standalone component |
| FrameworkScoreCard | MISSING | Compliance page exists but no dedicated component |
| ControlFamilyHeatmap | MISSING | Not implemented |

---

## Summary Scorecard

| Domain | Scope Items | Built | Partial | Missing | Completion |
|---|---|---|---|---|---|
| A: Critical Exposure & Misconfig | 12 | 10 | 1 | 1 | ~85% |
| B: Control Baseline & Compliance | 10 | 8 | 1 | 1 | ~80% |
| C: Identity & Access (CIEM) | 7 | 4 | 0 | 3 | ~57% |
| D: Workload & Runtime (Vulns) | 7 | 4 | 0 | 3 | ~57% |
| E: Data Security | 3 | 0 | 0 | 3 | 0% |
| F: Attack-Chain Lite | 4 | 0 | 2 | 2 | ~25% |
| G: Prevention & Code | 3 | 0 | 0 | 3 | 0% |
| Infrastructure/Foundation | 10 | 10 | 0 | 0 | 100% |
| AI Layer | 8 | 5 | 3 | 0 | ~81% |
| UI/Dashboard | 15 | 13 | 2 | 0 | ~93% |
| MSP/vCISO | 6 | 0 | 2 | 4 | ~17% |
| CDR/Detections | 5 | 4 | 1 | 0 | ~90% |
| **TOTAL** | **~90** | **~58** | **~12** | **~20** | **~72%** |

---

## Top Priority Gaps (Ordered by Business Impact)

1. **MSP / vCISO Portfolio Dashboard** — Best GTM entry per document; completely missing
2. **Data Security (Macie integration)** — Domain E entirely missing
3. **Attack Path Visualization** — Domain F only partial
4. **IAM Access Analyzer integration** — Key CIEM feature missing
5. **Drift Detection + Root Cause v2** — Intelligence moat gap
6. **ECR/Lambda vulnerability scanning** — Workload security gap
7. **AI Prompt Registry** — Formal registry not built
8. **Design System Components** — Reusable component library not extracted
9. **Prevention & Code Context** — Domain G entirely missing (Phase 3)
10. **White-label / Branding** — MSP revenue blocker
