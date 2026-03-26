"use client";

import { useState } from "react";
import { Shield, Server, Package, Lock } from "lucide-react";
import { useModuleEndpoint } from "@/lib/hooks/use-module-data";
import { cn } from "@/lib/utils";

// ── Data hooks ───────────────────────────────────────────────────────────────

function useCwppData() {
  const workloads = useModuleEndpoint("cwpp", "workloads");
  const sbom = useModuleEndpoint("cwpp", "sbom");
  const runtime = useModuleEndpoint("cwpp", "runtime");
  return { workloads, sbom, runtime };
}

// ── Types ────────────────────────────────────────────────────────────────────

interface Workload {
  id: string;
  type: "VM" | "Container" | "Serverless";
  name: string;
  cveCount: number;
  riskScore: number;
  status: "Protected" | "At Risk" | "Unmonitored";
}

interface SbomPackage {
  id: string;
  name: string;
  version: string;
  ecosystem: string;
  cves: string[];
  severity: "Critical" | "High" | "Medium" | "Low";
}

interface RuntimeDomain {
  id: string;
  name: string;
  description: string;
  passRate: number;
  total: number;
  passed: number;
}

// ── Fallback data ────────────────────────────────────────────────────────────

const FALLBACK_WORKLOADS: Workload[] = [
  { id: "1", type: "VM", name: "prod-api-us-east-1a", cveCount: 12, riskScore: 78, status: "At Risk" },
  { id: "2", type: "Container", name: "frontend-nginx:1.25", cveCount: 3, riskScore: 34, status: "Protected" },
  { id: "3", type: "Serverless", name: "lambda-auth-handler", cveCount: 0, riskScore: 12, status: "Protected" },
  { id: "4", type: "VM", name: "staging-db-primary", cveCount: 27, riskScore: 92, status: "At Risk" },
  { id: "5", type: "Container", name: "payment-svc:3.4.1", cveCount: 8, riskScore: 65, status: "At Risk" },
  { id: "6", type: "Serverless", name: "lambda-image-resize", cveCount: 1, riskScore: 18, status: "Protected" },
  { id: "7", type: "VM", name: "prod-worker-pool-3", cveCount: 5, riskScore: 45, status: "Protected" },
  { id: "8", type: "Container", name: "redis-cache:7.2", cveCount: 0, riskScore: 8, status: "Protected" },
];

const FALLBACK_SBOM: SbomPackage[] = [
  { id: "1", name: "lodash", version: "4.17.20", ecosystem: "npm", cves: ["CVE-2021-23337"], severity: "High" },
  { id: "2", name: "log4j-core", version: "2.14.1", ecosystem: "maven", cves: ["CVE-2021-44228", "CVE-2021-45046"], severity: "Critical" },
  { id: "3", name: "openssl", version: "1.1.1k", ecosystem: "system", cves: ["CVE-2022-0778"], severity: "High" },
  { id: "4", name: "requests", version: "2.25.1", ecosystem: "pip", cves: ["CVE-2023-32681"], severity: "Medium" },
  { id: "5", name: "spring-web", version: "5.3.17", ecosystem: "maven", cves: ["CVE-2022-22965"], severity: "Critical" },
  { id: "6", name: "golang.org/x/text", version: "0.3.7", ecosystem: "go", cves: ["CVE-2022-32149"], severity: "Medium" },
];

const FALLBACK_RUNTIME: RuntimeDomain[] = [
  { id: "1", name: "Container Image Security", description: "Image signing, vulnerability scanning, base image compliance", passRate: 87, total: 15, passed: 13 },
  { id: "2", name: "Container Runtime", description: "Privileged mode, root access, capabilities, seccomp profiles", passRate: 73, total: 22, passed: 16 },
  { id: "3", name: "Serverless Configuration", description: "Function timeout, memory limits, concurrency, IAM roles", passRate: 91, total: 11, passed: 10 },
  { id: "4", name: "Network Segmentation", description: "VPC isolation, security groups, network policies, egress rules", passRate: 68, total: 19, passed: 13 },
  { id: "5", name: "Secrets Management", description: "Env var secrets, mounted volumes, KMS encryption, rotation", passRate: 82, total: 16, passed: 13 },
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

// ── Status badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    "Protected": "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    "At Risk": "bg-red-500/10 text-red-400 border-red-500/20",
    "Unmonitored": "bg-slate-600/10 text-slate-400 border-slate-600/20",
  };
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium", styles[status] ?? styles["Unmonitored"])}>
      {status}
    </span>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const styles: Record<string, string> = {
    Critical: "bg-red-500/10 text-red-400 border-red-500/20",
    High: "bg-orange-500/10 text-orange-400 border-orange-500/20",
    Medium: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    Low: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  };
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium", styles[severity] ?? styles.Low)}>
      {severity}
    </span>
  );
}

// ── Tab content ──────────────────────────────────────────────────────────────

const TABS = ["Workloads", "SBOM Analysis", "Runtime Security"] as const;
type Tab = (typeof TABS)[number];

// ── Main page ────────────────────────────────────────────────────────────────

export default function CwppPage() {
  const { workloads, sbom, runtime } = useCwppData();
  const [activeTab, setActiveTab] = useState<Tab>("Workloads");

  const workloadList: Workload[] = (workloads.data as any)?.items ?? FALLBACK_WORKLOADS;
  const sbomList: SbomPackage[] = (sbom.data as any)?.items ?? FALLBACK_SBOM;
  const runtimeDomains: RuntimeDomain[] = (runtime.data as any)?.domains ?? FALLBACK_RUNTIME;

  const totalWorkloads = workloadList.length;
  const criticalCves = sbomList.filter((p) => p.severity === "Critical").reduce((s, p) => s + p.cves.length, 0);
  const malwareIndicators = workloadList.filter((w) => w.riskScore > 75).length;
  const protectionScore = Math.round(
    (workloadList.filter((w) => w.status === "Protected").length / Math.max(totalWorkloads, 1)) * 100
  );

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-900 min-h-screen">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Shield className="h-6 w-6 text-blue-400" />
        <div>
          <h1 className="text-xl font-bold text-white">Cloud Workload Protection Platform</h1>
          <p className="text-sm text-slate-400 mt-0.5">VM, container &amp; serverless vulnerability assessment and runtime security</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard icon={Server} label="Total Workloads" value={totalWorkloads} accent="bg-blue-600/80" />
        <SummaryCard icon={Shield} label="Critical CVEs" value={criticalCves} accent="bg-red-600/80" />
        <SummaryCard icon={Lock} label="Malware Indicators" value={malwareIndicators} accent="bg-orange-600/80" />
        <SummaryCard icon={Package} label="Protection Score" value={`${protectionScore}%`} accent="bg-emerald-600/80" />
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

      {/* Workloads Tab */}
      {activeTab === "Workloads" && (
        <div className="rounded-xl border border-slate-700 bg-slate-800/40 overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-800/80 text-slate-400 text-xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3 text-center">CVE Count</th>
                <th className="px-4 py-3 text-center">Risk Score</th>
                <th className="px-4 py-3 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {workloadList.map((w) => (
                <tr key={w.id} className="hover:bg-slate-800/60 transition-colors">
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-300 bg-slate-700/50 rounded px-2 py-0.5">
                      {w.type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-white font-medium">{w.name}</td>
                  <td className="px-4 py-3 text-center text-slate-300">{w.cveCount}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={cn("font-semibold", w.riskScore > 75 ? "text-red-400" : w.riskScore > 40 ? "text-yellow-400" : "text-emerald-400")}>
                      {w.riskScore}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center"><StatusBadge status={w.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* SBOM Tab */}
      {activeTab === "SBOM Analysis" && (
        <div className="rounded-xl border border-slate-700 bg-slate-800/40 overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-800/80 text-slate-400 text-xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Package</th>
                <th className="px-4 py-3">Version</th>
                <th className="px-4 py-3">Ecosystem</th>
                <th className="px-4 py-3">CVEs</th>
                <th className="px-4 py-3 text-center">Severity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {sbomList.map((pkg) => (
                <tr key={pkg.id} className="hover:bg-slate-800/60 transition-colors">
                  <td className="px-4 py-3 text-white font-medium">{pkg.name}</td>
                  <td className="px-4 py-3 text-slate-300 font-mono text-xs">{pkg.version}</td>
                  <td className="px-4 py-3 text-slate-400">{pkg.ecosystem}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {pkg.cves.map((cve) => (
                        <span key={cve} className="text-xs font-mono text-red-400 bg-red-500/10 rounded px-1.5 py-0.5">{cve}</span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center"><SeverityBadge severity={pkg.severity} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Runtime Security Tab */}
      {activeTab === "Runtime Security" && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {runtimeDomains.map((domain) => {
            const passColor = domain.passRate >= 85 ? "text-emerald-400" : domain.passRate >= 70 ? "text-yellow-400" : "text-red-400";
            const barColor = domain.passRate >= 85 ? "bg-emerald-500" : domain.passRate >= 70 ? "bg-yellow-500" : "bg-red-500";
            return (
              <div key={domain.id} className="rounded-xl border border-slate-700 bg-slate-800/50 p-5 flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white">{domain.name}</h3>
                  <span className={cn("text-lg font-bold", passColor)}>{domain.passRate}%</span>
                </div>
                <p className="text-xs text-slate-400">{domain.description}</p>
                <div className="w-full h-2 rounded-full bg-slate-700 overflow-hidden">
                  <div className={cn("h-full rounded-full transition-all", barColor)} style={{ width: `${domain.passRate}%` }} />
                </div>
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span>{domain.passed}/{domain.total} checks passed</span>
                  <span>{domain.total - domain.passed} failed</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
