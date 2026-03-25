"use client";

import { useState } from "react";
import { Mail, Send, Plus, X } from "lucide-react";
import { useReportSchedule, updateReportSchedule, sendReportNow } from "@/lib/hooks/use-reports";

const DAY_NAMES = ["", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function ReportsPage() {
  const { schedule, isLoading, mutate } = useReportSchedule();
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  const [newRecipient, setNewRecipient] = useState("");

  const handleToggle = async () => {
    if (!schedule) return;
    const enabled = !schedule.enabled;
    setSaving(true);
    setError("");
    try {
      await updateReportSchedule({ enabled });
      await mutate();
      setSuccess(enabled ? "Reports enabled." : "Reports disabled.");
    } catch {
      setError("Failed to update schedule.");
    } finally {
      setSaving(false);
    }
  };

  const handleFrequencyChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const frequency = e.target.value as "weekly" | "monthly";
    setError("");
    try {
      await updateReportSchedule({ frequency });
      await mutate();
    } catch {
      setError("Failed to update frequency.");
    }
  };

  const handleDayChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    setError("");
    try {
      await updateReportSchedule({ day_of_week: parseInt(e.target.value) });
      await mutate();
    } catch {
      setError("Failed to update day.");
    }
  };

  const addRecipient = async () => {
    if (!newRecipient || !schedule) return;
    const updated = [...(schedule.recipients ?? []), newRecipient];
    setError("");
    try {
      await updateReportSchedule({ recipients: updated });
      await mutate();
      setNewRecipient("");
    } catch {
      setError("Failed to add recipient.");
    }
  };

  const removeRecipient = async (email: string) => {
    if (!schedule) return;
    const updated = schedule.recipients.filter((r) => r !== email);
    setError("");
    try {
      await updateReportSchedule({ recipients: updated });
      await mutate();
    } catch {
      setError("Failed to remove recipient.");
    }
  };

  const handleSendNow = async () => {
    setSending(true);
    setError("");
    try {
      const result = await sendReportNow();
      setSuccess(
        `Report sent to ${result.sent} recipient${result.sent !== 1 ? "s" : ""}.`
      );
    } catch {
      setError("Failed to send report. Check SMTP settings.");
    } finally {
      setSending(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4 max-w-2xl">
        {[1, 2].map((i) => (
          <div key={i} className="h-32 bg-slate-100 animate-pulse rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">Scheduled Reports</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Automatically email an executive security digest to your team.
        </p>
      </div>

      {/* Success alert */}
      {success && (
        <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
          {success}
        </div>
      )}

      {/* Error alert */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Schedule card */}
      <div className="rounded-xl border border-slate-200 bg-white">
        <div className="px-6 py-4 border-b border-slate-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Mail className="h-5 w-5 text-slate-500" />
              <h2 className="text-base font-semibold text-slate-900">
                Report Schedule
              </h2>
            </div>
            {/* Toggle switch */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-500">
                {schedule?.enabled ? "Active" : "Inactive"}
              </span>
              <button
                role="switch"
                aria-checked={schedule?.enabled ?? false}
                onClick={handleToggle}
                disabled={saving}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 disabled:opacity-50 ${
                  schedule?.enabled ? "bg-blue-600" : "bg-slate-300"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                    schedule?.enabled ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            When enabled, a digest email is sent on the configured schedule.
          </p>
        </div>

        <div className="px-6 py-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-slate-700">
                Frequency
              </label>
              <select
                value={schedule?.frequency ?? "weekly"}
                onChange={handleFrequencyChange}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-slate-700">
                Send on
              </label>
              <select
                value={String(schedule?.day_of_week ?? 1)}
                onChange={handleDayChange}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {DAY_NAMES.slice(1).map((day, i) => (
                  <option key={i + 1} value={String(i + 1)}>
                    {day}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {schedule?.last_sent_at && (
            <p className="text-xs text-slate-500">
              Last sent: {new Date(schedule.last_sent_at).toLocaleString()}
            </p>
          )}
        </div>
      </div>

      {/* Recipients card */}
      <div className="rounded-xl border border-slate-200 bg-white">
        <div className="px-6 py-4 border-b border-slate-100">
          <h2 className="text-base font-semibold text-slate-900">Recipients</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Who receives the digest email. Requires SMTP to be configured.
          </p>
        </div>
        <div className="px-6 py-4 space-y-4">
          <div className="flex gap-2">
            <input
              type="email"
              placeholder="exec@example.com"
              value={newRecipient}
              onChange={(e) => setNewRecipient(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addRecipient()}
              className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={addRecipient}
              disabled={!newRecipient}
              className="inline-flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              <Plus className="h-4 w-4" />
              Add
            </button>
          </div>

          <div className="flex flex-wrap gap-2">
            {(schedule?.recipients ?? []).length === 0 && (
              <p className="text-sm text-slate-500">No recipients configured.</p>
            )}
            {(schedule?.recipients ?? []).map((email) => (
              <span
                key={email}
                className="inline-flex items-center gap-1 rounded-full bg-slate-100 border border-slate-200 pl-3 pr-2 py-0.5 text-xs font-medium text-slate-700"
              >
                {email}
                <button
                  onClick={() => removeRecipient(email)}
                  className="ml-0.5 text-slate-400 hover:text-red-500 transition-colors"
                  aria-label={`Remove ${email}`}
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Send now card */}
      <div className="rounded-xl border border-slate-200 bg-white">
        <div className="px-6 py-4 border-b border-slate-100">
          <h2 className="text-base font-semibold text-slate-900">Send Now</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Trigger an immediate digest send to all configured recipients.
          </p>
        </div>
        <div className="px-6 py-4">
          <button
            onClick={handleSendNow}
            disabled={sending}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="h-4 w-4" />
            {sending ? "Sending…" : "Send Digest Now"}
          </button>
        </div>
      </div>
    </div>
  );
}
