"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";
import type { SuppressionRule, SuppressionRuleCreate } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function useSuppressionRules() {
  const { data, error, isLoading, mutate } = useSWR<SuppressionRule[]>(
    "/api/v1/suppression-rules",
    apiFetcher
  );
  return { rules: data ?? [], error, isLoading, mutate };
}

export async function createSuppressionRule(data: SuppressionRuleCreate): Promise<SuppressionRule> {
  const res = await fetch(`${API}/api/v1/suppression-rules`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? "Failed to create rule");
  return res.json();
}

export async function deleteSuppressionRule(ruleId: string): Promise<void> {
  const res = await fetch(`${API}/api/v1/suppression-rules/${ruleId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to delete rule");
}

export async function applySuppressionRules(): Promise<{ suppressed: number }> {
  const res = await fetch(`${API}/api/v1/suppression-rules/apply`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to apply rules");
  return res.json();
}

export async function bulkUpdateFindings(
  findingIds: string[],
  status: string
): Promise<{ updated: number; failed: number; errors: string[] }> {
  const res = await fetch(`${API}/api/v1/findings/bulk`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ finding_ids: findingIds, status }),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? "Bulk update failed");
  return res.json();
}
