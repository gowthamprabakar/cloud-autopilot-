"use client"
import { useOnboarding, dismissOnboarding } from "@/lib/hooks/use-onboarding"
import type { OnboardingProgress } from "@/lib/types"

const STEPS: Array<{
  key: keyof OnboardingProgress
  label: string
  href: string | null
}> = [
  { key: "step_workspace_created",     label: "Workspace created",   href: null },
  { key: "step_aws_account_connected", label: "Connect AWS account", href: "/dashboard/accounts" },
  { key: "step_first_sync_complete",   label: "Run first sync",      href: "/dashboard/accounts" },
  { key: "step_team_member_invited",   label: "Invite team member",  href: "/dashboard/team" },
  { key: "step_sla_configured",        label: "Configure SLA rules", href: "/dashboard/settings/workspace" },
]

export function OnboardingBanner() {
  const { onboarding, mutate } = useOnboarding()

  if (!onboarding || onboarding.dismissed || onboarding.all_complete) return null

  const nextStep = STEPS.find((s) => !(onboarding[s.key] as boolean))

  async function handleDismiss() {
    await dismissOnboarding()
    mutate()
  }

  return (
    <div className="mx-6 mt-4 bg-blue-50 border border-blue-200 rounded-xl p-5">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">🚀</span>
            <h3 className="font-semibold text-slate-800">
              Get started with Cloud Posture Copilot
            </h3>
          </div>

          {/* Progress bar */}
          <div className="flex items-center gap-3 mb-4">
            <div className="flex-1 bg-blue-100 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${onboarding.completion_percentage}%` }}
              />
            </div>
            <span className="text-sm font-medium text-blue-700">
              {onboarding.completion_percentage}%
            </span>
          </div>

          {/* Steps grid */}
          <div className="grid grid-cols-2 gap-2 mb-4">
            {STEPS.map((step) => {
              const done = onboarding[step.key] as boolean
              return (
                <div key={step.key} className="flex items-center gap-2 text-sm">
                  {done ? (
                    <span className="text-green-500">✓</span>
                  ) : (
                    <span className="text-slate-300">○</span>
                  )}
                  <span
                    className={
                      done ? "text-slate-500 line-through" : "text-slate-700"
                    }
                  >
                    {step.label}
                  </span>
                </div>
              )
            })}
          </div>

          {/* CTA */}
          {nextStep?.href && (
            <a
              href={nextStep.href}
              className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-800"
            >
              {nextStep.label} →
            </a>
          )}
        </div>

        <button
          onClick={handleDismiss}
          className="ml-4 text-slate-400 hover:text-slate-600 text-lg leading-none"
          aria-label="Dismiss"
        >
          ×
        </button>
      </div>
    </div>
  )
}
