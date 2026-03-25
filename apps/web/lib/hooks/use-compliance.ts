"use client";
import useSWR from "swr";
import { apiClient, authHeaders } from "@/lib/api-client";
import type { ComplianceStats } from "@/lib/types";

export function useComplianceStats() {
  const { data, error, isLoading } = useSWR<ComplianceStats>(
    "/api/v1/compliance/stats",
    (url: string) => apiClient.get<ComplianceStats>(url, { headers: authHeaders() }),
    { shouldRetryOnError: false }
  );

  return { stats: data, isLoading, error };
}
