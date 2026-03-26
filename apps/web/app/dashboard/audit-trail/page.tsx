"use client";

import { useState, useMemo } from "react";
import {
  ClipboardList, Search, Download, ChevronDown, ChevronRight,
  Filter, Clock, User, Zap, Shield, AlertTriangle, CheckCircle2,
} from "lucide-react";
import {
  useSimulationAuditTrail,
  type AuditEntry,
} from "@/lib/hooks/use-audit-trail";
import { useSimulations } from "@/lib/hooks/use-simulations";
import { Spinner } from "@/components/ui/spinner";

// ── Constants ────────────────────────────────────────────────────────────────

const EVENT_TYPE_COLORS: Record<string, string> = {
  simulation: "bg-blue-600/20 text-blue-400 border-blue-500/30",
  agent:      "bg-purple-600/20 text-purple-400 border-purple-500/30",
  gate:       "bg-emerald-600/20 text-emerald-400 border-emerald-500/30",
  error:      "bg-red-600/20 text-red-400 border-red-500/30",
  system:     "bg-slate-600/20 text-slate-400 border-slate-500/30",
  security:   "bg-orange-600/20 text-orange-400 border-orange-500/30",
};

const EVENT_TYPE_ICONS: Record<string, typeof Zap> = {
  simulation: Zap,
  agent:      User,
  gate:       Shield,
  error:      AlertTriangle,
  system:     Clock,
  security:   Shield,
};

const ALL_EVENT_TYPES = ["simulation", "agent", "gate", "error", "system", "security"];

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmtDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function AuditTrailPage() {
  const { runs, isLoading: runsLoading } = useSimulations();
  const [selectedRunId, setSelectedRunId] = useState("");
  const [expandedEntries, setExpandedEntries] = useState<Set<string>>(new Set());
  const [enabledTypes, setEnabledTypes] = useState<Set<string>>(new Set(ALL_EVENT_TYPES));
  const [searchTerm, setSearchTerm] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  const { entries, isLoading: entriesLoading } = useSimulationAuditTrail(selectedRunId);

  // Filter + search
  const filteredEntries = useMemo(() => {
    let result = entries.filter((e) => enabledTypes.has(e.event_type));
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      result = result.filter(
        (e) =>
          e.action.toLowerCase().includes(q) ||
          e.actor.toLowerCase().includes(q) ||
          e.event_type.toLowerCase().includes(q)
      );
    }
    return result;
  }, [entries, enabledTypes, searchTerm]);

  function toggleExpand(id: string) {
    setExpandedEntries((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function toggleEventType(t: string) {
    setEnabledTypes((prev) => {
      const next = new Set(prev);
      next.has(t) ? next.delete(t) : next.add(t);
      return next;
    });
  }

  function handleExport() {
    const lines = filteredEntries.map(
      (e) => `${e.created_at}\t${e.event_type}\t${e.actor}\t${e.action}`
    );
    const blob = new Blob(["Timestamp\tType\tActor\tAction\n" + lines.join("\n")], {
      type: "text/tab-separated-values",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-trail-${selectedRunId || "all"}.tsv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // Recent completed/running runs for selector
  const recentRuns = (runs ?? [])
    .filter((r: any) => r.status === "completed" || r.status === "running")
    .slice(0, 50);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ClipboardList className="h-6 w-6 text-blue-400" />
          <h1 className="text-xl font-semibold text-white">Simulation Audit Trail</h1>
        </div>
        <button
          onClick={handleExport}
          disabled={filteredEntries.length === 0}
          className="flex items-center gap-2 rounded-lg bg-slate-700 px-4 py-2 text-sm text-slate-200 hover:bg-slate-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <Download className="h-4 w-4" />
          Export Report
        </button>
      </div>

      {/* Simulation Selector + Search */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        {/* Run selector */}
        <div className="relative flex-1 max-w-xs">
          <select
            value={selectedRunId}
            onChange={(e) => setSelectedRunId(e.target.value)}
            className="w-full appearance-none rounded-lg border border-slate-700 bg-slate-800 px-4 py-2.5 pr-10 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
          >
            <option value="">Select a simulation run...</option>
            {recentRuns.map((r: any) => (
              <option key={r.id} value={r.id}>
                {r.domain} — {r.status} — {new Date(r.created_at).toLocaleDateString()}
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-slate-500" />
        </div>

        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search actions..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-800 py-2.5 pl-10 pr-4 text-sm text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
          />
        </div>

        {/* Filter toggle */}
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
        >
          <Filter className="h-4 w-4" />
          Filters
          {enabledTypes.size < ALL_EVENT_TYPES.length && (
            <span className="ml-1 rounded-full bg-blue-600 px-1.5 py-0.5 text-[10px] text-white">
              {enabledTypes.size}
            </span>
          )}
        </button>
      </div>

      {/* Event type filters */}
      {showFilters && (
        <div className="flex flex-wrap gap-3 rounded-lg border border-slate-700 bg-slate-800/50 p-4">
          <span className="text-xs font-medium text-slate-400 mr-2 self-center">Event Types:</span>
          {ALL_EVENT_TYPES.map((t) => (
            <label key={t} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={enabledTypes.has(t)}
                onChange={() => toggleEventType(t)}
                className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
              />
              <span className="text-sm capitalize text-slate-300">{t}</span>
            </label>
          ))}
        </div>
      )}

      {/* Content */}
      {!selectedRunId ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-slate-700 bg-slate-800/30 py-20">
          <ClipboardList className="h-10 w-10 text-slate-600 mb-3" />
          <p className="text-sm text-slate-400">Select a simulation run to view its audit trail</p>
        </div>
      ) : entriesLoading ? (
        <div className="flex justify-center py-20">
          <Spinner />
        </div>
      ) : filteredEntries.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-slate-700 bg-slate-800/30 py-20">
          <p className="text-sm text-slate-400">No audit entries found</p>
        </div>
      ) : (
        <div className="space-y-1">
          {filteredEntries.map((entry) => {
            const isExpanded = expandedEntries.has(entry.id);
            const colorCls = EVENT_TYPE_COLORS[entry.event_type] ?? EVENT_TYPE_COLORS.system;
            const IconCmp = EVENT_TYPE_ICONS[entry.event_type] ?? Clock;

            return (
              <div
                key={entry.id}
                className="rounded-lg border border-slate-700/60 bg-slate-800/50 transition-colors hover:bg-slate-800"
              >
                {/* Entry row */}
                <button
                  onClick={() => entry.details && toggleExpand(entry.id)}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left"
                >
                  {/* Expand icon */}
                  {entry.details ? (
                    isExpanded ? (
                      <ChevronDown className="h-4 w-4 text-slate-500 shrink-0" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-slate-500 shrink-0" />
                    )
                  ) : (
                    <div className="w-4 shrink-0" />
                  )}

                  {/* Timestamp */}
                  <span className="w-44 shrink-0 text-xs text-slate-500 font-mono">
                    {fmtDate(entry.created_at)}
                  </span>

                  {/* Event type badge */}
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium capitalize shrink-0 ${colorCls}`}
                  >
                    <IconCmp className="h-3 w-3" />
                    {entry.event_type}
                  </span>

                  {/* Actor badge */}
                  <span className="rounded bg-slate-700 px-2 py-0.5 text-[11px] font-medium text-slate-300 shrink-0">
                    {entry.actor}
                  </span>

                  {/* Action */}
                  <span className="flex-1 truncate text-sm text-slate-200">
                    {entry.action}
                  </span>
                </button>

                {/* Expanded details */}
                {isExpanded && entry.details && (
                  <div className="border-t border-slate-700/50 px-4 py-3 ml-11">
                    <pre className="overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-300 font-mono leading-relaxed">
                      {JSON.stringify(entry.details, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Footer count */}
      {selectedRunId && !entriesLoading && filteredEntries.length > 0 && (
        <p className="text-xs text-slate-500 text-right">
          Showing {filteredEntries.length} of {entries.length} events
        </p>
      )}
    </div>
  );
}
