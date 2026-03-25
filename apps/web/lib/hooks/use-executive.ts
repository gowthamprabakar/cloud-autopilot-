"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface SeverityBucket {
  open: number;
  total: number;
}

export interface AccountRisk {
  id: string;
  account_id: string;
  alias: string;
  risk_score: number;
  open_findings: number;
  status: string;
}

export interface TopFinding {
  id: string;
  title: string;
  severity: string;
  risk_score: number;
  resource_type: string | null;
  account_id: string;
}

export interface ExecutiveSummary {
  risk_score: number;
  previous_score: number;
  trend: "improving" | "worsening" | "stable";
  trend_delta: number;
  total_findings: number;
  open_findings: number;
  by_severity: {
    critical: SeverityBucket;
    high: SeverityBucket;
    medium: SeverityBucket;
    low: SeverityBucket;
    info: SeverityBucket;
  };
  sla_compliance: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  accounts: AccountRisk[];
  top_findings: TopFinding[];
  score_formula: string;
}

export interface TrendDataPoint {
  date: string;
  open: number;
  new: number;
}

export interface ExecutiveTrend {
  days: number;
  data_points: TrendDataPoint[];
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useExecutiveSummary() {
  const { data, error, isLoading, mutate } = useSWR<ExecutiveSummary>(
    "/api/v1/executive/summary",
    apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { summary: data ?? null, isLoading, error, mutate };
}

export function useExecutiveTrend(days: 30 | 60 | 90 = 30) {
  const { data, error, isLoading } = useSWR<ExecutiveTrend>(
    `/api/v1/executive/trend?days=${days}`,
    apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { trend: data ?? null, isLoading, error };
}
