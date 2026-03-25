"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";
import type { SlaFinding, SlaSummary } from "@/lib/types";

export function useSlaFindings(statusFilter?: string) {
  const params = statusFilter ? `?status=${statusFilter}` : "";
  const { data, error, isLoading, mutate } = useSWR<SlaFinding[]>(
    `/api/v1/sla${params}`,
    apiFetcher
  );
  return { findings: data ?? [], error, isLoading, mutate };
}

export function useSlaSummary() {
  const { data, error, isLoading } = useSWR<SlaSummary>(
    "/api/v1/sla/summary",
    apiFetcher
  );
  return {
    summary: data ?? { total_open: 0, breached: 0, at_risk: 0, on_track: 0 },
    error,
    isLoading,
  };
}
