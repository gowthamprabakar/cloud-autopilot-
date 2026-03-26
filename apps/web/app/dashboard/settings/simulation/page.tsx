"use client";

import { useEffect, useState } from "react";

/* ------------------------------------------------------------------ */
/*  Types & defaults                                                   */
/* ------------------------------------------------------------------ */
interface SimulationSettings {
  claude_model: string;
  scout_token_limit: number;
  report_token_limit: number;
  context_chaining: boolean;
  wiz_agents: boolean;
  auto_switch: boolean;
  save_history: boolean;
  max_agents: number;
  timeout_seconds: number;
}

const DEFAULTS: SimulationSettings = {
  claude_model: "claude-sonnet-4-20250514",
  scout_token_limit: 800,
  report_token_limit: 2000,
  context_chaining: true,
  wiz_agents: true,
  auto_switch: false,
  save_history: true,
  max_agents: 6,
  timeout_seconds: 300,
};

const STORAGE_KEY = "cloud-copilot:simulation-settings";

const MODELS = [
  { value: "claude-sonnet-4-20250514", label: "Claude Sonnet 4" },
  { value: "claude-opus-4-20250514", label: "Claude Opus 4" },
  { value: "claude-haiku-3-20250307", label: "Claude Haiku 3" },
  { value: "claude-sonnet-4-20250514", label: "Claude Sonnet 4 (default)" },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */
function loadSettings(): SimulationSettings {
  if (typeof window === "undefined") return DEFAULTS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? { ...DEFAULTS, ...JSON.parse(raw) } : DEFAULTS;
  } catch {
    return DEFAULTS;
  }
}

function saveSettings(s: SimulationSettings) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
  } catch {
    /* quota exceeded – ignore */
  }
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{title}</h3>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

function Toggle({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-start gap-3 cursor-pointer group">
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative mt-0.5 inline-flex h-5 w-9 shrink-0 rounded-full transition-colors ${
          checked ? "bg-blue-600" : "bg-slate-700"
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform mt-0.5 ${
            checked ? "translate-x-4 ml-0.5" : "translate-x-0.5"
          }`}
        />
      </button>
      <div className="flex flex-col gap-0.5">
        <span className="text-sm text-white group-hover:text-blue-300 transition-colors">{label}</span>
        <span className="text-[11px] text-slate-500 leading-snug">{description}</span>
      </div>
    </label>
  );
}

function NumberInput({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="flex items-center justify-between gap-4">
      <span className="text-sm text-slate-300">{label}</span>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step ?? 1}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-24 rounded-lg bg-slate-800 border border-slate-700 px-3 py-1.5 text-sm text-white text-right focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
    </label>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */
export default function SimulationSettingsPage() {
  const [settings, setSettings] = useState<SimulationSettings>(DEFAULTS);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setSettings(loadSettings());
  }, []);

  function update<K extends keyof SimulationSettings>(key: K, value: SimulationSettings[K]) {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  }

  function handleSave() {
    saveSettings(settings);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  function handleReset() {
    setSettings(DEFAULTS);
    saveSettings(DEFAULTS);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-2xl px-6 py-10">
        <h1 className="text-lg font-bold tracking-wide mb-1">Simulation Settings</h1>
        <p className="text-sm text-slate-500 mb-8">
          Configure agent models, token limits, and behavior for simulation runs.
        </p>

        <div className="space-y-8">
          {/* Model selection */}
          <Section title="Model">
            <label className="flex items-center justify-between gap-4">
              <span className="text-sm text-slate-300">Claude Model</span>
              <select
                value={settings.claude_model}
                onChange={(e) => update("claude_model", e.target.value)}
                className="w-56 rounded-lg bg-slate-800 border border-slate-700 px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {MODELS.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </label>
          </Section>

          {/* Token limits */}
          <Section title="Token Limits">
            <NumberInput
              label="Scout token limit"
              value={settings.scout_token_limit}
              min={400}
              max={2000}
              step={100}
              onChange={(v) => update("scout_token_limit", v)}
            />
            <NumberInput
              label="Report token limit"
              value={settings.report_token_limit}
              min={600}
              max={4000}
              step={100}
              onChange={(v) => update("report_token_limit", v)}
            />
          </Section>

          {/* Behavior toggles */}
          <Section title="Behavior">
            <Toggle
              label="Context Chaining"
              description="Pass prior agent context to downstream agents for richer analysis."
              checked={settings.context_chaining}
              onChange={(v) => update("context_chaining", v)}
            />
            <Toggle
              label="Wiz Agents"
              description="Enable Wiz-specific coverage agents for CNAPP module gap detection."
              checked={settings.wiz_agents}
              onChange={(v) => update("wiz_agents", v)}
            />
            <Toggle
              label="Auto-Switch"
              description="Automatically switch to the next phase when the current one completes."
              checked={settings.auto_switch}
              onChange={(v) => update("auto_switch", v)}
            />
            <Toggle
              label="Save History"
              description="Persist simulation run history to localStorage for review."
              checked={settings.save_history}
              onChange={(v) => update("save_history", v)}
            />
          </Section>

          {/* Limits */}
          <Section title="Limits">
            <NumberInput
              label="Max agents"
              value={settings.max_agents}
              min={1}
              max={12}
              onChange={(v) => update("max_agents", v)}
            />
            <NumberInput
              label="Timeout (seconds)"
              value={settings.timeout_seconds}
              min={30}
              max={900}
              step={30}
              onChange={(v) => update("timeout_seconds", v)}
            />
          </Section>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 mt-10 pt-6 border-t border-slate-800">
          <button
            type="button"
            onClick={handleSave}
            className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm font-medium transition-colors"
          >
            {saved ? "Saved" : "Save Settings"}
          </button>
          <button
            type="button"
            onClick={handleReset}
            className="px-5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-sm font-medium text-slate-300 transition-colors"
          >
            Reset to Defaults
          </button>
        </div>
      </div>
    </div>
  );
}
