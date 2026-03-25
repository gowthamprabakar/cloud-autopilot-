import useSWR from "swr"
import type { OnboardingProgress } from "@/lib/types"

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export function useOnboarding() {
  const { data, error, isLoading, mutate } = useSWR<OnboardingProgress | null>(
    `${API}/api/v1/onboarding`,
    (url: string) =>
      fetch(url, { credentials: "include" }).then(async (r) => {
        if (!r.ok) return null
        return r.json() as Promise<OnboardingProgress>
      })
  )
  return { onboarding: data ?? null, error, isLoading, mutate }
}

export async function dismissOnboarding(): Promise<void> {
  await fetch(`${API}/api/v1/onboarding/dismiss`, {
    method: "POST",
    credentials: "include",
  })
}

export async function markOnboardingStep(
  step: string
): Promise<OnboardingProgress> {
  const res = await fetch(`${API}/api/v1/onboarding/mark/${step}`, {
    method: "POST",
    credentials: "include",
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<OnboardingProgress>
}
