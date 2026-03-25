"use client";
import useSWR from "swr";
import { apiClient, authHeaders } from "@/lib/api-client";
import type { CanonicalFinding, FindingListResponse, FindingStats } from "@/lib/types";

export function useFindings(params?: {
  page?: number;
  page_size?: number;
  severity?: string;
  status?: string;
  aws_account_id?: string;
}) {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.page_size) query.set("page_size", String(params.page_size));
  if (params?.severity) query.set("severity", params.severity);
  if (params?.status) query.set("status", params.status);
  if (params?.aws_account_id) query.set("aws_account_id", params.aws_account_id);

  const qs = query.toString();
  const key = `/api/v1/findings${qs ? `?${qs}` : ""}`;

  const { data, error, isLoading, mutate } = useSWR<FindingListResponse>(
    key,
    (url: string) => apiClient.get<FindingListResponse>(url, { headers: authHeaders() }),
    { shouldRetryOnError: false }
  );

  return {
    findings: data?.items,
    total: data?.total,
    pages: data?.pages,
    page: data?.page,
    isLoading,
    error,
    mutate,
  };
}

export function useFinding(id: string | null) {
  const { data, error, isLoading, mutate } = useSWR<CanonicalFinding>(
    id ? `/api/v1/findings/${id}` : null,
    (url: string) => apiClient.get<CanonicalFinding>(url, { headers: authHeaders() }),
    { shouldRetryOnError: false }
  );

  return { finding: data, isLoading, error, mutate };
}

export function useFindingStats() {
  const { data, error, isLoading } = useSWR<FindingStats>(
    "/api/v1/findings/stats",
    (url: string) => apiClient.get<FindingStats>(url, { headers: authHeaders() }),
    { shouldRetryOnError: false }
  );

  return { stats: data, isLoading, error };
}
