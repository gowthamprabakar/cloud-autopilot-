"use client"
import { useState, useEffect } from "react"
import { useWorkspaceSettings, updateWorkspaceSettings } from "@/lib/hooks/use-workspace-settings"
import { testJiraConnection } from "@/lib/hooks/use-jira"
import { Spinner } from "@/components/ui/spinner"
import type { WorkspaceSettingsUpdate } from "@/lib/types"

interface JiraForm {
  jira_base_url: string
  jira_email: string
  jira_api_token: string
  jira_project_key: string
  jira_issue_type: string
}

const DEFAULT_JIRA: JiraForm = {
  jira_base_url: "",
  jira_email: "",
  jira_api_token: "",
  jira_project_key: "",
  jira_issue_type: "Task",
}

const ISSUE_TYPES = ["Task", "Bug", "Story", "Epic", "Sub-task"]

export default function IntegrationsPage() {
  const { settings, isLoading } = useWorkspaceSettings()

  const [form, setForm] = useState<JiraForm>(DEFAULT_JIRA)
  const [showToken, setShowToken] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{
    ok: boolean
    message: string
  } | null>(null)

  // Populate from loaded settings
  useEffect(() => {
    if (settings) {
      setForm({
        jira_base_url: (settings as unknown as Record<string, string>).jira_base_url ?? "",
        jira_email: (settings as unknown as Record<string, string>).jira_email ?? "",
        jira_api_token: (settings as unknown as Record<string, string>).jira_api_token ?? "",
        jira_project_key: (settings as unknown as Record<string, string>).jira_project_key ?? "",
        jira_issue_type: (settings as unknown as Record<string, string>).jira_issue_type ?? "Task",
      })
    }
  }, [settings])

  function handleChange(field: keyof JiraForm, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }))
    setTestResult(null)
  }

  async function handleSave() {
    setSaving(true)
    setSaveError(null)
    setSaved(false)
    try {
      await updateWorkspaceSettings(form as unknown as WorkspaceSettingsUpdate)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save.")
    } finally {
      setSaving(false)
    }
  }

  async function handleTest() {
    setTesting(true)
    setTestResult(null)
    try {
      const result = await testJiraConnection()
      setTestResult(result)
    } catch {
      setTestResult({ ok: false, message: "Test request failed." })
    } finally {
      setTesting(false)
    }
  }

  const isJiraConnected =
    Boolean(form.jira_base_url) &&
    Boolean(form.jira_email) &&
    Boolean(form.jira_api_token)

  return (
    <div className="max-w-2xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">Integrations</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Connect Cloud Posture Copilot with your existing tools
        </p>
      </div>

      {/* Jira card */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-800">Jira</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Create Jira issues from security findings
            </p>
          </div>
          <span
            className={
              isJiraConnected
                ? "inline-flex items-center gap-1 text-xs font-medium text-green-700 bg-green-50 border border-green-200 rounded-full px-2.5 py-1"
                : "inline-flex items-center gap-1 text-xs font-medium text-slate-500 bg-slate-100 border border-slate-200 rounded-full px-2.5 py-1"
            }
          >
            {isJiraConnected ? "Connected ✓" : "Not Connected"}
          </span>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-6">
            <Spinner className="h-5 w-5" />
          </div>
        ) : (
          <div className="space-y-4">
            {/* Jira Base URL */}
            <div>
              <label
                htmlFor="jira_base_url"
                className="block text-xs font-medium text-slate-600 mb-1"
              >
                Jira Base URL
              </label>
              <input
                id="jira_base_url"
                type="url"
                value={form.jira_base_url}
                onChange={(e) => handleChange("jira_base_url", e.target.value)}
                placeholder="https://yourorg.atlassian.net"
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Email */}
            <div>
              <label
                htmlFor="jira_email"
                className="block text-xs font-medium text-slate-600 mb-1"
              >
                Email
              </label>
              <input
                id="jira_email"
                type="email"
                value={form.jira_email}
                onChange={(e) => handleChange("jira_email", e.target.value)}
                placeholder="admin@yourorg.com"
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* API Token */}
            <div>
              <label
                htmlFor="jira_api_token"
                className="block text-xs font-medium text-slate-600 mb-1"
              >
                API Token
              </label>
              <div className="relative">
                <input
                  id="jira_api_token"
                  type={showToken ? "text" : "password"}
                  value={form.jira_api_token}
                  onChange={(e) => handleChange("jira_api_token", e.target.value)}
                  placeholder="••••••••••••••••••••"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 pr-20 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  type="button"
                  onClick={() => setShowToken((v) => !v)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-slate-500 hover:text-slate-700 font-medium"
                >
                  {showToken ? "Hide" : "Reveal"}
                </button>
              </div>
            </div>

            {/* Project Key */}
            <div>
              <label
                htmlFor="jira_project_key"
                className="block text-xs font-medium text-slate-600 mb-1"
              >
                Project Key
              </label>
              <input
                id="jira_project_key"
                type="text"
                value={form.jira_project_key}
                onChange={(e) => handleChange("jira_project_key", e.target.value)}
                placeholder="SEC"
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Issue Type */}
            <div>
              <label
                htmlFor="jira_issue_type"
                className="block text-xs font-medium text-slate-600 mb-1"
              >
                Issue Type
              </label>
              <select
                id="jira_issue_type"
                value={form.jira_issue_type}
                onChange={(e) => handleChange("jira_issue_type", e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                {ISSUE_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>

            {/* Test result */}
            {testResult && (
              <div
                className={
                  testResult.ok
                    ? "rounded-lg border border-green-200 bg-green-50 px-4 py-2.5 text-sm text-green-700"
                    : "rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-600"
                }
              >
                {testResult.message}
              </div>
            )}

            {saveError && (
              <p className="text-sm text-red-600">{saveError}</p>
            )}

            {/* Actions */}
            <div className="flex items-center gap-3 pt-1">
              <button
                type="button"
                onClick={handleTest}
                disabled={testing || !isJiraConnected}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition-colors"
              >
                {testing ? "Testing…" : "Test Connection"}
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {saving ? "Saving…" : "Save Configuration"}
              </button>
              {saved && (
                <span className="text-sm text-green-600 font-medium">Saved ✓</span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Slack placeholder */}
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 opacity-60">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-slate-700">Slack</h2>
              <span className="text-xs font-medium text-slate-500 bg-slate-200 rounded-full px-2 py-0.5">
                Coming Soon
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Send alerts to Slack channels (Coming Soon)
            </p>
          </div>
          <span className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 bg-white border border-slate-200 rounded-full px-2.5 py-1">
            Not Connected
          </span>
        </div>
      </div>
    </div>
  )
}
