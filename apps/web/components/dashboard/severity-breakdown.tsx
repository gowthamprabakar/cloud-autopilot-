"use client";
import type { FindingStats } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";

interface Props {
  stats: FindingStats | undefined;
  isLoading: boolean;
}

const SEVERITIES = ["critical", "high", "medium", "low", "info"] as const;

export function SeverityBreakdown({ stats, isLoading }: Props) {
  if (isLoading) return <div className="flex justify-center p-8"><Spinner className="h-6 w-6" /></div>;
  if (!stats) return null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <h3 className="text-sm font-semibold text-slate-900 mb-4">Findings by Severity</h3>
      <div className="space-y-3">
        {SEVERITIES.map((sev) => {
          const count = stats.by_severity[sev] ?? 0;
          const total = stats.total || 1;
          const pct = Math.round((count / total) * 100);
          return (
            <div key={sev} className="flex items-center gap-3">
              <Badge variant={sev} className="w-16 justify-center capitalize">{sev}</Badge>
              <div className="flex-1 bg-slate-100 rounded-full h-1.5">
                <div
                  className={`h-1.5 rounded-full ${
                    sev === "critical" ? "bg-red-500" :
                    sev === "high" ? "bg-orange-500" :
                    sev === "medium" ? "bg-amber-500" :
                    sev === "low" ? "bg-lime-500" : "bg-gray-400"
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-sm font-medium text-slate-700 w-8 text-right">{count}</span>
            </div>
          );
        })}
      </div>
      <p className="mt-4 text-xs text-slate-400">{stats.total} total open findings</p>
    </div>
  );
}
