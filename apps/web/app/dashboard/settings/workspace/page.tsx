"use client";
import { useState, useEffect } from "react";
import { useWorkspaceSettings, updateWorkspaceSettings } from "@/lib/hooks/use-workspace-settings";
import { Spinner } from "@/components/ui/spinner";
import type { WorkspaceSettingsUpdate } from "@/lib/types";

type SeverityField = keyof WorkspaceSettingsUpdate;

interface SlaSetting {
  label: string;
  field: SeverityField;
  defaultValue: number;
}

const SLA_FIELDS: SlaSetting[] = [
  { label: "Critical", field: "sla_days_critical", defaultValue: 3 },
  { label: "High", field: "sla_days_high", defaultValue: 7 },
  { label: "Medium", field: "sla_days_medium", defaultValue: 30 },
  { label: "Low", field: "sla_days_low", defaultValue: 90 },
  { label: "Info", field: "sla_days_info", defaultValue: 180 },
];

export default function WorkspaceSettingsPage() {
  const { settings, isLoading, error, mutate } = useWorkspaceSettings();

  const [form, setForm] = useState<WorkspaceSettingsUpdate>({
    sla_days_critical: 3,
    sla_days_high: 7,
    sla_days_medium: 30,
    sla_days_low: 90,
    sla_days_info: 180,
    finding_auto_close_days: 90,
  });

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  // Populate form when settings load
  useEffect(() => {
    if (settings) {
      setForm({
        sla_days_critical: settings.sla_days_critical,
        sla_days_high: settings.sla_days_high,
        sla_days_medium: settings.sla_days_medium,
        sla_days_low: settings.sla_days_low,
        sla_days_info: settings.sla_days_info,
        finding_auto_close_days: settings.finding_auto_close_days,
      });
    }
  }, [settings]);

  function handleChange(field: SeverityField, value: string) {
    const parsed = parseInt(value, 10);
    setForm((prev) => ({ ...prev, [field]: isNaN(parsed) ? 1 : parsed }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);
    setSaved(false);
    try {
      await updateWorkspaceSettings(form);
      await mutate();
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save settings.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">Workspace Settings</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Configure SLA thresholds and auto-close behaviour for your workspace.
        </p>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-600">
          Failed to load workspace settings.
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-6 w-6" />
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* SLA Configuration card */}
          <div className="rounded-xl border border-slate-200 bg-white p-6">
            <h2 className="text-sm font-semibold text-slate-800 mb-1">
              SLA Configuration
            </h2>
            <p className="text-xs text-slate-500 mb-5">
              Define how many days each severity level has before a finding is
              considered a breach.
            </p>

            <div className="space-y-4">
              {SLA_FIELDS.map(({ label, field, defaultValue }) => (
                <div key={field} className="flex items-center justify-between gap-4">
                  <label
                    htmlFor={field}
                    className="text-sm font-medium text-slate-700 w-20 shrink-0"
                  >
                    {label}
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      id={field}
                      type="number"
                      min={1}
                      max={365}
                      value={form[field] ?? defaultValue}
                      onChange={(e) => handleChange(field, e.target.value)}
                      className="w-20 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-800 text-right focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <span className="text-sm text-slate-500">days</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Auto-close card */}
          <div className="rounded-xl border border-slate-200 bg-white p-6">
            <h2 className="text-sm font-semibold text-slate-800 mb-1">
              Auto-Close
            </h2>
            <p className="text-xs text-slate-500 mb-5">
              Automatically close findings that have not been updated after the
              specified number of days.
            </p>

            <div className="flex items-center justify-between gap-4">
              <label
                htmlFor="finding_auto_close_days"
                className="text-sm font-medium text-slate-700 shrink-0"
              >
                Auto-close after
              </label>
              <div className="flex items-center gap-2">
                <input
                  id="finding_auto_close_days"
                  type="number"
                  min={1}
                  max={365}
                  value={form.finding_auto_close_days ?? 90}
                  onChange={(e) =>
                    handleChange("finding_auto_close_days", e.target.value)
                  }
                  className="w-20 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-800 text-right focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <span className="text-sm text-slate-500">days</span>
              </div>
            </div>
          </div>

          {saveError && (
            <p className="text-sm text-red-600">{saveError}</p>
          )}

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {saving ? "Saving…" : "Save Changes"}
            </button>
            {saved && (
              <span className="text-sm text-green-600 font-medium">Saved ✓</span>
            )}
          </div>
        </form>
      )}
    </div>
  );
}
