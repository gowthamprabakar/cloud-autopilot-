"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";

export interface AuditEntry {
  id: string;
  event_type: string;
  actor: string;
  action: string;
  details: Record<string, any> | null;
  created_at: string;
}

export interface DomainTrend {
  domain: string;
  run_count: number;
  avg_confidence: number;
  best_confidence: number;
  worst_confidence: number;
  avg_cost: number;
  total_cost: number;
}

export interface CostAnalysis {
  total_cost: number;
  daily_costs: Array<{ date: string; cost: number; runs: number }>;
  by_domain: Record<string, number>;
  budget_used_pct: number;
}

export function useSimulationAuditTrail(runId: string) {
  const { data, error, isLoading } = useSWR<AuditEntry[]>(
    runId ? `/api/v1/audit-trail/${runId}` : null, apiFetcher, { revalidateOnFocus: false }
  );
  return { entries: data ?? [], isLoading, error };
}

export function useDomainTrends() {
  const { data, error, isLoading } = useSWR<{ trends: DomainTrend[] }>(
    "/api/v1/session-history/trends", apiFetcher, { revalidateOnFocus: false }
  );
  return { trends: data?.trends ?? [], isLoading, error };
}

export function useCostAnalysis(days: number = 30) {
  const { data, error, isLoading } = useSWR<CostAnalysis>(
    `/api/v1/session-history/costs?days=${days}`, apiFetcher, { revalidateOnFocus: false }
  );
  return { costs: data ?? null, isLoading, error };
}
