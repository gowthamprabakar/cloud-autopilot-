"use client";

import { useState } from "react";
import {
  Brain, KeyRound, DollarSign, Shield, Network,
  AlertTriangle, CheckCircle2, XCircle, Clock,
  Cpu, Lock, Globe, Server,
} from "lucide-react";
import { useModuleEndpoint } from "@/lib/hooks/use-module-data";
import { cn } from "@/lib/utils";

// ── Types ────────────────────────────────────────────────────────────────────

interface CredentialRow {
  id: string;
  service: string;
  key_alias: string;
  privilege_scope: string;
  rotation_status: "rotated" | "overdue" | "pending";
  last_rotated: string;
  exposure_risk: "critical" | "high" | "medium" | "low";
}

interface SpendData {
  service: string;
  baseline: number;
  current: number;
  threshold_exceeded: boolean;
}

interface CanaryStrategy {
  id: string;
  name: string;
  description: string;
  type: "adjacent" | "store" | "internet" | "repo";
  deployed: boolean;
  detections: number;
}

interface VPCRow {
  service: string;
  provider: string;
  routing: "vpc" | "public";
  endpoint_policy: boolean;
  last_audit: string;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const RISK_BADGE: Record<string, string> = {
  critical: "bg-red-500/10 text-red-400 border border-red-500/20",
  high:     "bg-orange-500/10 text-orange-400 border border-orange-500/20",
  medium:   "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20",
  low:      "bg-blue-500/10 text-blue-400 border border-blue-500/20",
};

const ROTATION_BADGE: Record<string, string> = {
  rotated: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  overdue: "bg-red-500/10 text-red-400 border border-red-500/20",
  pending: "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20",
};

// ── Summary Card ─────────────────────────────────────────────────────────────

function SummaryCard({
  label, value, icon: Icon, accent = "text-blue-400", sub,
}: {
  label: string; value: string | number; icon: React.ElementType;
  accent?: string; sub?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5 flex flex-col gap-1">
      <div className="flex items-center gap-2 text-xs text-slate-500 uppercase tracking-wider">
        <Icon className={cn("h-4 w-4", accent)} />
        {label}
      </div>
      <p className="text-2xl font-semibold text-white">{value}</p>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

// ── Tab Button ───────────────────────────────────────────────────────────────

type Tab = "credentials" | "spend" | "canary" | "vpc";

function TabButton({ active, label, onClick }: {
  active: boolean; label: string; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "px-4 py-2 text-sm font-medium rounded-lg transition-colors",
        active
          ? "bg-blue-600/20 text-blue-400"
          : "text-slate-400 hover:text-white hover:bg-slate-800",
      )}
    >
      {label}
    </button>
  );
}

// ── Credential Audit Tab ─────────────────────────────────────────────────────

function CredentialAuditTab({ rows }: { rows: CredentialRow[] }) {
  if (rows.length === 0) {
    return (
      <div className="text-center py-16 text-slate-500">
        <KeyRound className="h-8 w-8 mx-auto mb-3 opacity-40" />
        <p>No AI service credentials found.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-slate-500 uppercase tracking-wider border-b border-slate-800">
            <th className="py-3 px-4">Service</th>
            <th className="py-3 px-4">Key Alias</th>
            <th className="py-3 px-4">Privilege Scope</th>
            <th className="py-3 px-4">Rotation Status</th>
            <th className="py-3 px-4">Last Rotated</th>
            <th className="py-3 px-4">Exposure Risk</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60">
          {rows.map((r) => (
            <tr key={r.id} className="hover:bg-slate-800/40 transition-colors">
              <td className="py-3 px-4">
                <div className="flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-purple-400" />
                  <span className="text-white font-medium">{r.service}</span>
                </div>
              </td>
              <td className="py-3 px-4 text-slate-400 font-mono text-xs">{r.key_alias}</td>
              <td className="py-3 px-4">
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-slate-300">
                  {r.privilege_scope}
                </span>
              </td>
              <td className="py-3 px-4">
                <span className={cn("text-xs px-2 py-0.5 rounded-full capitalize", ROTATION_BADGE[r.rotation_status])}>
                  {r.rotation_status}
                </span>
              </td>
              <td className="py-3 px-4 text-slate-400 text-xs">{r.last_rotated || "\u2014"}</td>
              <td className="py-3 px-4">
                <span className={cn("text-xs px-2 py-0.5 rounded-full capitalize", RISK_BADGE[r.exposure_risk])}>
                  {r.exposure_risk}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Spend Anomaly Tab ────────────────────────────────────────────────────────

function SpendAnomalyTab({ rows }: { rows: SpendData[] }) {
  if (rows.length === 0) {
    return (
      <div className="text-center py-16 text-slate-500">
        <DollarSign className="h-8 w-8 mx-auto mb-3 opacity-40" />
        <p>No spend data available.</p>
      </div>
    );
  }

  const maxVal = Math.max(...rows.map((r) => Math.max(r.baseline, r.current)), 1);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center gap-4 text-xs text-slate-500 mb-2">
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-slate-600 inline-block" /> Baseline</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-blue-500 inline-block" /> Current</span>
        <span className="flex items-center gap-1.5"><AlertTriangle className="h-3 w-3 text-red-400" /> 3x Threshold Exceeded</span>
      </div>
      {rows.map((r) => {
        const basePct = Math.round((r.baseline / maxVal) * 100);
        const curPct = Math.round((r.current / maxVal) * 100);
        return (
          <div key={r.service} className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-sm text-white font-medium">{r.service}</span>
              {r.threshold_exceeded && (
                <span className="flex items-center gap-1 text-xs text-red-400">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  3x threshold
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-4 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-slate-600 rounded-full" style={{ width: `${basePct}%` }} />
              </div>
              <span className="text-xs text-slate-500 w-16 text-right">${r.baseline.toLocaleString()}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-4 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className={cn("h-full rounded-full", r.threshold_exceeded ? "bg-red-500" : "bg-blue-500")}
                  style={{ width: `${curPct}%` }}
                />
              </div>
              <span className="text-xs text-slate-500 w-16 text-right">${r.current.toLocaleString()}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Canary Plan Tab ──────────────────────────────────────────────────────────

const CANARY_ICONS: Record<string, React.ElementType> = {
  adjacent: KeyRound,
  store: Lock,
  internet: Globe,
  repo: Server,
};

function CanaryPlanTab({ strategies }: { strategies: CanaryStrategy[] }) {
  if (strategies.length === 0) {
    return (
      <div className="text-center py-16 text-slate-500">
        <Shield className="h-8 w-8 mx-auto mb-3 opacity-40" />
        <p>No canary strategies configured.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-6">
      {strategies.map((s) => {
        const Icon = CANARY_ICONS[s.type] ?? Shield;
        return (
          <div key={s.id} className="rounded-xl border border-slate-800 bg-slate-900/50 p-5 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-purple-500/10">
                  <Icon className="h-5 w-5 text-purple-400" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">{s.name}</h3>
                  <p className="text-xs text-slate-500 capitalize">{s.type.replace("_", " ")} strategy</p>
                </div>
              </div>
              {s.deployed ? (
                <span className="flex items-center gap-1 text-xs text-emerald-400">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Deployed
                </span>
              ) : (
                <span className="flex items-center gap-1 text-xs text-slate-500">
                  <Clock className="h-3.5 w-3.5" /> Pending
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">{s.description}</p>
            <div className="flex items-center justify-between pt-2 border-t border-slate-800">
              <span className="text-xs text-slate-500">Detections</span>
              <span className={cn("text-sm font-semibold", s.detections > 0 ? "text-red-400" : "text-slate-400")}>
                {s.detections}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── VPC Enforcement Tab ──────────────────────────────────────────────────────

function VPCEnforcementTab({ rows }: { rows: VPCRow[] }) {
  if (rows.length === 0) {
    return (
      <div className="text-center py-16 text-slate-500">
        <Network className="h-8 w-8 mx-auto mb-3 opacity-40" />
        <p>No AI service access records.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-slate-500 uppercase tracking-wider border-b border-slate-800">
            <th className="py-3 px-4">AI Service</th>
            <th className="py-3 px-4">Provider</th>
            <th className="py-3 px-4">Routing</th>
            <th className="py-3 px-4">Endpoint Policy</th>
            <th className="py-3 px-4">Last Audit</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60">
          {rows.map((r, i) => (
            <tr key={`${r.service}-${i}`} className="hover:bg-slate-800/40 transition-colors">
              <td className="py-3 px-4 text-white font-medium">{r.service}</td>
              <td className="py-3 px-4 text-slate-400 text-xs">{r.provider}</td>
              <td className="py-3 px-4">
                {r.routing === "vpc" ? (
                  <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <Lock className="h-3 w-3" /> VPC
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20">
                    <Globe className="h-3 w-3" /> Public
                  </span>
                )}
              </td>
              <td className="py-3 px-4">
                {r.endpoint_policy ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                ) : (
                  <XCircle className="h-4 w-4 text-red-400" />
                )}
              </td>
              <td className="py-3 px-4 text-slate-400 text-xs">{r.last_audit || "\u2014"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Loading Skeleton ─────────────────────────────────────────────────────────

function Skeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-slate-800 bg-slate-900 p-5 h-24" />
        ))}
      </div>
      <div className="rounded-xl border border-slate-800 bg-slate-900 h-64" />
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function LLMjackingPage() {
  const [tab, setTab] = useState<Tab>("credentials");
  const { data: credData, isLoading: credLoading } = useModuleEndpoint("llmjacking", "credentials");
  const { data: spendData, isLoading: spendLoading } = useModuleEndpoint("llmjacking", "spend");
  const { data: canaryData, isLoading: canaryLoading } = useModuleEndpoint("llmjacking", "canary");
  const { data: vpcData, isLoading: vpcLoading } = useModuleEndpoint("llmjacking", "vpc");

  const isLoading = credLoading || spendLoading || canaryLoading || vpcLoading;

  const credentials: CredentialRow[] = credData?.credentials ?? [];
  const spendRows: SpendData[] = spendData?.services ?? [];
  const strategies: CanaryStrategy[] = canaryData?.strategies ?? [];
  const vpcRows: VPCRow[] = vpcData?.services ?? [];

  const totalServices = credentials.length;
  const credRisks = credentials.filter((c) => c.exposure_risk === "critical" || c.exposure_risk === "high").length;
  const spendAnomalies = spendRows.filter((s) => s.threshold_exceeded).length;
  const vpcPct = vpcRows.length > 0
    ? Math.round((vpcRows.filter((v) => v.routing === "vpc").length / vpcRows.length) * 100)
    : 0;

  if (isLoading) {
    return (
      <div className="flex-1 overflow-auto p-6 lg:p-10 bg-slate-950">
        <div className="flex items-center gap-3 mb-8">
          <Brain className="h-6 w-6 text-purple-400" />
          <h1 className="text-xl font-semibold text-white">LLMjacking</h1>
        </div>
        <Skeleton />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto p-6 lg:p-10 bg-slate-950">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <Brain className="h-6 w-6 text-purple-400" />
        <div>
          <h1 className="text-xl font-semibold text-white">LLMjacking</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Cloud AI credential abuse detection &mdash; key rotation, spend anomaly, canary traps & VPC enforcement
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <SummaryCard label="AI Services" value={totalServices} icon={Cpu} accent="text-purple-400" sub="monitored credentials" />
        <SummaryCard label="Credential Risks" value={credRisks} icon={KeyRound} accent="text-red-400" sub="critical + high exposure" />
        <SummaryCard label="Spend Anomalies" value={spendAnomalies} icon={DollarSign} accent="text-yellow-400" sub="above 3x threshold" />
        <SummaryCard label="VPC Enforcement" value={`${vpcPct}%`} icon={Network} accent="text-emerald-400" sub="services via VPC endpoint" />
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 mb-6">
        <TabButton active={tab === "credentials"} label="Credential Audit" onClick={() => setTab("credentials")} />
        <TabButton active={tab === "spend"} label="Spend Anomaly" onClick={() => setTab("spend")} />
        <TabButton active={tab === "canary"} label="Canary Plan" onClick={() => setTab("canary")} />
        <TabButton active={tab === "vpc"} label="VPC Enforcement" onClick={() => setTab("vpc")} />
      </div>

      {/* Tab Content */}
      <div className="rounded-xl border border-slate-800 bg-slate-900">
        {tab === "credentials" && <CredentialAuditTab rows={credentials} />}
        {tab === "spend" && <SpendAnomalyTab rows={spendRows} />}
        {tab === "canary" && <CanaryPlanTab strategies={strategies} />}
        {tab === "vpc" && <VPCEnforcementTab rows={vpcRows} />}
      </div>
    </div>
  );
}
