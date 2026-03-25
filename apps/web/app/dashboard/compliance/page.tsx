"use client";
import { useComplianceStats } from "@/lib/hooks/use-compliance";
import { Spinner } from "@/components/ui/spinner";

export default function CompliancePage() {
  const { stats, isLoading } = useComplianceStats();

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Compliance</h1>
        <p className="text-sm text-slate-500 mt-0.5">Framework coverage based on active findings</p>
      </div>

      {isLoading ? (
        <div className="flex justify-center p-12"><Spinner className="h-6 w-6" /></div>
      ) : !stats?.frameworks?.length ? (
        <div className="rounded-xl border border-slate-200 bg-white p-12 text-center">
          <p className="text-sm text-slate-500">No compliance data yet. Sync your AWS accounts to populate compliance mappings.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {stats.frameworks.map((fw) => (
            <div key={fw.framework_id} className="rounded-xl border border-slate-200 bg-white p-5">
              <h3 className="font-semibold text-slate-900">{fw.display_name}</h3>
              <p className="text-xs text-slate-400 mt-0.5">{fw.framework_id}</p>

              <div className="mt-4 flex items-end gap-4">
                <div>
                  <p className="text-2xl font-bold text-slate-900">{fw.coverage_pct.toFixed(0)}%</p>
                  <p className="text-xs text-slate-400">Coverage</p>
                </div>
                <div>
                  <p className="text-lg font-semibold text-green-600">{fw.passing}</p>
                  <p className="text-xs text-slate-400">Passing</p>
                </div>
                <div>
                  <p className="text-lg font-semibold text-red-500">{fw.failing}</p>
                  <p className="text-xs text-slate-400">Failing</p>
                </div>
              </div>

              <div className="mt-3 bg-slate-100 rounded-full h-2">
                <div
                  className="h-2 rounded-full bg-green-500 transition-all"
                  style={{ width: `${fw.coverage_pct}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
