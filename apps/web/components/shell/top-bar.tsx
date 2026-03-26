"use client";

import useSWR from "swr";
import StatusIndicator, { type StatusLevel } from "../ui/status-indicator";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
interface InfraMetrics {
  agents_active: number;
  messages_total: number;
  solutions_count: number;
  gates_passed: number;
  runs_completed: number;
  domains_covered: number;
  overall_progress: number; // 0-100
  status: StatusLevel;
}

const FALLBACK: InfraMetrics = {
  agents_active: 0,
  messages_total: 0,
  solutions_count: 0,
  gates_passed: 0,
  runs_completed: 0,
  domains_covered: 0,
  overall_progress: 0,
  status: "standby",
};

/* ------------------------------------------------------------------ */
/*  SWR fetcher                                                        */
/* ------------------------------------------------------------------ */
const fetcher = (url: string): Promise<InfraMetrics> =>
  fetch(url, { credentials: "include" })
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then((raw: any) => ({
      agents_active: raw?.agents?.total_executions ?? 0,
      messages_total: raw?.communication?.total_messages ?? 0,
      solutions_count: raw?.simulations?.completed ?? 0,
      gates_passed: raw?.gates?.passed ?? 0,
      runs_completed: raw?.simulations?.total ?? 0,
      domains_covered: 17,
      overall_progress: raw?.simulations?.avg_confidence ?? 0,
      status: (raw?.simulations?.total ?? 0) > 0 ? "certified" as StatusLevel : "standby" as StatusLevel,
    }))
    .catch(() => FALLBACK);

/* ------------------------------------------------------------------ */
/*  Stat pill                                                          */
/* ------------------------------------------------------------------ */
function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex flex-col items-center gap-0.5 px-3">
      <span className="text-base font-bold tabular-nums" style={{ color }}>
        {(value ?? 0).toLocaleString()}
      </span>
      <span className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */
export default function TopBar() {
  const { data } = useSWR<InfraMetrics>("/api/v1/infra/metrics", fetcher, {
    refreshInterval: 30_000,
    fallbackData: FALLBACK,
    revalidateOnFocus: false,
  });

  const m = data ?? FALLBACK;

  const stats: { label: string; value: number; color: string }[] = [
    { label: "Agents", value: m.agents_active, color: "#FF6B35" },
    { label: "Messages", value: m.messages_total, color: "#00D4FF" },
    { label: "Solutions", value: m.solutions_count, color: "#22C55E" },
    { label: "Gates", value: m.gates_passed, color: "#FFD700" },
    { label: "Runs", value: m.runs_completed, color: "#A855F7" },
    { label: "Domains", value: m.domains_covered, color: "#F97316" },
  ];

  return (
    <header className="sticky top-0 z-40 flex items-center justify-between gap-4 px-6 py-2 bg-slate-950 border-b border-slate-800 shadow-lg shadow-black/30">
      {/* Left: brand */}
      <div className="flex items-center gap-3 shrink-0">
        <div className="h-7 w-7 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-[11px] font-bold text-white">
          CC
        </div>
        <span className="text-sm font-semibold text-white tracking-wide hidden sm:inline">
          Cloud Copilot
        </span>
      </div>

      {/* Center: KPI stats */}
      <div className="flex items-center gap-1 overflow-x-auto scrollbar-none">
        {stats.map((s) => (
          <Stat key={s.label} {...s} />
        ))}
      </div>

      {/* Right: progress + status */}
      <div className="flex items-center gap-4 shrink-0">
        {/* Progress bar */}
        <div className="flex items-center gap-2">
          <div className="w-24 h-1.5 rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-blue-500 to-green-400 transition-all duration-700"
              style={{ width: `${Math.min(m.overall_progress, 100)}%` }}
            />
          </div>
          <span className="text-[10px] text-slate-400 tabular-nums w-8 text-right">
            {m.overall_progress}%
          </span>
        </div>

        {/* Status orb */}
        <StatusIndicator status={m.status} label={m.status} />
      </div>
    </header>
  );
}
