"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";
import type { AuditLogListResponse } from "@/lib/types";

export function useAuditLog(page = 1, pageSize = 50) {
  const { data, error, isLoading } = useSWR<AuditLogListResponse>(
    `/api/v1/audit-log?page=${page}&page_size=${pageSize}`,
    apiFetcher,
    { revalidateOnFocus: false }
  );
  return { data, error, isLoading };
}
