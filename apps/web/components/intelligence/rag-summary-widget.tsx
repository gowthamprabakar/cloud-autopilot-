"use client";
import Link from "next/link";
import { useIntelligenceSummary } from "@/lib/hooks/use-intelligence";
import { Spinner } from "@/components/ui/spinner";

export default function RagSummaryWidget() {
  const { data, isLoading, error } = useIntelligenceSummary();

  if (isLoading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-4 flex items-center justify-center">
        <Spinner className="h-5 w-5" />
      </div>
    );
  }

  if (error || !data) return null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Security Intelligence</h3>
        <span className="text-xs text-slate-400">{data.total_analyzed} analysed</span>
      </div>

      <div className="grid grid-cols-3 gap-2 mb-3">
        {/* RED */}
        <div className="flex flex-col items-center rounded-lg bg-red-50 border border-red-100 py-2 px-1">
          <span className="text-2xl font-black text-red-600">{data.rag_counts.RED}</span>
          <span className="text-xs text-red-700 font-medium text-center leading-tight mt-0.5">Critical</span>
        </div>
        {/* AMBER */}
        <div className="flex flex-col items-center rounded-lg bg-amber-50 border border-amber-100 py-2 px-1">
          <span className="text-2xl font-black text-amber-600">{data.rag_counts.AMBER}</span>
          <span className="text-xs text-amber-700 font-medium text-center leading-tight mt-0.5">High Priority</span>
        </div>
        {/* GREEN */}
        <div className="flex flex-col items-center rounded-lg bg-green-50 border border-green-100 py-2 px-1">
          <span className="text-2xl font-black text-green-600">{data.rag_counts.GREEN}</span>
          <span className="text-xs text-green-700 font-medium text-center leading-tight mt-0.5">Low Priority</span>
        </div>
      </div>

      {/* Top RED findings */}
      {data.top_red_findings.length > 0 && (
        <ul className="space-y-1 mb-3">
          {data.top_red_findings.slice(0, 3).map((f) => (
            <li key={f.finding_id} className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-red-500 shrink-0" />
              <Link
                href={`/dashboard/findings/${f.finding_id}` as any}
                className="text-xs text-slate-700 hover:text-blue-600 hover:underline truncate"
              >
                {f.title}
              </Link>
              <span className="text-xs text-slate-400 shrink-0">{f.sla_days}d SLA</span>
            </li>
          ))}
        </ul>
      )}

      <Link
        href={"/dashboard/findings" as any}
        className="text-xs font-medium text-blue-600 hover:underline"
      >
        View Security Intelligence →
      </Link>
    </div>
  );
}
