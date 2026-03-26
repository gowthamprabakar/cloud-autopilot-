"use client";
import { apiClient } from "@/lib/api-client";

export async function exportJSON(runId: string) {
  const res = await apiClient.get(`/api/v1/exports/${runId}/json`);
  return res;
}

export async function exportMarkdown(runId: string): Promise<string> {
  const res = await apiClient.get<string>(`/api/v1/exports/${runId}/markdown`);
  return res;
}

export async function exportExecutive(runId: string): Promise<string> {
  const res = await apiClient.get<string>(`/api/v1/exports/${runId}/executive`);
  return res;
}

export async function exportIaC(runId: string) {
  const res = await apiClient.get(`/api/v1/exports/${runId}/iac`);
  return res;
}
