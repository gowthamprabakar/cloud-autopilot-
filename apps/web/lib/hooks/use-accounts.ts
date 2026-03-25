"use client";
import useSWR from "swr";
import { apiClient, authHeaders } from "@/lib/api-client";
import type { AwsAccount, JobRun } from "@/lib/types";

export function useAccounts() {
  const { data, error, isLoading, mutate } = useSWR<AwsAccount[]>(
    "/api/v1/aws-accounts",
    (url: string) => apiClient.get<AwsAccount[]>(url, { headers: authHeaders() }),
    { shouldRetryOnError: false }
  );

  return { accounts: data, isLoading, error, mutate };
}

export function useAccount(id: string | null) {
  const { data, error, isLoading, mutate } = useSWR<AwsAccount>(
    id ? `/api/v1/aws-accounts/${id}` : null,
    (url: string) => apiClient.get<AwsAccount>(url, { headers: authHeaders() }),
    { shouldRetryOnError: false }
  );

  return { account: data, isLoading, error, mutate };
}

export function useJobRuns(accountId: string | null) {
  const { data, error, isLoading } = useSWR<JobRun[]>(
    accountId ? `/api/v1/aws-accounts/${accountId}/job-runs` : null,
    (url: string) => apiClient.get<JobRun[]>(url, { headers: authHeaders() }),
    { shouldRetryOnError: false }
  );

  return { jobRuns: data, isLoading, error };
}
