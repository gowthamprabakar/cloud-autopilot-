"use client";

import { useState } from "react";
import {
  Shield, ChevronDown, ChevronRight, AlertTriangle, CheckCircle2,
  XCircle, Loader2,
} from "lucide-react";
import {
  useMITRECoverage,
  useMITREHeatmap,
  type TechniqueCoverage,
} from "@/lib/hooks/use-mitre";

// ── Helpers ──────────────────────────────────────────────────────────────────

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ");
}

function coverageColor(pct: number): string {
  if (pct >= 80) return "bg-emerald-600";
  if (pct >= 50) return "bg-yellow-500";
  return "bg-red-600";
}

function coverageTextColor(pct: number): string {
  if (pct >= 80) return "text-emerald-400";
  if (pct >= 50) return "text-yellow-400";
  return "text-red-400";
}

function coverageBorderColor(pct: number): string {
  if (pct >= 80) return "border-emerald-600/40";
  if (pct >= 50) return "border-yellow-500/40";
  return "border-red-600/40";
}

/** Canonical tactic display order */
const TACTIC_ORDER = [
  "Reconnaissance",
  "Resource Development",
  "Initial Access",
  "Execution",
  "Persistence",
  "Privilege Escalation",
  "Defense Evasion",
  "Credential Access",
  "Discovery",
  "Lateral Movement",
  "Collection",
  "Exfiltration",
  "Impact",
];

// ── Stat Card ────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, color }: {
  label: string; value: string | number; sub?: string; color?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/60 p-5">
      <p className="text-xs font-medium uppercase tracking-wider text-slate-400">{label}</p>
      <p className={cn("mt-1 text-2xl font-bold", color ?? "text-white")}>{value}</p>
      {sub && <p className="mt-0.5 text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

// ── Tactic Column ────────────────────────────────────────────────────────────

function TacticColumn({ name, data }: {
  name: string;
  data: { total_techniques: number; covered: number; coverage_pct: number; techniques: TechniqueCoverage[] };
}) {
  const [expanded, setExpanded] = useState(false);
  const pct = data.coverage_pct;

  return (
    <div className={cn(
      "flex flex-col rounded-lg border bg-slate-800/50 overflow-hidden",
      coverageBorderColor(pct),
    )}>
      {/* Header bar */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between px-3 py-2.5 hover:bg-slate-700/40 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0">
          {expanded ? <ChevronDown className="h-3.5 w-3.5 text-slate-400 shrink-0" /> : <ChevronRight className="h-3.5 w-3.5 text-slate-400 shrink-0" />}
          <span className="text-xs font-semibold text-slate-200 truncate">{name}</span>
        </div>
        <span className={cn("text-xs font-bold tabular-nums ml-2 shrink-0", coverageTextColor(pct))}>
          {pct.toFixed(0)}%
        </span>
      </button>

      {/* Coverage bar */}
      <div className="mx-3 mb-2">
        <div className="h-1.5 rounded-full bg-slate-700 overflow-hidden">
          <div
            className={cn("h-full rounded-full transition-all", coverageColor(pct))}
            style={{ width: `${Math.max(pct, 2)}%` }}
          />
        </div>
        <p className="mt-1 text-[10px] text-slate-500">{data.covered}/{data.total_techniques} techniques</p>
      </div>

      {/* Expanded technique list */}
      {expanded && (
        <div className="border-t border-slate-700 max-h-64 overflow-y-auto">
          {data.techniques.map((t) => (
            <div
              key={t.technique_id}
              className="flex items-center gap-2 px-3 py-1.5 text-xs border-b border-slate-700/50 last:border-0"
            >
              {t.covered
                ? <CheckCircle2 className="h-3 w-3 text-emerald-400 shrink-0" />
                : <XCircle className="h-3 w-3 text-red-400 shrink-0" />}
              <span className="font-mono text-slate-500 shrink-0">{t.technique_id}</span>
              <span className="text-slate-300 truncate">{t.name}</span>
              {t.finding_count > 0 && (
                <span className="ml-auto text-[10px] text-slate-500 shrink-0">{t.finding_count} findings</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Technique Matrix ─────────────────────────────────────────────────────────

function TechniqueMatrix({ techniques }: { techniques: Record<string, TechniqueCoverage> }) {
  const grouped: Record<string, TechniqueCoverage[]> = {};
  for (const t of Object.values(techniques)) {
    if (!grouped[t.tactic]) grouped[t.tactic] = [];
    grouped[t.tactic].push(t);
  }

  const orderedTactics = TACTIC_ORDER.filter((t) => grouped[t]);

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/60 p-5">
      <h3 className="text-sm font-semibold text-white mb-4">Technique Matrix</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {orderedTactics.map((tactic) => (
          <div key={tactic}>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">{tactic}</p>
            <div className="flex flex-wrap gap-1">
              {grouped[tactic].map((t) => (
                <span
                  key={t.technique_id}
                  title={`${t.technique_id}: ${t.name} (${t.finding_count} findings)`}
                  className={cn(
                    "inline-block px-1.5 py-0.5 rounded text-[10px] font-mono cursor-default",
                    t.covered
                      ? "bg-emerald-900/60 text-emerald-300 border border-emerald-700/40"
                      : "bg-red-900/40 text-red-300 border border-red-700/40",
                  )}
                >
                  {t.technique_id}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Uncovered Techniques ─────────────────────────────────────────────────────

function UncoveredList({ techniques }: { techniques: Record<string, TechniqueCoverage> }) {
  const uncovered = Object.values(techniques)
    .filter((t) => !t.covered)
    .sort((a, b) => a.tactic.localeCompare(b.tactic) || a.technique_id.localeCompare(b.technique_id));

  if (uncovered.length === 0) {
    return (
      <div className="rounded-xl border border-emerald-700/40 bg-emerald-900/20 p-5 text-center">
        <CheckCircle2 className="h-6 w-6 text-emerald-400 mx-auto mb-2" />
        <p className="text-sm text-emerald-300 font-medium">Full coverage achieved</p>
        <p className="text-xs text-slate-400 mt-1">All tracked ATT&CK techniques have detection coverage.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/60 p-5">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="h-4 w-4 text-red-400" />
        <h3 className="text-sm font-semibold text-white">Uncovered Techniques ({uncovered.length})</h3>
      </div>
      <p className="text-xs text-slate-400 mb-3">Techniques without detection coverage, prioritized for remediation.</p>
      <div className="max-h-80 overflow-y-auto space-y-1">
        {uncovered.map((t) => (
          <div key={t.technique_id} className="flex items-center gap-3 rounded-lg px-3 py-2 bg-slate-700/30 border border-slate-700/50">
            <XCircle className="h-3.5 w-3.5 text-red-400 shrink-0" />
            <span className="font-mono text-xs text-slate-400 shrink-0 w-16">{t.technique_id}</span>
            <span className="text-xs text-slate-200 truncate">{t.name}</span>
            <span className="ml-auto text-[10px] text-slate-500 shrink-0 bg-slate-700/60 px-2 py-0.5 rounded">{t.tactic}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function MITREPage() {
  const { coverage, isLoading: covLoading, error: covError } = useMITRECoverage();
  const { heatmap, isLoading: hmLoading, error: hmError } = useMITREHeatmap();

  const isLoading = covLoading || hmLoading;
  const error = covError || hmError;

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/60 px-6 py-5">
        <div className="flex items-center gap-3">
          <Shield className="h-5 w-5 text-blue-400" />
          <div>
            <h1 className="text-lg font-bold">MITRE ATT&CK Coverage</h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Technique coverage analysis mapped to MITRE ATT&CK Cloud (IaaS) framework
            </p>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Loading */}
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-6 w-6 animate-spin text-blue-400" />
            <span className="ml-3 text-sm text-slate-400">Loading ATT&CK coverage data...</span>
          </div>
        )}

        {/* Error */}
        {error && !isLoading && (
          <div className="rounded-xl border border-red-700/40 bg-red-900/20 p-5 text-center">
            <AlertTriangle className="h-6 w-6 text-red-400 mx-auto mb-2" />
            <p className="text-sm text-red-300">Failed to load MITRE ATT&CK data</p>
            <p className="text-xs text-slate-400 mt-1">Check API connectivity and try again.</p>
          </div>
        )}

        {/* Coverage Summary */}
        {coverage && !isLoading && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard
                label="Total Techniques"
                value={coverage.total_techniques}
                sub="ATT&CK Cloud (IaaS)"
              />
              <StatCard
                label="Covered"
                value={coverage.covered}
                sub="with detection findings"
                color="text-emerald-400"
              />
              <StatCard
                label="Coverage"
                value={`${coverage.coverage_pct.toFixed(1)}%`}
                sub="technique coverage rate"
                color={coverageTextColor(coverage.coverage_pct)}
              />
              <StatCard
                label="Uncovered"
                value={coverage.uncovered}
                sub="remediation candidates"
                color={coverage.uncovered > 0 ? "text-red-400" : "text-emerald-400"}
              />
            </div>

            {/* Overall coverage bar */}
            <div className="rounded-xl border border-slate-700 bg-slate-800/60 p-5">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-slate-400">Overall Coverage</span>
                <span className={cn("text-sm font-bold", coverageTextColor(coverage.coverage_pct))}>
                  {coverage.coverage_pct.toFixed(1)}%
                </span>
              </div>
              <div className="h-3 rounded-full bg-slate-700 overflow-hidden">
                <div
                  className={cn("h-full rounded-full transition-all", coverageColor(coverage.coverage_pct))}
                  style={{ width: `${Math.max(coverage.coverage_pct, 1)}%` }}
                />
              </div>
            </div>
          </>
        )}

        {/* Tactic Heatmap */}
        {heatmap && !isLoading && (
          <div>
            <h2 className="text-sm font-semibold text-white mb-3">Tactic Heatmap</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {TACTIC_ORDER.filter((t) => heatmap.tactics[t]).map((tactic) => (
                <TacticColumn key={tactic} name={tactic} data={heatmap.tactics[tactic]} />
              ))}
            </div>
          </div>
        )}

        {/* Technique Matrix */}
        {coverage && !isLoading && coverage.techniques && (
          <TechniqueMatrix techniques={coverage.techniques} />
        )}

        {/* Uncovered Techniques */}
        {coverage && !isLoading && coverage.techniques && (
          <UncoveredList techniques={coverage.techniques} />
        )}
      </div>
    </div>
  );
}
