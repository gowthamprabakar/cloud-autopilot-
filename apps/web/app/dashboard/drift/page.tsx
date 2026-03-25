"use client";

import { useState } from "react";
import {
  GitCompare, TrendingUp, Layers, RefreshCw,
  ArrowRight, ChevronDown, ChevronRight
} from "lucide-react";
import {
  useDriftSummary,
  useRecurrences,
  useDriftSignals,
  useRootCauseClusters,
  type Recurrence,
  type DriftSignal,
  type RootCauseCluster,
} from "@/lib/hooks/use-drift";
import { cn } from "@/lib/utils";

// ── Helpers ───────────────────────────────────────────────────────────────────

const SEV_BADGE: Record<string, string> = {
  critical: "bg-red-500/10 text-red-400 border border-red-500/20",
  high:     "bg-orange-500/10 text-orange-400 border border-orange-500/20",
  medium:   "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20",
  low:      "bg-blue-500/10 text-blue-400 border border-blue-500/20",
  info:     "bg-slate-500/10 text-slate-400 border border-slate-500/20",
};

function sevBadge(severity: string) {
  const s = severity.toLowerCase();
  return SEV_BADGE[s] ?? SEV_BADGE.info;
}

function truncate(str: string, max = 48) {
  return str.length > max ? str.slice(0, max) + "\u2026" : str;
}

function fmtDate(iso: string | null) {
  if (!iso) return "\u2014";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

// ── Summary card ──────────────────────────────────────────────────────────────

function SummaryCard({
  label, value, icon: Icon, accent = "text-blue-400",
  sub,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  accent?: string;
  sub?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5 flex flex-col gap-1">
      <div className="flex items-center gap-2 text-xs text-slate-500 uppercase tracking-wider">
        <Icon className={cn("h-4 w-4", accent)} />
        {label}
      </div>
      <p className="text-2xl font-semibold text-white">{value}</p>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

// ── Tab button ────────────────────────────────────────────────────────────────

type Tab = "recurrences" | "signals" | "clusters";

function TabButton({
  active, label, count, onClick,
}: {
  active: boolean; label: string; count: number; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "px-4 py-2 text-sm font-medium rounded-lg transition-colors",
        active
          ? "bg-blue-600/20 text-blue-400"
          : "text-slate-400 hover:text-white hover:bg-slate-800",
      )}
    >
      {label}
      <span className={cn(
        "ml-2 text-xs px-1.5 py-0.5 rounded-full",
        active ? "bg-blue-500/20 text-blue-300" : "bg-slate-800 text-slate-500",
      )}>
        {count}
      </span>
    </button>
  );
}

// ── Recurrences table ─────────────────────────────────────────────────────────

function RecurrencesTab({ recurrences }: { recurrences: Recurrence[] }) {
  if (recurrences.length === 0) {
    return (
      <div className="text-center py-16 text-slate-500">
        <RefreshCw className="h-8 w-8 mx-auto mb-3 opacity-40" />
        <p>No recurring findings detected yet.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-slate-500 uppercase tracking-wider border-b border-slate-800">
            <th className="py-3 px-4">Title</th>
            <th className="py-3 px-4">Severity</th>
            <th className="py-3 px-4">Resource</th>
            <th className="py-3 px-4 text-center">Occurrences</th>
            <th className="py-3 px-4">Status</th>
            <th className="py-3 px-4">First Resolved</th>
            <th className="py-3 px-4">Reopened</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60">
          {recurrences.map((r) => (
            <tr key={r.fingerprint} className="hover:bg-slate-800/40 transition-colors">
              <td className="py-3 px-4 text-white font-medium max-w-xs">
                {truncate(r.title, 56)}
              </td>
              <td className="py-3 px-4">
                <span className={cn("text-xs px-2 py-0.5 rounded-full capitalize", sevBadge(r.severity))}>
                  {r.severity}
                </span>
              </td>
              <td className="py-3 px-4 text-slate-400 font-mono text-xs max-w-[200px] truncate">
                {truncate(r.resource_arn, 40)}
              </td>
              <td className="py-3 px-4 text-center">
                <span className="text-white font-semibold">{r.occurrences}</span>
              </td>
              <td className="py-3 px-4">
                <span className="text-xs px-2 py-0.5 rounded-full bg-orange-500/10 text-orange-400 border border-orange-500/20">
                  RECURRED
                </span>
              </td>
              <td className="py-3 px-4 text-slate-400 text-xs">{fmtDate(r.first_resolved_at)}</td>
              <td className="py-3 px-4 text-slate-400 text-xs">{fmtDate(r.reopened_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Drift Signals table ───────────────────────────────────────────────────────

function DriftSignalsTab({ signals }: { signals: DriftSignal[] }) {
  if (signals.length === 0) {
    return (
      <div className="text-center py-16 text-slate-500">
        <TrendingUp className="h-8 w-8 mx-auto mb-3 opacity-40" />
        <p>No drift signals detected yet.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-slate-500 uppercase tracking-wider border-b border-slate-800">
            <th className="py-3 px-4">Resource</th>
            <th className="py-3 px-4">Type</th>
            <th className="py-3 px-4">Severity Progression</th>
            <th className="py-3 px-4 text-center">Findings</th>
            <th className="py-3 px-4">Worst Title</th>
            <th className="py-3 px-4">Region</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60">
          {signals.map((s, i) => (
            <tr key={`${s.resource_arn}-${i}`} className="hover:bg-slate-800/40 transition-colors">
              <td className="py-3 px-4 text-slate-300 font-mono text-xs max-w-[200px] truncate">
                {truncate(s.resource_arn, 40)}
              </td>
              <td className="py-3 px-4">
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-slate-300">
                  {s.resource_type}
                </span>
              </td>
              <td className="py-3 px-4">
                <div className="flex items-center gap-1.5 flex-wrap">
                  {s.severities.map((sev, j) => (
                    <span key={j} className="flex items-center gap-1">
                      <span className={cn("text-xs px-2 py-0.5 rounded-full capitalize", sevBadge(sev))}>
                        {sev}
                      </span>
                      {j < s.severities.length - 1 && (
                        <ArrowRight className="h-3 w-3 text-slate-600" />
                      )}
                    </span>
                  ))}
                </div>
              </td>
              <td className="py-3 px-4 text-center text-white font-semibold">
                {s.finding_count}
              </td>
              <td className="py-3 px-4 text-slate-400 max-w-xs">
                {truncate(s.worst_title, 48)}
              </td>
              <td className="py-3 px-4 text-slate-500 text-xs">{s.region}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Root Cause Clusters ───────────────────────────────────────────────────────

function ClustersTab({ clusters }: { clusters: RootCauseCluster[] }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  if (clusters.length === 0) {
    return (
      <div className="text-center py-16 text-slate-500">
        <Layers className="h-8 w-8 mx-auto mb-3 opacity-40" />
        <p>No root cause clusters identified yet.</p>
      </div>
    );
  }

  function toggle(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {clusters.map((c) => {
        const isOpen = expanded.has(c.cluster_id);
        return (
          <div
            key={c.cluster_id}
            className="rounded-xl border border-slate-800 bg-slate-900 p-5 flex flex-col gap-3"
          >
            {/* Header */}
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <h3 className="text-white font-semibold text-sm leading-snug">
                  {c.root_cause_pattern}
                </h3>
                <div className="flex items-center gap-2 mt-1.5">
                  <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-slate-300">
                    {c.resource_type}
                  </span>
                  <span className="text-xs text-slate-500">
                    {c.finding_count} finding{c.finding_count !== 1 ? "s" : ""}
                  </span>
                </div>
              </div>
              <button
                onClick={() => toggle(c.cluster_id)}
                className="text-slate-500 hover:text-white transition-colors mt-0.5"
              >
                {isOpen
                  ? <ChevronDown className="h-4 w-4" />
                  : <ChevronRight className="h-4 w-4" />}
              </button>
            </div>

            {/* Severity distribution */}
            <div className="flex items-center gap-1.5 flex-wrap">
              {Object.entries(c.severity_distribution).map(([sev, count]) => (
                <span
                  key={sev}
                  className={cn("text-xs px-2 py-0.5 rounded-full capitalize", sevBadge(sev))}
                >
                  {sev}: {count}
                </span>
              ))}
            </div>

            {/* Footer info */}
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>{c.affected_resources.length} affected resource{c.affected_resources.length !== 1 ? "s" : ""}</span>
              <span className="truncate max-w-[200px]" title={c.sample_title}>
                {truncate(c.sample_title, 40)}
              </span>
            </div>

            {/* Expanded details */}
            {isOpen && (
              <div className="border-t border-slate-800 pt-3 mt-1">
                <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">Affected Resources</p>
                <div className="flex flex-col gap-1">
                  {c.affected_resources.map((arn, i) => (
                    <span key={i} className="text-xs font-mono text-slate-400 truncate">
                      {arn}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Loading skeleton ──────────────────────────────────────────────────────────

function Skeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-slate-800 bg-slate-900 p-5 h-24" />
        ))}
      </div>
      <div className="rounded-xl border border-slate-800 bg-slate-900 h-64" />
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DriftPage() {
  const [tab, setTab] = useState<Tab>("recurrences");
  const { summary, isLoading: summaryLoading } = useDriftSummary();
  const { recurrences, isLoading: recLoading } = useRecurrences();
  const { signals, isLoading: sigLoading } = useDriftSignals();
  const { clusters, isLoading: cluLoading } = useRootCauseClusters();

  const isLoading = summaryLoading || recLoading || sigLoading || cluLoading;

  if (isLoading) {
    return (
      <div className="flex-1 overflow-auto p-6 lg:p-10 bg-slate-950">
        <div className="flex items-center gap-3 mb-8">
          <GitCompare className="h-6 w-6 text-blue-400" />
          <h1 className="text-xl font-semibold text-white">Drift Detection</h1>
        </div>
        <Skeleton />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto p-6 lg:p-10 bg-slate-950">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <GitCompare className="h-6 w-6 text-blue-400" />
        <h1 className="text-xl font-semibold text-white">Drift Detection</h1>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <SummaryCard
          label="Recurrences"
          value={summary?.recurrence_count ?? 0}
          icon={RefreshCw}
          accent="text-orange-400"
          sub={`${summary?.total_recurred_findings ?? 0} total recurred findings`}
        />
        <SummaryCard
          label="Drift Signals"
          value={summary?.drift_signal_count ?? 0}
          icon={TrendingUp}
          accent="text-yellow-400"
          sub={`${summary?.total_drifted_resources ?? 0} drifted resources`}
        />
        <SummaryCard
          label="Root Cause Clusters"
          value={summary?.root_cause_clusters ?? 0}
          icon={Layers}
          accent="text-purple-400"
        />
        <SummaryCard
          label="Top Cluster"
          value={summary?.top_cluster_pattern ?? "\u2014"}
          icon={GitCompare}
          accent="text-blue-400"
          sub={summary ? `${summary.top_cluster_size} findings` : undefined}
        />
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 mb-6">
        <TabButton
          active={tab === "recurrences"}
          label="Recurrences"
          count={recurrences.length}
          onClick={() => setTab("recurrences")}
        />
        <TabButton
          active={tab === "signals"}
          label="Drift Signals"
          count={signals.length}
          onClick={() => setTab("signals")}
        />
        <TabButton
          active={tab === "clusters"}
          label="Root Cause Clusters"
          count={clusters.length}
          onClick={() => setTab("clusters")}
        />
      </div>

      {/* Tab content */}
      <div className="rounded-xl border border-slate-800 bg-slate-900">
        {tab === "recurrences" && <RecurrencesTab recurrences={recurrences} />}
        {tab === "signals" && <DriftSignalsTab signals={signals} />}
        {tab === "clusters" && <ClustersTab clusters={clusters} />}
      </div>
    </div>
  );
}
