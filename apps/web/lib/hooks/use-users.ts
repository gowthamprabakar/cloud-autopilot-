import useSWR from "swr";
import { swrFetcher, apiClient } from "@/lib/api-client";
import type { UserListResponse, UserResponse, InviteUserRequest } from "@/lib/types";

export function useUsers() {
  const { data, error, isLoading, mutate } = useSWR<UserListResponse>(
    "/api/v1/users",
    swrFetcher
  );
  return { users: data?.items ?? [], total: data?.total ?? 0, isLoading, error, mutate };
}

export async function inviteUser(data: InviteUserRequest): Promise<UserResponse> {
  return apiClient.post<UserResponse>("/api/v1/users/invite", data);
}

export async function updateUserRole(userId: string, role: string): Promise<UserResponse> {
  return apiClient.patch<UserResponse>(`/api/v1/users/${userId}/role`, { role });
}

export async function deactivateUser(userId: string): Promise<void> {
  return apiClient.delete(`/api/v1/users/${userId}`);
}
