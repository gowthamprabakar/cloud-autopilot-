"use client";
import useSWR from "swr";
import { apiClient, authHeaders, ApiError } from "@/lib/api-client";
import type { UserProfileResponse } from "@/lib/types";

export function useAuth() {
  const { data: user, error, isLoading, mutate } = useSWR<UserProfileResponse>(
    "/api/v1/auth/me",
    (url: string) => apiClient.get<UserProfileResponse>(url),
    { shouldRetryOnError: false }
  );

  const isAuthenticated = !!user && !error;

  async function logout() {
    try {
      await apiClient.post("/api/v1/auth/logout", {});
    } catch {}
    // Clear any residual localStorage token (migration from Phase 1)
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
    }
    await mutate(undefined, false);
    window.location.href = "/login";
  }

  return { user, isAuthenticated, isLoading, error, logout, mutate };
}
