"use client"
import { useState } from "react"
import useSWR from "swr"
import { apiFetcher } from "@/lib/api-client"
import { Spinner } from "@/components/ui/spinner"

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

interface SmtpStatus {
  configured: boolean
  host: string | null
  port: number | null
  from_email: string | null
}

// We only display status + send test — SMTP config lives in env vars, not DB.
export default function EmailSettingsPage() {
  const { data: smtpStatus, isLoading: statusLoading } = useSWR<SmtpStatus>(
    "/api/v1/email/status",
    apiFetcher
  )

  const [showPassword, setShowPassword] = useState(false)
  const [testEmail, setTestEmail] = useState("")
  const [sending, setSending] = useState(false)
  const [sendResult, setSendResult] = useState<{
    ok: boolean
    message: string
  } | null>(null)

  async function handleSendTest() {
    setSending(true)
    setSendResult(null)
    try {
      const res = await fetch(`${API}/api/v1/email/test`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ to: testEmail || undefined }),
      })
      if (!res.ok) {
        const text = await res.text()
        setSendResult({ ok: false, message: text || "Failed to send test email." })
      } else {
        setSendResult({ ok: true, message: "Test email sent successfully!" })
      }
    } catch {
      setSendResult({ ok: false, message: "Request failed. Check your network." })
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">Email Settings</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Configure SMTP to send assignment alerts and weekly digests
        </p>
      </div>

      {/* SMTP Status banner */}
      <div>
        {statusLoading ? (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Spinner className="h-4 w-4" /> Checking SMTP status…
          </div>
        ) : smtpStatus ? (
          smtpStatus.configured ? (
            <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-2.5 text-sm text-green-700">
              <span className="font-medium">SMTP configured</span>
              {smtpStatus.host && (
                <span className="text-green-600">— host: {smtpStatus.host}</span>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-700">
              <span className="font-medium">SMTP not configured</span>
              <span className="text-amber-600">— set SMTP_HOST env var</span>
            </div>
          )
        ) : null}
      </div>

      {/* SMTP Configuration card (read-only display) */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-5">
        <div>
          <h2 className="text-sm font-semibold text-slate-800">SMTP Configuration</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            These values are read from environment variables and cannot be edited here.
          </p>
        </div>

        <div className="space-y-4">
          {/* Host */}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Host <span className="text-slate-400 font-normal">(SMTP_HOST)</span>
            </label>
            <input
              type="text"
              readOnly
              value=""
              placeholder="smtp.sendgrid.net"
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500 placeholder-slate-400 cursor-not-allowed"
            />
          </div>

          {/* Port */}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Port <span className="text-slate-400 font-normal">(SMTP_PORT)</span>
            </label>
            <input
              type="text"
              readOnly
              value=""
              placeholder="587"
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500 placeholder-slate-400 cursor-not-allowed"
            />
          </div>

          {/* Username */}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Username <span className="text-slate-400 font-normal">(SMTP_USERNAME)</span>
            </label>
            <input
              type="text"
              readOnly
              value=""
              placeholder="apikey"
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500 placeholder-slate-400 cursor-not-allowed"
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Password <span className="text-slate-400 font-normal">(SMTP_PASSWORD)</span>
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                readOnly
                value=""
                placeholder="••••••••••••"
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 pr-16 text-sm text-slate-500 placeholder-slate-400 cursor-not-allowed"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-slate-500 hover:text-slate-700 font-medium"
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          {/* From Email */}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              From Email <span className="text-slate-400 font-normal">(SMTP_FROM_EMAIL)</span>
            </label>
            <input
              type="text"
              readOnly
              value=""
              placeholder="security@yourcompany.com"
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500 placeholder-slate-400 cursor-not-allowed"
            />
          </div>

          {/* From Name */}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              From Name <span className="text-slate-400 font-normal">(SMTP_FROM_NAME)</span>
            </label>
            <input
              type="text"
              readOnly
              value=""
              placeholder="Cloud Posture Copilot"
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500 placeholder-slate-400 cursor-not-allowed"
            />
          </div>

          {/* Use TLS */}
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked
              readOnly
              className="rounded border-slate-300 cursor-not-allowed"
              id="use_tls"
            />
            <label htmlFor="use_tls" className="cursor-not-allowed">
              Use TLS (recommended) — controlled via{" "}
              <span className="font-mono text-xs text-slate-500">SMTP_USE_TLS</span>
            </label>
          </div>
        </div>

        {/* Send test email */}
        <div className="border-t border-slate-100 pt-5 space-y-3">
          <div>
            <label
              htmlFor="test_email_recipient"
              className="block text-xs font-medium text-slate-600 mb-1"
            >
              Send test email to (optional — defaults to your account email)
            </label>
            <input
              id="test_email_recipient"
              type="email"
              value={testEmail}
              onChange={(e) => setTestEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {sendResult && (
            <div
              className={
                sendResult.ok
                  ? "rounded-lg border border-green-200 bg-green-50 px-4 py-2.5 text-sm text-green-700"
                  : "rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-600"
              }
            >
              {sendResult.message}
            </div>
          )}

          <button
            type="button"
            onClick={handleSendTest}
            disabled={sending}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {sending ? "Sending…" : "Send Test Email"}
          </button>
        </div>
      </div>

      {/* Env var info notice */}
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
        <p className="text-sm text-amber-800">
          <span className="font-semibold">SMTP credentials are configured via environment variables</span>{" "}
          (<span className="font-mono text-xs">SMTP_HOST</span>,{" "}
          <span className="font-mono text-xs">SMTP_PORT</span>,{" "}
          <span className="font-mono text-xs">SMTP_USERNAME</span>,{" "}
          <span className="font-mono text-xs">SMTP_PASSWORD</span>, etc.) and cannot be stored in the UI.
          Use this page to send a test email and verify your configuration.
        </p>
        <p className="text-xs text-amber-700 mt-2">
          See{" "}
          <span className="font-mono">.env.example</span> in the project root for all available SMTP environment variables.
        </p>
      </div>
    </div>
  )
}
