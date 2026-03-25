"use client";
import useSWR from "swr";
import { apiClient, apiFetcher } from "@/lib/api-client";
import type { ScanJob, ScanTriggerResponse } from "@/lib/types";

export interface ScanStatusResponse {
  latest_job: ScanJob | null;
  is_running: boolean;
  last_sync_message: string;
}

export interface ScanHistoryResponse {
  items: ScanJob[];
  total: number;
}

/**
 * Current / most-recent scan status with is_running flag and human message.
 * Polls every 5 s while running, 60 s otherwise.
 */
export function useScanStatus() {
  const { data, error, isLoading, mutate } = useSWR<ScanStatusResponse>(
    "/api/v1/scanner/status",
    apiFetcher,
    {
      refreshInterval: (d?: ScanStatusResponse) =>
        d?.is_running ? 5_000 : 60_000,
      shouldRetryOnError: false,
    }
  );

  return {
    scanJob: data?.latest_job ?? null,
    isRunning: data?.is_running ?? false,
    message: data?.last_sync_message ?? "",
    isLoading,
    error,
    mutate,
  };
}

/**
 * Full scan history list.
 * Polls every 5 s while a scan is running, 60 s otherwise.
 */
export function useScanHistory() {
  const { isRunning } = useScanStatus();

  const { data, error, isLoading, mutate } = useSWR<ScanHistoryResponse>(
    "/api/v1/scanner/history",
    apiFetcher,
    {
      refreshInterval: isRunning ? 5_000 : 60_000,
      shouldRetryOnError: false,
    }
  );

  return { history: data?.items ?? [], total: data?.total ?? 0, isLoading, error, mutate };
}

/**
 * Trigger a scan. Pass an accountId to scope to one account.
 */
export async function triggerScan(accountId?: string): Promise<ScanTriggerResponse> {
  const url = accountId
    ? `/api/v1/scanner/trigger?aws_account_id=${accountId}`
    : `/api/v1/scanner/trigger`;
  return apiClient.post<ScanTriggerResponse>(url, {});
}
