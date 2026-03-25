"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";

export interface WorkspaceSummary {
  workspace_id: string;
  workspace_name: string;
  risk_score: number;
  open_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  sla_compliance: Record<string, { compliance_pct: number }>;
  has_sla_breach: boolean;
  trend_delta: number;
}

export interface PortfolioSummary {
  total_workspaces: number;
  total_open_findings: number;
  total_critical: number;
  total_high: number;
  sla_breach_count: number;
  avg_risk_score: number;
  workspaces: WorkspaceSummary[];
}

export interface SLABreach {
  finding_id: string;
  workspace_id: string;
  workspace_name: string;
  title: string;
  severity: string;
  resource_arn: string;
  sla_limit_hours: number;
  age_hours: number;
  remaining_hours: number;
  is_breached: boolean;
  first_seen: string;
}

export function usePortfolioSummary() {
  const { data, error, isLoading, mutate } = useSWR<PortfolioSummary>(
    "/api/v1/portfolio/summary",
    apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { portfolio: data ?? null, isLoading, error, mutate };
}

export function useSLABreaches() {
  const { data, error, isLoading } = useSWR<SLABreach[]>(
    "/api/v1/portfolio/sla-breaches",
    apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { breaches: data ?? [], isLoading, error };
}
