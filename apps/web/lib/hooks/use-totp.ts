"use client";
import useSWR from "swr";
import { apiClient, apiFetcher } from "@/lib/api-client";
import type { TotpStatus, TotpSetupResponse } from "@/lib/types";

export function useTotpStatus() {
  const { data, error, mutate } = useSWR<TotpStatus>(
    "/api/v1/auth/2fa/status",
    apiFetcher
  );
  return {
    status: data,
    isLoading: !data && !error,
    mutate,
  };
}

export async function setupTotp(): Promise<TotpSetupResponse> {
  return apiClient.post<TotpSetupResponse>("/api/v1/auth/2fa/setup", {});
}

export async function verifyTotp(code: string): Promise<void> {
  await apiClient.post<void>("/api/v1/auth/2fa/verify", { code });
}

export async function disableTotp(code: string): Promise<void> {
  await apiClient.post<void>("/api/v1/auth/2fa/disable", { code });
}
