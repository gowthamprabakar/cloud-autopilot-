"use client";
import useSWR from "swr";
import { apiFetcher } from "@/lib/api-client";
import type { WorkspaceSettings, WorkspaceSettingsUpdate } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function useWorkspaceSettings() {
  const { data, error, isLoading, mutate } = useSWR<WorkspaceSettings>(
    "/api/v1/workspace/settings",
    apiFetcher
  );
  return { settings: data ?? null, error, isLoading, mutate };
}

export async function updateWorkspaceSettings(
  updates: WorkspaceSettingsUpdate
): Promise<WorkspaceSettings> {
  const res = await fetch(`${API}/api/v1/workspace/settings`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<WorkspaceSettings>;
}
