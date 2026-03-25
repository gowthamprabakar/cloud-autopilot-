"use client";
import useSWR from "swr";
import { apiClient, apiFetcher } from "@/lib/api-client";
import type { ReportSchedule, ReportScheduleUpdate } from "@/lib/types";

export function useReportSchedule() {
  const { data, error, mutate } = useSWR<ReportSchedule>(
    "/api/v1/reports/schedule",
    apiFetcher
  );
  return {
    schedule: data,
    isLoading: !data && !error,
    mutate,
  };
}

export async function updateReportSchedule(
  update: ReportScheduleUpdate
): Promise<ReportSchedule> {
  return apiClient.put<ReportSchedule>("/api/v1/reports/schedule", update);
}

export async function sendReportNow(): Promise<{ sent: number; recipients: string[] }> {
  return apiClient.post<{ sent: number; recipients: string[] }>(
    "/api/v1/reports/send-now",
    {}
  );
}
