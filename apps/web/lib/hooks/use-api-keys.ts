"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";
import type { ApiKey, ApiKeyCreate, ApiKeyCreatedResponse } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function useApiKeys() {
  const { data, error, isLoading, mutate } = useSWR<ApiKey[]>(
    "/api/v1/api-keys",
    apiFetcher
  );
  return { apiKeys: data ?? [], error, isLoading, mutate };
}

export async function createApiKey(req: ApiKeyCreate): Promise<ApiKeyCreatedResponse> {
  const res = await fetch(`${API}/api/v1/api-keys`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function revokeApiKey(keyId: string): Promise<void> {
  const res = await fetch(`${API}/api/v1/api-keys/${keyId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok) throw new Error(await res.text());
}
