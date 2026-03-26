"use client";

import { useState } from "react";
import { Shield, Database, Eye, FileWarning } from "lucide-react";
import { useModuleEndpoint } from "@/lib/hooks/use-module-data";
import { cn } from "@/lib/utils";

// ── Data hooks ───────────────────────────────────────────────────────────────

function useDspmData() {
  const classify = useModuleEndpoint("dspm", "classify");
  const exposure = useModuleEndpoint("dspm", "exposure");
  const breachImpact = useModuleEndpoint("dspm", "breach-impact");
  return { classify, exposure, breachImpact };
}

// ── Types ────────────────────────────────────────────────────────────────────

interface DataStore {
  id: string;
  name: string;
  type: "S3" | "RDS" | "DynamoDB";
  classification: "PII" | "PHI" | "PCI" | "Confidential" | "Public";
  encryption: boolean;
  publicAccess: boolean;
  recordCount: number;
}

interface ExposurePath {
  id: string;
  source: string;
  classification: string;
  chain: string[];
  riskLevel: "Critical" | "High" | "Medium" | "Low";
}

interface BreachRecord {
  id: string;
  dataStore: string;
  recordsAtRisk: number;
  estimatedCost: number;
  notificationRequired: boolean;
  regulations: string[];
}

interface RegulatoryCard {
  id: string;
  framework: string;
  description: string;
  score: number;
  controls: number;
  passing: number;
}

// ── Fallback data ────────────────────────────────────────────────────────────

const FALLBACK_STORES: DataStore[] = [
  { id: "1", name: "prod-user-data", type: "S3", classification: "PII", encryption: true, publicAccess: false, recordCount: 2_340_000 },
  { id: "2", name: "healthcare-records", type: "RDS", classification: "PHI", encryption: true, publicAccess: false, recordCount: 890_000 },
  { id: "3", name: "payment-transactions", type: "DynamoDB", classification: "PCI", encryption: true, publicAccess: false, recordCount: 5_600_000 },
  { id: "4", name: "internal-docs-backup", type: "S3", classification: "Confidential", encryption: false, publicAccess: true, recordCount: 45_000 },
  { id: "5", name: "public-assets-cdn", type: "S3", classification: "Public", encryption: false, publicAccess: true, recordCount: 12_000 },
  { id: "6", name: "customer-analytics", type: "RDS", classification: "PII", encryption: true, publicAccess: false, recordCount: 1_100_000 },
  { id: "7", name: "session-store", type: "DynamoDB", classification: "Confidential", encryption: true, publicAccess: false, recordCount: 320_000 },
  { id: "8", name: "hr-employee-data", type: "RDS", classification: "PII", encryption: false, publicAccess: false, recordCount: 15_000 },
];

const FALLBACK_EXPOSURE: ExposurePath[] = [
  { id: "1", source: "prod-user-data (S3)", classification: "PII", chain: ["S3 Bucket", "Misconfigured IAM Role", "Lambda Function", "Public API Gateway"], riskLevel: "Critical" },
  { id: "2", source: "internal-docs-backup (S3)", classification: "Confidential", chain: ["S3 Bucket", "Public ACL", "Internet"], riskLevel: "Critical" },
  { id: "3", source: "healthcare-records (RDS)", classification: "PHI", chain: ["RDS Instance", "Overprivileged EC2", "NAT Gateway", "Internet"], riskLevel: "High" },
  { id: "4", source: "payment-transactions (DynamoDB)", classification: "PCI", chain: ["DynamoDB", "Cross-Account Role", "External Account"], riskLevel: "High" },
  { id: "5", source: "customer-analytics (RDS)", classification: "PII", chain: ["RDS Instance", "Snapshot Public Share"], riskLevel: "Medium" },
];

const FALLBACK_BREACH: BreachRecord[] = [
  { id: "1", dataStore: "prod-user-data", recordsAtRisk: 2_340_000, estimatedCost: 9_828_000, notificationRequired: true, regulations: ["GDPR", "CCPA"] },
  { id: "2", dataStore: "healthcare-records", recordsAtRisk: 890_000, estimatedCost: 8_900_000, notificationRequired: true, regulations: ["HIPAA", "GDPR"] },
  { id: "3", dataStore: "payment-transactions", recordsAtRisk: 5_600_000, estimatedCost: 22_400_000, notificationRequired: true, regulations: ["PCI-DSS", "GDPR"] },
  { id: "4", dataStore: "internal-docs-backup", recordsAtRisk: 45_000, estimatedCost: 189_000, notificationRequired: false, regulations: ["GDPR"] },
  { id: "5", dataStore: "hr-employee-data", recordsAtRisk: 15_000, estimatedCost: 63_000, notificationRequired: true, regulations: ["GDPR", "CCPA"] },
];

const FALLBACK_REGULATORY: RegulatoryCard[] = [
  { id: "1", framework: "GDPR", description: "General Data Protection Regulation - EU data privacy and security", score: 74, controls: 42, passing: 31 },
  { id: "2", framework: "HIPAA", description: "Health Insurance Portability and Accountability Act - PHI safeguards", score: 81, controls: 38, passing: 31 },
  { id: "3", framework: "PCI-DSS", description: "Payment Card Industry Data Security Standard - cardholder data", score: 68, controls: 52, passing: 35 },
  { id: "4", framework: "CCPA", description: "California Consumer Privacy Act - consumer data rights", score: 88, controls: 24, passing: 21 },
];

// ── Summary card ─────────────────────────────────────────────────────────────

function SummaryCard({ icon: Icon, label, value, accent }: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  accent: string;
}) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/60 p-5 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <div className={cn("flex items-center justify-center h-9 w-9 rounded-lg", accent)}>
          <Icon className="h-4.5 w-4.5 text-white" />
        </div>
        <span className="text-xs font-medium text-slate-400">{label}</span>
      </div>
      <span className="text-2xl font-bold text-white">{value}</span>
    </div>
  );
}

// ── Classification badge ─────────────────────────────────────────────────────

function ClassBadge({ classification }: { classification: string }) {
  const styles: Record<string, string> = {
    PII: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    PHI: "bg-red-500/10 text-red-400 border-red-500/20",
    PCI: "bg-orange-500/10 text-orange-400 border-orange-500/20",
    Confidential: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    Public: "bg-slate-600/10 text-slate-400 border-slate-600/20",
  };
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium", styles[classification] ?? styles.Public)}>
      {classification}
    </span>
  );
}

function RiskBadge({ level }: { level: string }) {
  const styles: Record<string, string> = {
    Critical: "bg-red-500/10 text-red-400 border-red-500/20",
    High: "bg-orange-500/10 text-orange-400 border-orange-500/20",
    Medium: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    Low: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  };
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium", styles[level] ?? styles.Low)}>
      {level}
    </span>
  );
}

// ── Tabs ─────────────────────────────────────────────────────────────────────

const TABS = ["Classification", "Exposure Paths", "Breach Impact", "Regulatory"] as const;
type Tab = (typeof TABS)[number];

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatCurrency(n: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
}

function formatNumber(n: number): string {
  return new Intl.NumberFormat("en-US").format(n);
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function DspmPage() {
  const { classify, exposure, breachImpact } = useDspmData();
  const [activeTab, setActiveTab] = useState<Tab>("Classification");

  const storeList: DataStore[] = (classify.data as any)?.items ?? FALLBACK_STORES;
  const exposureList: ExposurePath[] = (exposure.data as any)?.paths ?? FALLBACK_EXPOSURE;
  const breachList: BreachRecord[] = (breachImpact.data as any)?.records ?? FALLBACK_BREACH;
  const regulatoryList: RegulatoryCard[] = (breachImpact.data as any)?.regulatory ?? FALLBACK_REGULATORY;

  const totalStores = storeList.length;
  const sensitiveCount = storeList.filter((s) => s.classification !== "Public").length;
  const exposurePaths = exposureList.length;
  const totalBreachCost = breachList.reduce((sum, b) => sum + b.estimatedCost, 0);

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-900 min-h-screen">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Database className="h-6 w-6 text-blue-400" />
        <div>
          <h1 className="text-xl font-bold text-white">Data Security Posture Management</h1>
          <p className="text-sm text-slate-400 mt-0.5">Sensitive data discovery, exposure tracking &amp; breach impact analysis</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard icon={Database} label="Data Stores" value={totalStores} accent="bg-blue-600/80" />
        <SummaryCard icon={Eye} label="Sensitive Data Found" value={sensitiveCount} accent="bg-purple-600/80" />
        <SummaryCard icon={FileWarning} label="Exposure Paths" value={exposurePaths} accent="bg-red-600/80" />
        <SummaryCard icon={Shield} label="Breach Impact ($)" value={formatCurrency(totalBreachCost)} accent="bg-orange-600/80" />
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-700 flex gap-1">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "px-4 py-2.5 text-sm font-medium transition-colors rounded-t-lg",
              activeTab === tab
                ? "text-blue-400 border-b-2 border-blue-400 bg-slate-800/50"
                : "text-slate-400 hover:text-white hover:bg-slate-800/30"
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Classification Tab */}
      {activeTab === "Classification" && (
        <div className="rounded-xl border border-slate-700 bg-slate-800/40 overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-800/80 text-slate-400 text-xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Store Name</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3 text-center">Classification</th>
                <th className="px-4 py-3 text-center">Encryption</th>
                <th className="px-4 py-3 text-center">Public Access</th>
                <th className="px-4 py-3 text-right">Records</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {storeList.map((store) => (
                <tr key={store.id} className="hover:bg-slate-800/60 transition-colors">
                  <td className="px-4 py-3 text-white font-medium">{store.name}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs font-medium text-slate-300 bg-slate-700/50 rounded px-2 py-0.5">{store.type}</span>
                  </td>
                  <td className="px-4 py-3 text-center"><ClassBadge classification={store.classification} /></td>
                  <td className="px-4 py-3 text-center">
                    <span className={store.encryption ? "text-emerald-400" : "text-red-400"}>{store.encryption ? "Enabled" : "Disabled"}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={store.publicAccess ? "text-red-400 font-semibold" : "text-emerald-400"}>{store.publicAccess ? "Yes" : "No"}</span>
                  </td>
                  <td className="px-4 py-3 text-right text-slate-300 font-mono text-xs">{formatNumber(store.recordCount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Exposure Paths Tab */}
      {activeTab === "Exposure Paths" && (
        <div className="space-y-4">
          {exposureList.map((path) => (
            <div key={path.id} className="rounded-xl border border-slate-700 bg-slate-800/50 p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <h3 className="text-sm font-semibold text-white">{path.source}</h3>
                  <ClassBadge classification={path.classification} />
                </div>
                <RiskBadge level={path.riskLevel} />
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                {path.chain.map((node, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <span className={cn(
                      "text-xs font-medium rounded-lg px-3 py-1.5 border",
                      idx === 0 ? "bg-blue-500/10 text-blue-400 border-blue-500/20" :
                      idx === path.chain.length - 1 ? "bg-red-500/10 text-red-400 border-red-500/20" :
                      "bg-slate-700/50 text-slate-300 border-slate-600/30"
                    )}>
                      {node}
                    </span>
                    {idx < path.chain.length - 1 && <span className="text-slate-600">&#8594;</span>}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Breach Impact Tab */}
      {activeTab === "Breach Impact" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-700 bg-slate-800/40 overflow-hidden">
            <table className="w-full text-sm text-left">
              <thead className="bg-slate-800/80 text-slate-400 text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3">Data Store</th>
                  <th className="px-4 py-3 text-right">Records at Risk</th>
                  <th className="px-4 py-3 text-right">Estimated Cost</th>
                  <th className="px-4 py-3 text-center">Notification Required</th>
                  <th className="px-4 py-3">Regulations</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {breachList.map((record) => (
                  <tr key={record.id} className="hover:bg-slate-800/60 transition-colors">
                    <td className="px-4 py-3 text-white font-medium">{record.dataStore}</td>
                    <td className="px-4 py-3 text-right text-slate-300 font-mono text-xs">{formatNumber(record.recordsAtRisk)}</td>
                    <td className="px-4 py-3 text-right text-red-400 font-semibold">{formatCurrency(record.estimatedCost)}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={record.notificationRequired ? "text-red-400 font-semibold" : "text-slate-400"}>
                        {record.notificationRequired ? "Yes" : "No"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1.5 flex-wrap">
                        {record.regulations.map((reg) => (
                          <span key={reg} className="text-xs font-medium bg-slate-700/50 text-slate-300 rounded px-2 py-0.5 border border-slate-600/30">{reg}</span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-5">
            <h3 className="text-sm font-semibold text-white mb-2">Total Breach Impact Summary</h3>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-2xl font-bold text-red-400">{formatCurrency(totalBreachCost)}</p>
                <p className="text-xs text-slate-400 mt-1">Total Estimated Cost</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-orange-400">{formatNumber(breachList.reduce((s, b) => s + b.recordsAtRisk, 0))}</p>
                <p className="text-xs text-slate-400 mt-1">Total Records at Risk</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-yellow-400">{breachList.filter((b) => b.notificationRequired).length}</p>
                <p className="text-xs text-slate-400 mt-1">Notification Requirements</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Regulatory Tab */}
      {activeTab === "Regulatory" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {regulatoryList.map((reg) => {
            const scoreColor = reg.score >= 85 ? "text-emerald-400" : reg.score >= 70 ? "text-yellow-400" : "text-red-400";
            const barColor = reg.score >= 85 ? "bg-emerald-500" : reg.score >= 70 ? "bg-yellow-500" : "bg-red-500";
            return (
              <div key={reg.id} className="rounded-xl border border-slate-700 bg-slate-800/50 p-5 flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-semibold text-white">{reg.framework}</h3>
                  <span className={cn("text-2xl font-bold", scoreColor)}>{reg.score}%</span>
                </div>
                <p className="text-xs text-slate-400">{reg.description}</p>
                <div className="w-full h-2 rounded-full bg-slate-700 overflow-hidden">
                  <div className={cn("h-full rounded-full transition-all", barColor)} style={{ width: `${reg.score}%` }} />
                </div>
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span>{reg.passing}/{reg.controls} controls passing</span>
                  <span>{reg.controls - reg.passing} failing</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
