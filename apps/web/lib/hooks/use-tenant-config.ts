"use client";
import useSWR from "swr";
import { apiFetcher, apiClient } from "@/lib/api-client";

export interface TenantConfig {
  id: string;
  display_name: string;
  logo_url: string | null;
  primary_color: string;
  secondary_color: string;
  feature_simulations: boolean;
  feature_graph_explorer: boolean;
  feature_agent_memory: boolean;
  feature_ciem: boolean;
  feature_vulns: boolean;
  feature_detections: boolean;
  max_simulations_per_month: number;
  max_agents_per_simulation: number;
  api_budget_usd: number;
  sso_provider: string | null;
}

export interface BudgetStatus {
  simulations_used: number;
  simulations_limit: number;
  cost_used: number;
  cost_limit: number;
}

export function useTenantConfig() {
  const { data, error, isLoading, mutate } = useSWR<TenantConfig>(
    "/api/v1/admin/tenants/config", apiFetcher, { revalidateOnFocus: false }
  );
  return { config: data ?? null, isLoading, error, mutate };
}

export function useBudgetStatus() {
  const { data, error, isLoading } = useSWR<BudgetStatus>(
    "/api/v1/admin/tenants/budget", apiFetcher, { revalidateOnFocus: false }
  );
  return { budget: data ?? null, isLoading, error };
}

export async function updateTenantConfig(updates: Partial<TenantConfig>) {
  return apiClient.put("/api/v1/admin/tenants/config", updates);
}
