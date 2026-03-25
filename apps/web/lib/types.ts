/**
 * Shared TypeScript types — aligned to backend API contracts.
 * Phase 1 will expand significantly.
 *
 * Rules:
 * - Never derive severity, risk_score, or compliance_state in the frontend.
 * - All such values come from backend API responses and are rendered as-is.
 */

// ── Enums (mirror backend StrEnum values) ──────────────────────────────────

export type Severity = "critical" | "high" | "medium" | "low" | "info";

export type FindingStatus =
  | "open"
  | "in_progress"
  | "resolved"
  | "accepted"
  | "suppressed";

export type JobStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

// ── Health ─────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: "ok" | string;
  service: string;
}

// ── Auth (Phase 1) ─────────────────────────────────────────────────────────

export type UserRole =
  | "super_admin"
  | "admin"
  | "analyst"
  | "viewer"
  | "msp_partner";

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface UserProfileResponse {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  tenant_id: string;
  workspace_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Tenant / Workspace (Phase 1) ───────────────────────────────────────────

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  created_at: string;
}

export interface Workspace {
  id: string;
  tenant_id: string;
  name: string;
  slug: string;
  created_at: string;
}

// ── AWS Account (Phase 1) ──────────────────────────────────────────────────

export interface AwsAccount {
  id: string;
  workspace_id: string;
  account_id: string;
  account_alias: string | null;
  role_arn: string;
  status: "pending" | "active" | "error" | "disabled";
  enabled_regions: string[];
  last_synced_at: string | null;
  created_at: string;
}

// ── Findings ───────────────────────────────────────────────────────────────

export interface CanonicalFinding {
  id: string;
  workspace_id: string;
  aws_account_id: string;
  fingerprint: string;
  primary_source: "security_hub" | "guard_duty" | "inspector" | "config" | "iam_access_analyzer";
  severity: Severity;
  status: FindingStatus;
  risk_score: number | null;
  title: string;
  description: string | null;
  remediation: string | null;
  resource_arn: string | null;
  resource_type: string | null;
  region: string | null;
  compliance_frameworks: string[];
  tags: Record<string, string>;
  first_seen_at: string | null;
  last_seen_at: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface FindingListResponse {
  items: CanonicalFinding[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface FindingStats {
  by_severity: Record<Severity, number>;
  by_status: Record<FindingStatus, number>;
  total: number;
}

// ── Job Runs ───────────────────────────────────────────────────────────────

export interface JobRun {
  id: string;
  aws_account_id: string | null;
  workspace_id: string;
  job_type: string;
  status: JobStatus;
  progress_detail: Record<string, unknown>;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

// ── Compliance ─────────────────────────────────────────────────────────────

export interface ComplianceFrameworkSummary {
  framework_id: string;
  display_name: string;
  total_controls: number;
  passing: number;
  failing: number;
  coverage_pct: number;
}

export interface ComplianceStats {
  frameworks: ComplianceFrameworkSummary[];
  last_updated: string | null;
}

// ── AI Safe Layer ──────────────────────────────────────────────────────────
// AI is AUGMENTATION ONLY — severity, risk_score, compliance state are
// never derived from or set by AI responses.

export type AiGenerationStatus = "pending" | "completed" | "failed";
export type AiFeedbackVerdict = "accepted" | "edited" | "rejected";

export interface AiInsight {
  id: string;
  workspace_id: string;
  finding_id: string;
  prompt_template_id: string;
  input_context_hash: string;
  model_id: string;
  generation_status: AiGenerationStatus;
  summary: string | null;
  suggested_actions: string[];
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface GenerateInsightRequest {
  prompt_template_id: string;
}

export interface AiFeedbackRequest {
  verdict: AiFeedbackVerdict;
  edited_text?: string | null;
}

export interface AiFeedbackResponse {
  id: string;
  insight_id: string;
  user_id: string | null;
  verdict: AiFeedbackVerdict;
  edited_text: string | null;
  created_at: string;
}

export interface PromptTemplate {
  id: string;
  description: string;
}

// ── Users (Sprint 7) ───────────────────────────────────────────────────────
export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  tenant_id: string;
  workspace_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserListResponse {
  items: UserResponse[];
  total: number;
}

export interface InviteUserRequest {
  email: string;
  full_name: string;
  role: UserRole;
  password: string;
}

export interface UpdateUserRoleRequest {
  role: UserRole;
}

// ── Workspace (Sprint 7) ────────────────────────────────────────────────────
export interface WorkspaceResponse {
  id: string;
  tenant_id: string;
  name: string;
  slug: string;
  status: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UpdateWorkspaceRequest {
  name?: string;
}

// ── Audit Log ─────────────────────────────────────────────────────────────

export interface AuditLog {
  id: string;
  workspace_id: string;
  actor_user_id: string | null;
  actor_email: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  detail: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditLogListResponse {
  items: AuditLog[];
  total: number;
  page: number;
  pages: number;
}

// ── Notifications ─────────────────────────────────────────────────────────

export interface Notification {
  id: string;
  workspace_id: string;
  user_id: string | null;
  type: string;
  title: string;
  body: string;
  is_read: boolean;
  metadata_: Record<string, unknown> | null;
  link_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface NotificationListResponse {
  items: Notification[];
  unread_count: number;
}

// ── Suppression Rules ─────────────────────────────────────────────────────

export interface SuppressionRule {
  id: string;
  workspace_id: string;
  created_by_user_id: string | null;
  name: string;
  reason: string;
  match_title_contains: string | null;
  match_resource_type: string | null;
  match_resource_arn_contains: string | null;
  match_severity: string | null;
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SuppressionRuleCreate {
  name: string;
  reason: string;
  match_title_contains?: string;
  match_resource_type?: string;
  match_resource_arn_contains?: string;
  match_severity?: string;
  expires_at?: string;
}

// ── Bulk Update ────────────────────────────────────────────────────────────

export interface BulkFindingUpdateRequest {
  finding_ids: string[];
  status: FindingStatus;
}

export interface BulkFindingUpdateResponse {
  updated: number;
  failed: number;
  errors: string[];
}

// ── API Keys ──────────────────────────────────────────────────────────────────
export interface ApiKey {
  id: string
  workspace_id: string
  name: string
  key_prefix: string        // e.g. "sk-abc123" — safe to display
  last_used_at: string | null
  expires_at: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ApiKeyCreate {
  name: string
  expires_at?: string | null
}

export interface ApiKeyCreatedResponse extends ApiKey {
  raw_key: string           // shown ONCE — display in a modal with copy button
}

// ── Webhooks ─────────────────────────────────────────────────────────────────
export interface WebhookDestination {
  id: string
  workspace_id: string
  name: string
  url: string
  events: string[]
  is_active: boolean
  created_at: string
  updated_at: string
  // secret is NOT in list/get response — only in WebhookCreatedResponse
}

export interface WebhookCreatedResponse extends WebhookDestination {
  secret: string            // shown ONCE — display with copy button
}

export interface WebhookCreate {
  name: string
  url: string
  events: string[]
}

// ── Finding Comments ──────────────────────────────────────────────────────────
export interface FindingComment {
  id: string
  finding_id: string
  user_id: string | null
  author_email: string | null
  body: string
  created_at: string
  updated_at: string
}

// ── Finding Assignments ───────────────────────────────────────────────────────
export interface FindingAssignment {
  id: string
  finding_id: string
  workspace_id: string
  assignee_user_id: string
  assignee_email: string | null
  assigned_by_user_id: string | null
  assigned_by_email: string | null
  due_date: string | null
  is_active: boolean
  note: string | null
  created_at: string
  updated_at: string
}

export interface AssignFindingRequest {
  assignee_user_id: string
  due_date?: string | null
  note?: string | null
}

// ── SLA ──────────────────────────────────────────────────────────────────────
export interface SlaFinding {
  id: string
  title: string
  severity: string
  resource_type: string | null
  resource_arn: string | null
  first_seen_at: string | null
  risk_score: number | null
  sla_status: "on_track" | "at_risk" | "breached" | "resolved"
  sla_due_date: string | null
  sla_days_remaining: number | null
  sla_days_total: number | null
}

export interface SlaSummary {
  total_open: number
  breached: number
  at_risk: number
  on_track: number
}

// ── Workspace Settings ────────────────────────────────────────────────────────
export interface WorkspaceSettings {
  id: string
  workspace_id: string
  sla_days_critical: number
  sla_days_high: number
  sla_days_medium: number
  sla_days_low: number
  sla_days_info: number
  finding_auto_close_days: number
  created_at: string
  updated_at: string
}

export interface WorkspaceSettingsUpdate {
  sla_days_critical?: number
  sla_days_high?: number
  sla_days_medium?: number
  sla_days_low?: number
  sla_days_info?: number
  finding_auto_close_days?: number
}

// ── Onboarding ────────────────────────────────────────────────────────────────
export interface OnboardingProgress {
  workspace_id: string
  step_workspace_created: boolean
  step_aws_account_connected: boolean
  step_first_sync_complete: boolean
  step_team_member_invited: boolean
  step_sla_configured: boolean
  all_complete: boolean
  completion_percentage: number
  completed_at: string | null
  dismissed: boolean
}

// ── Jira ──────────────────────────────────────────────────────────────────────
export interface JiraTicket {
  id: string
  finding_id: string
  workspace_id: string
  jira_key: string
  jira_url: string
  created_at: string
}

export interface JiraTicketCreate {
  finding_id: string
}

export interface JiraConnectionTest {
  ok: boolean
  message: string
}

// ─── Security Graph ───────────────────────────────────────────────────────────

export type GraphNodeType =
  | "s3_bucket" | "iam_role" | "lambda" | "rds" | "ec2"
  | "vpc" | "security_group" | "internet" | "subnet"
  | "kms_key" | "secrets_manager" | "cloudtrail";

export interface SecurityGraphNode {
  id: string;
  workspace_id: string;
  node_type: GraphNodeType;
  resource_arn: string | null;
  resource_name: string | null;
  region: string | null;
  metadata: Record<string, unknown>;
  finding_ids: string[];
  risk_score: number | null;
  is_internet_facing: boolean;
  is_sensitive_data: boolean;
}

export interface SecurityGraphEdge {
  id: string;
  workspace_id: string;
  source_node_id: string;
  target_node_id: string;
  edge_type: string;
  is_attack_path: boolean;
  risk_contribution: number | null;
  metadata: Record<string, unknown>;
}

export interface AttackPath {
  id: string;
  name: string;
  description: string | null;
  severity: string;
  node_path: string[];
  edge_path: string[];
  toxic_combo_tags: string[];
  blast_radius: number;
  entry_description: string | null;
  target_description: string | null;
  is_active: boolean;
  related_finding_ids: string[];
}

export interface SecurityGraphStats {
  total_nodes: number;
  attack_path_nodes: number;
  internet_facing: number;
  sensitive_data_nodes: number;
}

export interface SecurityGraphResponse {
  nodes: SecurityGraphNode[];
  edges: SecurityGraphEdge[];
  attack_paths: AttackPath[];
  stats: SecurityGraphStats;
}

// ─── Finding Intelligence (RAG system) ────────────────────────────────────────

export type RAGLevel = "RED" | "AMBER" | "GREEN";

export interface PrioritizedAction {
  title: string;
  description: string;
  effort: "LOW" | "MEDIUM" | "HIGH";
  impact: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  cli_command: string | null;
  console_url: string | null;
  rag_color: RAGLevel;
}

export interface CausalFactor {
  name: string;
  score: number;
  evidence: string[];
  contributing_nodes: string[];
  weight: number;
}

export interface ToxicCombo {
  name: string;
  description: string;
  factors_involved: string[];
  score_boost: number;
  // legacy field aliases
  tags?: string[];
  severity_boost?: number;
}

export interface CausalAnalysis {
  composite_score: number;
  primary_root_cause: string;
  secondary_causes: string[];
  causal_chain: string[];
  factors: CausalFactor[];
  toxic_combinations: ToxicCombo[];
  blast_radius_count: number;
  confidence: number;
}

export interface RAGScore {
  level: RAGLevel;
  composite_score: number;
  primary_reason: string;
  sla_days: number;
  escalation_required: boolean;
  stakeholders: string[];
  immediate_actions: PrioritizedAction[];
  sprint_actions: PrioritizedAction[];
  quarterly_actions: PrioritizedAction[];
}

export interface FindingIntelligence {
  id: string;
  finding_id: string;
  // Descriptive
  what_is_it: string | null;
  current_state: string | null;
  expected_state: string | null;
  business_impact: string | null;
  attack_scenario: string | null;
  // Causal
  composite_score: number | null;
  primary_root_cause: string | null;
  causal_factors: CausalFactor[];
  causal_chain: string[];
  toxic_combinations: ToxicCombo[];
  blast_radius_count: number | null;
  confidence: number | null;
  // RAG
  rag_level: RAGLevel | null;
  rag_composite_score: number | null;
  rag_primary_reason: string | null;
  sla_days: number | null;
  escalation_required: boolean;
  stakeholders: string[];
  immediate_actions: PrioritizedAction[];
  sprint_actions: PrioritizedAction[];
  quarterly_actions: PrioritizedAction[];
  // Meta
  ollama_model: string | null;
  fallback_used: boolean;
  generation_status: "pending" | "completed" | "failed";
}

export interface WorkspaceIntelligenceSummary {
  rag_counts: { RED: number; AMBER: number; GREEN: number };
  total_analyzed: number;
  top_red_findings: Array<{ finding_id: string; title: string; rag_level: string; composite_score: number; sla_days: number }>;
}

export interface IntelligenceHealth {
  ollama_available: boolean;
  models: string[];
  model_in_use: string | null;
}

// ── Reports ────────────────────────────────────────────────────────────────

// ── Scanner (Sprint 17) ───────────────────────────────────────────────────────

export type ScanStatus = 'running' | 'completed' | 'failed' | 'partial'
export type ScanTrigger = 'manual' | 'scheduler' | 'api'

export interface ScanJob {
  id: string
  workspace_id: string
  aws_account_id: string | null
  status: ScanStatus
  triggered_by: ScanTrigger
  started_at: string
  completed_at: string | null
  findings_added: number
  findings_updated: number
  findings_total: number
  sources_scanned: string[]
  sources_failed: string[]
  error_message: string | null
  duration_seconds: number | null
  created_at: string
}

export interface ScanTriggerResponse {
  job_id: string
  status: string
  message: string
}

// ── 2FA / TOTP (Sprint 14) ────────────────────────────────────────────────────
export interface TotpSetupResponse {
  secret: string
  otpauth_uri: string
  backup_codes: string[]
}

export interface TotpStatus {
  enabled: boolean
  pending: boolean
}

// ── Report Schedules (Sprint 14) ──────────────────────────────────────────────
export interface ReportSchedule {
  id: string
  workspace_id: string
  enabled: boolean
  frequency: 'weekly' | 'monthly'
  day_of_week: number
  recipients: string[]
  last_sent_at: string | null
}

export interface ReportScheduleUpdate {
  enabled?: boolean
  frequency?: 'weekly' | 'monthly'
  day_of_week?: number
  recipients?: string[]
}

export interface ExecutiveSummaryResponse {
  generated_at: string;
  workspace_id: string;
  period_days: number;
  total_findings: number;
  open_findings: number;
  critical_open: number;
  high_open: number;
  new_last_7_days: number;
  resolved_last_7_days: number;
  avg_risk_score: number | null;
  mttr_days: number | null;
  top_findings: Array<{
    id: string;
    title: string;
    severity: Severity;
    risk_score: number | null;
    resource_type: string | null;
    resource_arn: string | null;
  }>;
  accounts: Array<{
    account_id: string;
    account_alias: string | null;
    total_findings: number;
    open_findings: number;
    critical_findings: number;
  }>;
  compliance: Array<{
    framework_id: string;
    total: number;
    passing: number;
    coverage_pct: number;
  }>;
}
