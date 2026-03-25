import useSWR from "swr";
import { swrFetcher, apiClient } from "@/lib/api-client";
import type { WorkspaceResponse, UpdateWorkspaceRequest } from "@/lib/types";

export function useWorkspace() {
  const { data, error, isLoading, mutate } = useSWR<WorkspaceResponse>(
    "/api/v1/workspaces/current",
    swrFetcher
  );
  return { workspace: data ?? null, isLoading, error, mutate };
}

export async function updateWorkspace(data: UpdateWorkspaceRequest): Promise<WorkspaceResponse> {
  return apiClient.patch<WorkspaceResponse>("/api/v1/workspaces/current", data);
}
