/**
 * API client — thin fetch wrapper over the FastAPI backend.
 *
 * Rules (enforced here at the boundary):
 * - All calls go through this module; no raw fetch() elsewhere.
 * - Auth token injection happens here.
 * - Error normalisation happens here.
 * - Zero business logic, scoring, or compliance inference here.
 *
 * Sprint 6: credentials: "include" added so the browser automatically sends
 * the httpOnly access_token cookie on every request. authHeaders() is kept
 * as a fallback for non-browser clients / API tools.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function authHeaders(): HeadersInit {
  return {};
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(`API Error ${status}: ${detail}`);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {}
    throw new ApiError(res.status, detail);
  }

  return res.json() as Promise<T>;
}

export const apiClient = {
  get: <T>(path: string, init?: RequestInit) =>
    request<T>(path, { method: "GET", ...init }),
  post: <T>(path: string, body: unknown, init?: RequestInit) =>
    request<T>(path, {
      method: "POST",
      body: JSON.stringify(body),
      ...init,
    }),
  put: <T>(path: string, body: unknown, init?: RequestInit) =>
    request<T>(path, {
      method: "PUT",
      body: JSON.stringify(body),
      ...init,
    }),
  patch: <T>(path: string, body: unknown, init?: RequestInit) =>
    request<T>(path, {
      method: "PATCH",
      body: JSON.stringify(body),
      ...init,
    }),
  delete: <T>(path: string, init?: RequestInit) =>
    request<T>(path, { method: "DELETE", ...init }),
};

/**
 * Shared SWR fetcher — uses apiClient.get() which includes credentials.
 * Usage: useSWR(key, swrFetcher)
 */
export async function swrFetcher<T>(url: string): Promise<T> {
  return apiClient.get<T>(url);
}

/**
 * Shared typed fetcher for use outside SWR contexts.
 * Calls apiClient.get() which sends credentials: "include".
 */
export async function apiFetcher<T>(url: string): Promise<T> {
  return apiClient.get<T>(url);
}
