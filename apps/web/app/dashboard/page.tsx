"use client";
import { useFindingStats } from "@/lib/hooks/use-findings";
import { useAccounts } from "@/lib/hooks/use-accounts";
import { useComplianceStats } from "@/lib/hooks/use-compliance";
import { SeverityBreakdown } from "@/components/dashboard/severity-breakdown";
import { StatsCard } from "@/components/dashboard/stats-card";
import { Spinner } from "@/components/ui/spinner";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { OnboardingBanner } from "@/components/onboarding/onboarding-banner";
import RagSummaryWidget from "@/components/intelligence/rag-summary-widget";

export default function DashboardPage() {
  const { stats, isLoading: statsLoading } = useFindingStats();
  const { accounts, isLoading: accountsLoading } = useAccounts();
  const { stats: compliance, isLoading: complianceLoading } = useComplianceStats();

  const activeAccounts = accounts?.filter(a => a.status === "active").length ?? 0;
  const totalAccounts = accounts?.length ?? 0;
  const criticalCount = stats?.by_severity?.critical ?? 0;
  const highCount = stats?.by_severity?.high ?? 0;

  return (
    <div className="space-y-6">
      <OnboardingBanner />

      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">Security Overview</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Your AWS cloud security posture at a glance
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          label="Total Findings"
          value={statsLoading ? "—" : stats?.total ?? 0}
          description="Open findings"
        />
        <StatsCard
          label="Critical + High"
          value={statsLoading ? "—" : criticalCount + highCount}
          description="Needs immediate attention"
        />
        <StatsCard
          label="AWS Accounts"
          value={accountsLoading ? "—" : `${activeAccounts}/${totalAccounts}`}
          description="Active / total connected"
        />
        <StatsCard
          label="Compliance Frameworks"
          value={complianceLoading ? "—" : compliance?.frameworks?.length ?? 0}
          description="Tracked frameworks"
        />
      </div>

      {/* Main content: severity breakdown + accounts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SeverityBreakdown stats={stats} isLoading={statsLoading} />

        {/* AWS Accounts Quick View */}
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-slate-900">AWS Accounts</h3>
            <Link href="/dashboard/accounts" className="text-xs text-blue-600 hover:underline">
              Manage →
            </Link>
          </div>
          {accountsLoading ? (
            <div className="flex justify-center p-4"><Spinner className="h-5 w-5" /></div>
          ) : !accounts?.length ? (
            <div className="text-center py-6">
              <p className="text-sm text-slate-500">No AWS accounts connected yet.</p>
              <Link href="/dashboard/accounts" className="mt-2 inline-block text-sm text-blue-600 hover:underline">
                Connect your first account →
              </Link>
            </div>
          ) : (
            <div className="space-y-2">
              {accounts.slice(0, 5).map((account) => (
                <div key={account.id} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                  <div>
                    <p className="text-sm font-medium text-slate-800">{account.account_alias ?? account.account_id}</p>
                    <p className="text-xs text-slate-400">{account.account_id}</p>
                  </div>
                  <Badge variant={account.status as any}>{account.status}</Badge>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Security Intelligence RAG summary */}
      <RagSummaryWidget />

      {/* Compliance overview */}
      {!complianceLoading && compliance?.frameworks?.length ? (
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">Compliance Frameworks</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {compliance.frameworks.map((fw) => (
              <div key={fw.framework_id} className="rounded-lg border border-slate-100 p-3">
                <p className="text-xs font-medium text-slate-700">{fw.display_name}</p>
                <p className="mt-1 text-lg font-bold text-slate-900">{fw.coverage_pct.toFixed(0)}%</p>
                <p className="text-xs text-slate-400">{fw.passing}/{fw.total_controls} passing</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
