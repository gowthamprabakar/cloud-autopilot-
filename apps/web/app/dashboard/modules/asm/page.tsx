"use client";

import { useState } from "react";
import { Globe, Eye, Ghost, AlertTriangle, Radio } from "lucide-react";
import { useModuleEndpoint } from "@/lib/hooks/use-module-data";
import { cn } from "@/lib/utils";

// -- Data hooks ---------------------------------------------------------------

function useAsmData() {
  const exposure = useModuleEndpoint("asm", "exposure");
  const shadow = useModuleEndpoint("asm", "shadow");
  const priorities = useModuleEndpoint("asm", "priorities");
  return { exposure, shadow, priorities };
}

// -- Types --------------------------------------------------------------------

interface ExposedAsset {
  id: string;
  asset: string;
  type: "Domain" | "IP" | "API" | "S3 Bucket" | "Database";
  port: string;
  protocol: string;
  tls: boolean;
  provider: string;
  lastSeen: string;
}

interface ShadowAsset {
  id: string;
  asset: string;
  type: string;
  discoveredVia: "DNS Enum" | "Cert Transparency" | "Port Scan" | "Cloud API" | "OSINT";
  owner: string;
  managed: boolean;
  riskLevel: "Critical" | "High" | "Medium" | "Low";
}

interface PriorityItem {
  id: string;
  asset: string;
  riskScore: number;
  factors: string[];
  exploitable: boolean;
  firstSeen: string;
  recommendation: string;
}

// -- Fallback data ------------------------------------------------------------

const FALLBACK_EXPOSURE: ExposedAsset[] = [
  { id: "1", asset: "api.acme.com", type: "API", port: "443", protocol: "HTTPS", tls: true, provider: "AWS", lastSeen: "2m ago" },
  { id: "2", asset: "52.14.88.201", type: "IP", port: "22", protocol: "SSH", tls: false, provider: "AWS", lastSeen: "5m ago" },
  { id: "3", asset: "staging.acme.com", type: "Domain", port: "80", protocol: "HTTP", tls: false, provider: "GCP", lastSeen: "1h ago" },
  { id: "4", asset: "acme-backup-2024.s3.amazonaws.com", type: "S3 Bucket", port: "443", protocol: "HTTPS", tls: true, provider: "AWS", lastSeen: "12m ago" },
  { id: "5", asset: "db-replica.acme.io", type: "Database", port: "5432", protocol: "PostgreSQL", tls: false, provider: "AWS", lastSeen: "30m ago" },
  { id: "6", asset: "admin-panel.acme.com", type: "Domain", port: "443", protocol: "HTTPS", tls: true, provider: "Azure", lastSeen: "8m ago" },
  { id: "7", asset: "10.0.3.44", type: "IP", port: "3389", protocol: "RDP", tls: false, provider: "Azure", lastSeen: "3h ago" },
];

const FALLBACK_SHADOW: ShadowAsset[] = [
  { id: "1", asset: "dev-test.acme.io", type: "Domain", discoveredVia: "Cert Transparency", owner: "Unknown", managed: false, riskLevel: "Critical" },
  { id: "2", asset: "acme-legacy-api.herokuapp.com", type: "Domain", discoveredVia: "DNS Enum", owner: "Engineering", managed: false, riskLevel: "High" },
  { id: "3", asset: "52.14.92.17", type: "IP", discoveredVia: "Port Scan", owner: "Unknown", managed: false, riskLevel: "High" },
  { id: "4", asset: "acme-logs.s3.amazonaws.com", type: "S3 Bucket", discoveredVia: "Cloud API", owner: "DevOps", managed: false, riskLevel: "Medium" },
  { id: "5", asset: "internal-wiki.acme.com", type: "Domain", discoveredVia: "OSINT", owner: "IT", managed: false, riskLevel: "Medium" },
  { id: "6", asset: "grafana.acme.dev", type: "Domain", discoveredVia: "DNS Enum", owner: "SRE", managed: false, riskLevel: "Low" },
];

const FALLBACK_PRIORITIES: PriorityItem[] = [
  { id: "1", asset: "dev-test.acme.io", riskScore: 96, factors: ["Unmanaged", "No TLS", "Default creds"], exploitable: true, firstSeen: "3d ago", recommendation: "Decommission or onboard to asset inventory" },
  { id: "2", asset: "52.14.88.201:22", riskScore: 91, factors: ["SSH exposed", "Weak cipher"], exploitable: true, firstSeen: "7d ago", recommendation: "Restrict SSH to VPN only" },
  { id: "3", asset: "db-replica.acme.io:5432", riskScore: 88, factors: ["DB exposed", "No TLS", "Public subnet"], exploitable: true, firstSeen: "1d ago", recommendation: "Move to private subnet, enable TLS" },
  { id: "4", asset: "staging.acme.com:80", riskScore: 75, factors: ["HTTP only", "Debug mode"], exploitable: false, firstSeen: "14d ago", recommendation: "Enable HTTPS, disable debug" },
  { id: "5", asset: "acme-backup-2024.s3", riskScore: 72, factors: ["Public listing", "Sensitive data"], exploitable: false, firstSeen: "5d ago", recommendation: "Remove public ACL, enable encryption" },
  { id: "6", asset: "10.0.3.44:3389", riskScore: 68, factors: ["RDP exposed", "Outdated OS"], exploitable: false, firstSeen: "21d ago", recommendation: "Restrict to bastion host" },
];

// -- Reusable components ------------------------------------------------------

function SummaryCard({ icon: Icon, label, value, accent }: {
  icon: React.ElementType; label: string; value: string | number; accent: string;
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

// -- Tabs ---------------------------------------------------------------------

const TABS = ["Exposure Map", "Shadow Assets", "Priority Ranking"] as const;
type Tab = (typeof TABS)[number];

// -- Main page ----------------------------------------------------------------

export default function AsmPage() {
  const { exposure, shadow, priorities } = useAsmData();
  const [activeTab, setActiveTab] = useState<Tab>("Exposure Map");

  const exposureList: ExposedAsset[] = (exposure.data as any)?.items ?? FALLBACK_EXPOSURE;
  const shadowList: ShadowAsset[] = (shadow.data as any)?.items ?? FALLBACK_SHADOW;
  const priorityList: PriorityItem[] = (priorities.data as any)?.items ?? FALLBACK_PRIORITIES;

  const externalAssets = exposureList.length;
  const exposedServices = exposureList.filter((e) => !e.tls || e.protocol === "SSH" || e.protocol === "RDP").length;
  const shadowAssets = shadowList.length;
  const avgRisk = Math.round(priorityList.reduce((s, p) => s + p.riskScore, 0) / Math.max(priorityList.length, 1));

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-900 min-h-screen">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Globe className="h-6 w-6 text-blue-400" />
        <div>
          <h1 className="text-xl font-bold text-white">Attack Surface Management</h1>
          <p className="text-sm text-slate-400 mt-0.5">External asset discovery, shadow IT detection &amp; risk-prioritized remediation</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard icon={Globe} label="External Assets" value={externalAssets} accent="bg-blue-600/80" />
        <SummaryCard icon={Radio} label="Exposed Services" value={exposedServices} accent="bg-red-600/80" />
        <SummaryCard icon={Ghost} label="Shadow Assets" value={shadowAssets} accent="bg-purple-600/80" />
        <SummaryCard icon={AlertTriangle} label="Avg Risk Score" value={avgRisk} accent="bg-orange-600/80" />
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

      {/* Exposure Map Tab */}
      {activeTab === "Exposure Map" && (
        <div className="rounded-xl border border-slate-700 bg-slate-800/40 overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-800/80 text-slate-400 text-xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Asset</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3 text-center">Port</th>
                <th className="px-4 py-3">Protocol</th>
                <th className="px-4 py-3 text-center">TLS</th>
                <th className="px-4 py-3">Provider</th>
                <th className="px-4 py-3">Last Seen</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {exposureList.map((e) => (
                <tr key={e.id} className="hover:bg-slate-800/60 transition-colors">
                  <td className="px-4 py-3 text-white font-medium font-mono text-xs">{e.asset}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs font-medium text-slate-300 bg-slate-700/50 rounded px-2 py-0.5">{e.type}</span>
                  </td>
                  <td className="px-4 py-3 text-center text-slate-300 font-mono text-xs">{e.port}</td>
                  <td className="px-4 py-3 text-slate-300">{e.protocol}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={e.tls ? "text-emerald-400" : "text-red-400 font-semibold"}>{e.tls ? "Yes" : "No"}</span>
                  </td>
                  <td className="px-4 py-3 text-slate-400">{e.provider}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{e.lastSeen}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Shadow Assets Tab */}
      {activeTab === "Shadow Assets" && (
        <div className="rounded-xl border border-slate-700 bg-slate-800/40 overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-800/80 text-slate-400 text-xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Asset</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Discovered Via</th>
                <th className="px-4 py-3">Owner</th>
                <th className="px-4 py-3 text-center">Managed</th>
                <th className="px-4 py-3 text-center">Risk Level</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {shadowList.map((s) => (
                <tr key={s.id} className="hover:bg-slate-800/60 transition-colors">
                  <td className="px-4 py-3 text-white font-medium font-mono text-xs">{s.asset}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs font-medium text-slate-300 bg-slate-700/50 rounded px-2 py-0.5">{s.type}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs font-medium bg-slate-700/50 text-slate-300 rounded px-2 py-0.5 border border-slate-600/30">{s.discoveredVia}</span>
                  </td>
                  <td className="px-4 py-3 text-slate-300">{s.owner}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={s.managed ? "text-emerald-400" : "text-red-400 font-semibold"}>{s.managed ? "Yes" : "No"}</span>
                  </td>
                  <td className="px-4 py-3 text-center"><RiskBadge level={s.riskLevel} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Priority Ranking Tab */}
      {activeTab === "Priority Ranking" && (
        <div className="space-y-3">
          {priorityList.map((p, idx) => {
            const barColor = p.riskScore > 85 ? "bg-red-500" : p.riskScore > 70 ? "bg-orange-500" : "bg-yellow-500";
            const textColor = p.riskScore > 85 ? "text-red-400" : p.riskScore > 70 ? "text-orange-400" : "text-yellow-400";
            return (
              <div key={p.id} className="rounded-xl border border-slate-700 bg-slate-800/50 p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-slate-500 bg-slate-700/50 rounded-full w-7 h-7 flex items-center justify-center">#{idx + 1}</span>
                    <span className="text-sm font-semibold text-white font-mono">{p.asset}</span>
                    {p.exploitable && (
                      <span className="inline-flex items-center rounded-full border border-red-500/20 bg-red-500/10 text-red-400 px-2 py-0.5 text-xs font-medium">Exploitable</span>
                    )}
                  </div>
                  <span className={cn("text-lg font-bold", textColor)}>{p.riskScore}</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-700 overflow-hidden">
                  <div className={cn("h-full rounded-full", barColor)} style={{ width: `${p.riskScore}%` }} />
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex gap-1.5 flex-wrap">
                    {p.factors.map((f) => (
                      <span key={f} className="text-xs bg-slate-700/50 text-slate-300 rounded px-2 py-0.5 border border-slate-600/30">{f}</span>
                    ))}
                  </div>
                  <span className="text-xs text-slate-500">Found {p.firstSeen}</span>
                </div>
                <p className="text-xs text-slate-400">{p.recommendation}</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
