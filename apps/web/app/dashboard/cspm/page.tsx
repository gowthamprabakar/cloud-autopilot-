"use client";

import { useState } from "react";
import {
  ShieldCheck, AlertTriangle, CheckCircle2, XCircle,
  BarChart3, FileWarning, ChevronDown, ChevronRight,
} from "lucide-react";
import { useCSPMPosture, type CSPMPosture } from "@/lib/hooks/use-modules";
import { cn } from "@/lib/utils";

// ── Severity badge styles ────────────────────────────────────────────────────

const SEV_BADGE: Record<string, string> = {
  critical: "bg-red-500/10 text-red-400 border border-red-500/20",
  high:     "bg-orange-500/10 text-orange-400 border border-orange-500/20",
  medium:   "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20",
  low:      "bg-blue-500/10 text-blue-400 border border-blue-500/20",
  info:     "bg-slate-500/10 text-slate-400 border border-slate-500/20",
};

// ── Posture Score Gauge ──────────────────────────────────────────────────────

function PostureGauge({ score }: { score: number }) {
  const radius = 70;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color =
    score >= 80 ? "text-emerald-400" :
    score >= 60 ? "text-yellow-400" :
    score >= 40 ? "text-orange-400" : "text-red-400";
  const strokeColor =
    score >= 80 ? "#34d399" :
    score >= 60 ? "#facc15" :
    score >= 40 ? "#fb923c" : "#f87171";

  return (
    <div className="flex flex-col items-center justify-center">
      <svg width="180" height="180" className="-rotate-90">
        <circle cx="90" cy="90" r={radius} fill="none" stroke="#334155" strokeWidth="12" />
        <circle
          cx="90" cy="90" r={radius} fill="none"
          stroke={strokeColor} strokeWidth="12"
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-700"
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className={cn("text-4xl font-bold", color)}>{score}%</span>
        <span className="text-xs text-slate-400 mt-1">Posture Score</span>
      </div>
    </div>
  );
}

// ── Progress bar ─────────────────────────────────────────────────────────────

function PassRateBar({ rate }: { rate: number }) {
  const color =
    rate >= 80 ? "bg-emerald-500" :
    rate >= 60 ? "bg-yellow-500" :
    rate >= 40 ? "bg-orange-500" : "bg-red-500";
  return (
    <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
      <div className={cn("h-full rounded-full transition-all duration-500", color)} style={{ width: `${rate}%` }} />
    </div>
  );
}

// ── Framework card ───────────────────────────────────────────────────────────

function FrameworkCard({ name, data }: { name: string; data: { total_controls: number; passed: number; failed: number; score: number } }) {
  const scoreColor =
    data.score >= 80 ? "text-emerald-400" :
    data.score >= 60 ? "text-yellow-400" : "text-red-400";

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-5">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-white">{name}</h4>
        <span className={cn("text-lg font-bold", scoreColor)}>{data.score}%</span>
      </div>
      <PassRateBar rate={data.score} />
      <div className="flex items-center justify-between mt-3 text-xs text-slate-400">
        <span>{data.passed}/{data.total_controls} passed</span>
        <span className="text-red-400">{data.failed} failed</span>
      </div>
    </div>
  );
}

// ── Category card ────────────────────────────────────────────────────────────

function CategoryCard({ name, cat }: { name: string; cat: CSPMPosture["categories"][string] }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-4">
      <button onClick={() => setExpanded(!expanded)} className="w-full text-left">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-medium text-white truncate">{name}</h4>
          {expanded ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-400 mb-2">
          <span>{cat.rules} rules</span>
          <span className="text-emerald-400">{cat.passed} passed</span>
          {cat.failed > 0 && (
            <span className="inline-flex items-center gap-1 rounded-full bg-red-500/10 text-red-400 border border-red-500/20 px-2 py-0.5 text-xs font-medium">
              {cat.failed} failed
            </span>
          )}
        </div>
        <PassRateBar rate={cat.pass_rate} />
      </button>
      {expanded && cat.findings.length > 0 && (
        <div className="mt-3 space-y-2 border-t border-slate-700 pt-3">
          {cat.findings.slice(0, 5).map((f) => (
            <div key={f.id} className="flex items-start gap-2 text-xs">
              <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-medium capitalize", SEV_BADGE[f.severity] ?? SEV_BADGE.info)}>
                {f.severity}
              </span>
              <span className="text-slate-300 truncate flex-1">{f.title}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Skeleton loader ──────────────────────────────────────────────────────────

function Skeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-48 bg-slate-800 rounded-xl" />
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {Array.from({ length: 10 }).map((_, i) => <div key={i} className="h-28 bg-slate-800 rounded-xl" />)}
      </div>
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function CSPMPage() {
  const { posture, isLoading, error } = useCSPMPosture();

  if (isLoading) return <div className="p-6"><Skeleton /></div>;
  if (error) return <div className="p-6 text-red-400">Failed to load CSPM posture data.</div>;
  if (!posture) return <div className="p-6 text-slate-400">No CSPM data available.</div>;

  const categories = Object.entries(posture.categories);
  const frameworks = Object.entries(posture.frameworks);

  // Flatten all findings for the top-findings table
  const allFindings = categories.flatMap(([cat, data]) =>
    data.findings.map((f) => ({ ...f, category: cat }))
  );

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <ShieldCheck className="h-6 w-6 text-blue-400" />
        <h1 className="text-xl font-bold text-white">CSPM Posture Dashboard</h1>
      </div>

      {/* Top stats row */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Posture gauge */}
        <div className="lg:col-span-1 flex items-center justify-center rounded-xl border border-slate-700 bg-slate-800/50 p-6 relative">
          <PostureGauge score={posture.posture_score} />
        </div>

        {/* Summary cards */}
        <div className="lg:col-span-3 grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard icon={BarChart3} label="Total Rules" value={posture.total_rules} color="text-blue-400" />
          <StatCard icon={CheckCircle2} label="Passed" value={posture.total_passed} color="text-emerald-400" />
          <StatCard icon={XCircle} label="Failed" value={posture.total_failed} color="text-red-400" />
          <StatCard icon={FileWarning} label="Open Findings" value={posture.open_findings} color="text-orange-400" />
        </div>
      </div>

      {/* Category breakdown */}
      <section>
        <h2 className="text-base font-semibold text-white mb-4">Category Breakdown</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {categories.map(([name, cat]) => (
            <CategoryCard key={name} name={name} cat={cat} />
          ))}
        </div>
      </section>

      {/* Compliance Frameworks */}
      <section>
        <h2 className="text-base font-semibold text-white mb-4">Compliance Frameworks</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {frameworks.map(([name, data]) => (
            <FrameworkCard key={name} name={name} data={data} />
          ))}
        </div>
      </section>

      {/* Top Findings table */}
      <section>
        <h2 className="text-base font-semibold text-white mb-4">Top Findings</h2>
        <div className="rounded-xl border border-slate-700 bg-slate-800/50 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-left text-xs text-slate-400">
                <th className="px-4 py-3 font-medium">Severity</th>
                <th className="px-4 py-3 font-medium">Title</th>
                <th className="px-4 py-3 font-medium">Resource ARN</th>
                <th className="px-4 py-3 font-medium">Category</th>
              </tr>
            </thead>
            <tbody>
              {allFindings.slice(0, 25).map((f) => (
                <tr key={f.id} className="border-b border-slate-700/50 hover:bg-slate-700/20 transition-colors">
                  <td className="px-4 py-3">
                    <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-medium capitalize", SEV_BADGE[f.severity] ?? SEV_BADGE.info)}>
                      {f.severity}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-200 max-w-xs truncate">{f.title}</td>
                  <td className="px-4 py-3 text-slate-400 max-w-xs truncate font-mono text-xs">{f.resource_arn}</td>
                  <td className="px-4 py-3 text-slate-400">{f.category}</td>
                </tr>
              ))}
              {allFindings.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-slate-500">No findings reported.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

// ── Stat card helper ─────────────────────────────────────────────────────────

function StatCard({ icon: Icon, label, value, color }: { icon: any; label: string; value: number; color: string }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-4 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <Icon className={cn("h-4 w-4", color)} />
        <span className="text-xs text-slate-400">{label}</span>
      </div>
      <span className="text-2xl font-bold text-white">{value.toLocaleString()}</span>
    </div>
  );
}
