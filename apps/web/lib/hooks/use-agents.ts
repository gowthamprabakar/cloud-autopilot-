"use client";
import useSWR from "swr";
import { apiClient, apiFetcher } from "@/lib/api-client";

// ── Types ────────────────────────────────────────────────────────────────────

export interface TriageOutput {
  suggested_severity: string;
  confidence: number;
  rationale: string;
  mitre_tactics: string[];
  fallback_used: boolean;
  original_severity: string;
}

export interface AttackPathOutput {
  blast_radius_count: number;
  choke_points: string[];
  path_summary: string;
  attack_chain: string[];
}

export interface AgentResult<T> {
  id: string;
  workspace_id: string;
  finding_id: string;
  agent_name: string;
  status: "completed" | "failed";
  model_used: string;
  output: T;
  error_message: string | null;
  latency_ms: number | null;
  created_at: string;
  updated_at: string;
}

export interface AgentAuditLog {
  id: string;
  agent_name: string;
  triggered_by: string;
  model_used: string;
  output_summary: string | null;
  latency_ms: number | null;
  created_at: string;
}

// ── Triage hooks ─────────────────────────────────────────────────────────────

/**
 * Fetch the latest triage result for a finding.
 * Returns null if not yet triaged.
 */
export function useTriageResult(findingId: string) {
  const { data, error, isLoading, mutate } = useSWR<AgentResult<TriageOutput>>(
    findingId ? `/api/v1/findings/${findingId}/triage` : null,
    apiFetcher,
    { shouldRetryOnError: false, revalidateOnFocus: false }
  );
  return {
    result: data ?? null,
    isLoading,
    error,
    mutate,
  };
}

/**
 * Trigger a new triage analysis for a finding.
 */
export async function triggerTriage(findingId: string): Promise<AgentResult<TriageOutput>> {
  return apiClient.post<AgentResult<TriageOutput>>(
    `/api/v1/findings/${findingId}/triage`,
    {}
  );
}

// ── Attack Path hooks ─────────────────────────────────────────────────────────

/**
 * Fetch the latest attack path result for a finding.
 * Returns null if not yet analyzed.
 */
export function useAttackPathResult(findingId: string) {
  const { data, error, isLoading, mutate } = useSWR<AgentResult<AttackPathOutput>>(
    findingId ? `/api/v1/findings/${findingId}/attack-path` : null,
    apiFetcher,
    { shouldRetryOnError: false, revalidateOnFocus: false }
  );
  return {
    result: data ?? null,
    isLoading,
    error,
    mutate,
  };
}

/**
 * Trigger a new attack path analysis for a finding.
 */
export async function triggerAttackPath(findingId: string): Promise<AgentResult<AttackPathOutput>> {
  return apiClient.post<AgentResult<AttackPathOutput>>(
    `/api/v1/findings/${findingId}/attack-path`,
    {}
  );
}

// ── Root Cause hooks ──────────────────────────────────────────────────────────

export interface RootCauseOutput {
  root_cause: string;
  contributing_factors: string[];
  misconfiguration_type: string;
  affected_blast_radius: number;
  remediation_priority: "immediate" | "high" | "medium" | "low";
  fallback_used: boolean;
}

export function useRootCauseResult(findingId: string) {
  const { data, error, isLoading, mutate } = useSWR<AgentResult<RootCauseOutput>>(
    findingId ? `/api/v1/findings/${findingId}/root-cause` : null,
    apiFetcher,
    { shouldRetryOnError: false, revalidateOnFocus: false }
  );
  return { result: data ?? null, isLoading, error, mutate };
}

export async function triggerRootCause(findingId: string): Promise<AgentResult<RootCauseOutput>> {
  return apiClient.post<AgentResult<RootCauseOutput>>(
    `/api/v1/findings/${findingId}/root-cause`, {}
  );
}

// ── Remediation Plan hooks ────────────────────────────────────────────────────

export interface RemediationStep {
  step: number;
  action: string;
  command: string;
  iac_type: "terraform" | "cli" | "console";
}

export interface RemediationPlanOutput {
  steps: RemediationStep[];
  estimated_effort: "minutes" | "hours" | "days";
  auto_remediatable: boolean;
  fallback_used: boolean;
}

export function useRemediationPlan(findingId: string) {
  const { data, error, isLoading, mutate } = useSWR<AgentResult<RemediationPlanOutput>>(
    findingId ? `/api/v1/findings/${findingId}/remediation-plan` : null,
    apiFetcher,
    { shouldRetryOnError: false, revalidateOnFocus: false }
  );
  return { result: data ?? null, isLoading, error, mutate };
}

export async function triggerRemediationPlan(findingId: string): Promise<AgentResult<RemediationPlanOutput>> {
  return apiClient.post<AgentResult<RemediationPlanOutput>>(
    `/api/v1/findings/${findingId}/remediation-plan`, {}
  );
}

// ── Notification hooks ────────────────────────────────────────────────────────

export interface NotificationOutput {
  notification_sent: boolean;
  channel: "in_app";
  severity: string;
  message: string;
}

export function useNotificationResult(findingId: string) {
  const { data, error, isLoading, mutate } = useSWR<AgentResult<NotificationOutput>>(
    findingId ? `/api/v1/findings/${findingId}/notify` : null,
    apiFetcher,
    { shouldRetryOnError: false, revalidateOnFocus: false }
  );
  return { result: data ?? null, isLoading, error, mutate };
}

export async function triggerNotification(findingId: string): Promise<AgentResult<NotificationOutput>> {
  return apiClient.post<AgentResult<NotificationOutput>>(
    `/api/v1/findings/${findingId}/notify`, {}
  );
}

// ── Audit log hook ────────────────────────────────────────────────────────────

/**
 * Fetch all agent audit logs for a finding.
 */
export function useAgentAuditLogs(findingId: string) {
  const { data, error, isLoading } = useSWR<AgentAuditLog[]>(
    findingId ? `/api/v1/findings/${findingId}/agent-audit-logs` : null,
    apiFetcher,
    { shouldRetryOnError: false, revalidateOnFocus: false }
  );
  return {
    logs: data ?? [],
    isLoading,
    error,
  };
}
