"use client";

import { useState, useEffect } from "react";
import {
  Building2, Palette, ToggleLeft, Gauge, ShieldCheck, Save,
  Loader2, AlertCircle,
} from "lucide-react";
import {
  useTenantConfig,
  useBudgetStatus,
  updateTenantConfig,
  type TenantConfig,
} from "@/lib/hooks/use-tenant-config";

/* ---------- tiny helpers ---------- */

function SectionHeader({ icon: Icon, title }: { icon: any; title: string }) {
  return (
    <h2 className="flex items-center gap-2 text-lg font-semibold text-white mb-4">
      <Icon className="h-5 w-5 text-blue-400" />
      {title}
    </h2>
  );
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-slate-700 bg-slate-800/60 p-6 ${className}`}>
      {children}
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return <label className="block text-sm font-medium text-slate-300 mb-1">{children}</label>;
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between py-2 cursor-pointer group">
      <span className="text-sm text-slate-300 group-hover:text-white transition-colors">
        {label}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          checked ? "bg-blue-600" : "bg-slate-600"
        }`}
      >
        <span
          className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
            checked ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>
    </label>
  );
}

function ProgressBar({
  label,
  used,
  limit,
  unit = "",
}: {
  label: string;
  used: number;
  limit: number;
  unit?: string;
}) {
  const pct = limit > 0 ? Math.min((used / limit) * 100, 100) : 0;
  const color = pct > 90 ? "bg-red-500" : pct > 70 ? "bg-amber-500" : "bg-blue-500";
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm text-slate-400">{label}</span>
        <span className="text-sm font-medium text-white">
          {used.toLocaleString()}
          {unit} / {limit.toLocaleString()}
          {unit}
        </span>
      </div>
      <div className="h-2 rounded-full bg-slate-700 overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

/* ---------- page ---------- */

export default function TenantAdminPage() {
  const { config, isLoading, error, mutate } = useTenantConfig();
  const { budget } = useBudgetStatus();

  const [form, setForm] = useState<Partial<TenantConfig>>({});
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  // SSO extra fields (not stored in TenantConfig model but sent as part of updates)
  const [ssoClientId, setSsoClientId] = useState("");
  const [ssoTenantId, setSsoTenantId] = useState("");
  const [ssoDomain, setSsoDomain] = useState("");

  useEffect(() => {
    if (config) setForm(config);
  }, [config]);

  const set = <K extends keyof TenantConfig>(key: K, value: TenantConfig[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  async function handleSave() {
    setSaving(true);
    setSaveMsg(null);
    try {
      await updateTenantConfig({
        ...form,
        // pass SSO extras alongside
        ...(form.sso_provider ? ({ sso_client_id: ssoClientId, sso_tenant_id: ssoTenantId, sso_domain: ssoDomain } as any) : {}),
      });
      await mutate();
      setSaveMsg("Saved successfully.");
    } catch (e: any) {
      setSaveMsg(`Error: ${e.message ?? "Unknown"}`);
    } finally {
      setSaving(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin text-blue-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-red-400 p-8">
        <AlertCircle className="h-5 w-5" />
        Failed to load tenant configuration.
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8 p-6 pb-24">
      <h1 className="text-2xl font-bold text-white flex items-center gap-2">
        <Building2 className="h-6 w-6 text-blue-400" />
        Tenant Administration
      </h1>

      {/* ----- Branding ----- */}
      <Card>
        <SectionHeader icon={Palette} title="Branding" />
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label>Display Name</Label>
            <input
              type="text"
              value={form.display_name ?? ""}
              onChange={(e) => set("display_name", e.target.value)}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <Label>Logo URL</Label>
            <input
              type="text"
              value={form.logo_url ?? ""}
              onChange={(e) => set("logo_url", e.target.value || null)}
              placeholder="https://..."
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <Label>Primary Color</Label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={form.primary_color ?? "#3b82f6"}
                onChange={(e) => set("primary_color", e.target.value)}
                className="h-9 w-9 cursor-pointer rounded border border-slate-600 bg-transparent"
              />
              <input
                type="text"
                value={form.primary_color ?? "#3b82f6"}
                onChange={(e) => set("primary_color", e.target.value)}
                className="flex-1 rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>
          <div>
            <Label>Secondary Color</Label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={form.secondary_color ?? "#8b5cf6"}
                onChange={(e) => set("secondary_color", e.target.value)}
                className="h-9 w-9 cursor-pointer rounded border border-slate-600 bg-transparent"
              />
              <input
                type="text"
                value={form.secondary_color ?? "#8b5cf6"}
                onChange={(e) => set("secondary_color", e.target.value)}
                className="flex-1 rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>
        </div>
      </Card>

      {/* ----- Feature Flags ----- */}
      <Card>
        <SectionHeader icon={ToggleLeft} title="Feature Flags" />
        <div className="grid gap-x-8 sm:grid-cols-2">
          <Toggle label="Simulations" checked={form.feature_simulations ?? false} onChange={(v) => set("feature_simulations", v)} />
          <Toggle label="Graph Explorer" checked={form.feature_graph_explorer ?? false} onChange={(v) => set("feature_graph_explorer", v)} />
          <Toggle label="Agent Memory" checked={form.feature_agent_memory ?? false} onChange={(v) => set("feature_agent_memory", v)} />
          <Toggle label="CIEM" checked={form.feature_ciem ?? false} onChange={(v) => set("feature_ciem", v)} />
          <Toggle label="Vulnerabilities" checked={form.feature_vulns ?? false} onChange={(v) => set("feature_vulns", v)} />
          <Toggle label="Detections" checked={form.feature_detections ?? false} onChange={(v) => set("feature_detections", v)} />
        </div>
      </Card>

      {/* ----- Limits ----- */}
      <Card>
        <SectionHeader icon={Gauge} title="Limits" />
        <div className="grid gap-6 sm:grid-cols-3">
          <div>
            <Label>Max Simulations / Month</Label>
            <input
              type="number"
              min={0}
              value={form.max_simulations_per_month ?? 0}
              onChange={(e) => set("max_simulations_per_month", Number(e.target.value))}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <Label>Max Agents / Simulation</Label>
            <input
              type="number"
              min={1}
              value={form.max_agents_per_simulation ?? 1}
              onChange={(e) => set("max_agents_per_simulation", Number(e.target.value))}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <Label>API Budget (USD)</Label>
            <input
              type="range"
              min={0}
              max={10000}
              step={50}
              value={form.api_budget_usd ?? 0}
              onChange={(e) => set("api_budget_usd", Number(e.target.value))}
              className="w-full accent-blue-500"
            />
            <p className="text-xs text-slate-400 mt-1 text-right">
              ${(form.api_budget_usd ?? 0).toLocaleString()}
            </p>
          </div>
        </div>
      </Card>

      {/* ----- SSO ----- */}
      <Card>
        <SectionHeader icon={ShieldCheck} title="Single Sign-On (SSO)" />
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <Label>SSO Provider</Label>
            <select
              value={form.sso_provider ?? ""}
              onChange={(e) => set("sso_provider", e.target.value || null)}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
            >
              <option value="">None</option>
              <option value="auth0">Auth0</option>
              <option value="okta">Okta</option>
              <option value="azure_ad">Azure AD</option>
            </select>
          </div>
          {form.sso_provider && (
            <>
              <div>
                <Label>Client ID</Label>
                <input
                  type="text"
                  value={ssoClientId}
                  onChange={(e) => setSsoClientId(e.target.value)}
                  className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <Label>Tenant ID</Label>
                <input
                  type="text"
                  value={ssoTenantId}
                  onChange={(e) => setSsoTenantId(e.target.value)}
                  className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div className="sm:col-span-2">
                <Label>Domain</Label>
                <input
                  type="text"
                  value={ssoDomain}
                  onChange={(e) => setSsoDomain(e.target.value)}
                  placeholder="your-tenant.auth0.com"
                  className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                />
              </div>
            </>
          )}
        </div>
      </Card>

      {/* ----- Budget Status ----- */}
      {budget && (
        <Card>
          <SectionHeader icon={Gauge} title="Budget Status" />
          <div className="grid gap-6 sm:grid-cols-2">
            <ProgressBar
              label="Simulations This Month"
              used={budget.simulations_used}
              limit={budget.simulations_limit}
            />
            <ProgressBar
              label="API Cost"
              used={budget.cost_used}
              limit={budget.cost_limit}
              unit=" USD"
            />
          </div>
        </Card>
      )}

      {/* ----- Save ----- */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          Save Changes
        </button>
        {saveMsg && (
          <span className={`text-sm ${saveMsg.startsWith("Error") ? "text-red-400" : "text-green-400"}`}>
            {saveMsg}
          </span>
        )}
      </div>
    </div>
  );
}
