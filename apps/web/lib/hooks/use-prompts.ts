"use client";
import useSWR from "swr";
import { apiFetcher, apiClient } from "@/lib/api-client";

export interface PromptTemplate {
  id: string;
  workspace_id: string | null;
  name: string;
  version: number;
  template: string;
  model_id: string;
  category: string;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export function usePrompts() {
  const { data, error, isLoading, mutate } = useSWR<PromptTemplate[]>(
    "/api/v1/prompts",
    apiFetcher,
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
  return { prompts: data ?? [], isLoading, error, mutate };
}

export async function seedPrompts(): Promise<{ seeded: number }> {
  return apiClient.post<{ seeded: number }>("/api/v1/prompts/seed", {});
}

export async function createPrompt(data: {
  name: string;
  template: string;
  category: string;
  model_id?: string;
}): Promise<PromptTemplate> {
  return apiClient.post<PromptTemplate>("/api/v1/prompts", data);
}

export async function updatePrompt(
  promptId: string,
  data: Partial<{
    template: string;
    model_id: string;
    category: string;
    is_active: boolean;
  }>
): Promise<PromptTemplate> {
  return apiClient.patch<PromptTemplate>(`/api/v1/prompts/${promptId}`, data);
}
