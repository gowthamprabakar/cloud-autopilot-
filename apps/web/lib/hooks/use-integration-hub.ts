"use client";
import useSWR from "swr";
import { apiFetcher, apiClient } from "@/lib/api-client";

export interface Integration {
  id: string;
  integration_type: "slack" | "jira" | "pagerduty" | "siem" | "github" | "gitlab";
  name: string;
  is_enabled: boolean;
  last_sync_at: string | null;
  last_error: string | null;
  created_at: string;
}

export function useIntegrations() {
  const { data, error, isLoading, mutate } = useSWR<Integration[]>(
    "/api/v1/integration-hub", apiFetcher, { revalidateOnFocus: false }
  );
  return { integrations: data ?? [], isLoading, error, mutate };
}

export async function createIntegration(type: string, name: string, config: Record<string, any>) {
  return apiClient.post("/api/v1/integration-hub", { integration_type: type, name, config });
}

export async function deleteIntegration(id: string) {
  return apiClient.delete(`/api/v1/integration-hub/${id}`);
}

export async function testIntegration(id: string) {
  return apiClient.post(`/api/v1/integration-hub/${id}/test`);
}
