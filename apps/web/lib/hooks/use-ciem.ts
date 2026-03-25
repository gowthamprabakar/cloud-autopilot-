"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface CIEMSummary {
  total_entities: number;
  roles: number;
  users: number;
  admin_entities: number;
  internet_facing_roles: number;
  no_mfa_count: number;
  escalation_paths_count: number;
  entities_with_escalation: number;
  critical_paths: number;
  cross_account_trusts: number;
  risk_breakdown: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
}

export interface CIEMEntity {
  id: string;
  name: string;
  type: "iam_role" | "iam_user" | "iam_group" | "iam_policy";
  resource_arn: string | null;
  region: string | null;
  risk_score: number | null;
  is_internet_facing: boolean;
  is_sensitive_data: boolean;
  permission_scope: "admin" | "write" | "read" | "limited" | "unknown";
  has_mfa: boolean | null;
  cross_account: boolean;
  policies: string[];
  has_escalation: boolean;
  escalation_risk: "critical" | "high" | "medium" | "low";
  escalation_patterns: string[];
  open_findings: number;
}

export interface EscalationPath {
  id: string;
  type: "graph_edge" | "finding";
  pattern: string;
  source: string;
  source_type: string;
  target: string;
  target_type: string;
  severity: string;
  is_attack_path: boolean;
  risk_contribution: number | null;
  finding_title?: string;
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useCIEMSummary() {
  const { data, error, isLoading, mutate } = useSWR<CIEMSummary>(
    "/api/v1/ciem/summary",
    apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { summary: data ?? null, isLoading, error, mutate };
}

export function useCIEMEntities() {
  const { data, error, isLoading } = useSWR<CIEMEntity[]>(
    "/api/v1/ciem/entities",
    apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { entities: data ?? [], isLoading, error };
}

export function useEscalationPaths() {
  const { data, error, isLoading } = useSWR<EscalationPath[]>(
    "/api/v1/ciem/escalation-paths",
    apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { paths: data ?? [], isLoading, error };
}
