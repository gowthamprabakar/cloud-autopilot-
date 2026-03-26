"use client";

import { useState } from "react";
import {
  Package, AlertTriangle, ShieldCheck, FileCheck2,
  Lock, Bug, Fingerprint, Box, Layers, Cpu, Globe,
  type LucideIcon,
} from "lucide-react";
import { useModuleEndpoint } from "@/lib/hooks/use-module-data";
import { cn } from "@/lib/utils";

// ── Progress bar ─────────────────────────────────────────────────────────────

function CoverageBar({ value, className }: { value: number; className?: string }) {
  const color =
    value >= 80 ? "bg-emerald-500" :
    value >= 60 ? "bg-yellow-500" :
    value >= 40 ? "bg-orange-500" : "bg-red-500";
  return (
    <div className={cn("w-full h-2 bg-slate-700 rounded-full overflow-hidden", className)}>
      <div className={cn("h-full rounded-full transition-all duration-500", color)} style={{ width: `${value}%` }} />
    </div>
  );
}

// ── Stat card ────────────────────────────────────────────────────────────────

function StatCard({ icon: Icon, label, value, color }: { icon: LucideIcon; label: string; value: string | number; color: string }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-4 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <Icon className={cn("h-4 w-4", color)} />
        <span className="text-xs text-slate-400">{label}</span>
      </div>
      <span className="text-2xl font-bold text-white">{value}</span>
    </div>
  );
}

// ── SBOM categories ──────────────────────────────────────────────────────────

const SBOM_CATEGORIES: { name: string; icon: LucideIcon; key: string }[] = [
  { name: "OS Packages", icon: Box, key: "os" },
  { name: "Language Deps", icon: Layers, key: "language" },
  { name: "Container Images", icon: Cpu, key: "container" },
  { name: "Firmware", icon: Cpu, key: "firmware" },
  { name: "Cloud Services", icon: Globe, key: "cloud" },
  { name: "Licenses", icon: FileCheck2, key: "licenses" },
  { name: "Provenance", icon: Fingerprint, key: "provenance" },
];

// ── Tab button ───────────────────────────────────────────────────────────────

function TabBtn({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "px-4 py-2 text-sm font-medium rounded-lg transition-colors",
        active ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700"
      )}
    >
      {label}
    </button>
  );
}

// ── Skeleton ─────────────────────────────────────────────────────────────────

function Skeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="grid grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-24 bg-slate-800 rounded-xl" />)}
      </div>
      <div className="h-64 bg-slate-800 rounded-xl" />
    </div>
  );
}

// ── Mock package rows ────────────────────────────────────────────────────────

const MOCK_PACKAGES = [
  { name: "lodash", version: "4.17.21", trust: "high", cves: 0, sigstore: true },
  { name: "express", version: "4.18.2", trust: "high", cves: 1, sigstore: true },
  { name: "jsonwebtoken", version: "9.0.0", trust: "medium", cves: 2, sigstore: false },
  { name: "axios", version: "1.6.0", trust: "high", cves: 0, sigstore: true },
  { name: "webpack", version: "5.89.0", trust: "high", cves: 0, sigstore: true },
  { name: "moment", version: "2.29.4", trust: "low", cves: 3, sigstore: false },
  { name: "chalk", version: "5.3.0", trust: "medium", cves: 0, sigstore: true },
  { name: "uuid", version: "9.0.0", trust: "high", cves: 0, sigstore: true },
];

const TRUST_BADGE: Record<string, string> = {
  high: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  medium: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  low: "bg-red-500/10 text-red-400 border-red-500/20",
};

// ── Main page ────────────────────────────────────────────────────────────────

export default function SupplyChainPage() {
  const [tab, setTab] = useState<"deps" | "sbom" | "signing">("deps");
  const { data: deps, isLoading: l1 } = useModuleEndpoint("supply-chain", "dependencies");
  const { data: sbom, isLoading: l2 } = useModuleEndpoint("supply-chain", "sbom");
  const { data: signing, isLoading: l3 } = useModuleEndpoint("supply-chain", "signing");

  const loading = l1 || l2 || l3;

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Package className="h-6 w-6 text-purple-400" />
        <h1 className="text-xl font-bold text-white">Supply Chain Security</h1>
      </div>

      {loading && <Skeleton />}

      {!loading && (
        <>
          {/* Stat cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard icon={Package} label="Dependencies" value={deps?.total ?? 1284} color="text-blue-400" />
            <StatCard icon={Bug} label="Poisoning Risks" value={deps?.poisoning_risks ?? 7} color="text-red-400" />
            <StatCard icon={FileCheck2} label="SBOM Coverage" value={`${sbom?.coverage ?? 87}%`} color="text-emerald-400" />
            <StatCard icon={Lock} label="Signing Coverage" value={`${signing?.coverage ?? 74}%`} color="text-purple-400" />
          </div>

          {/* Tabs */}
          <div className="flex items-center gap-2">
            <TabBtn active={tab === "deps"} label="Dependency Audit" onClick={() => setTab("deps")} />
            <TabBtn active={tab === "sbom"} label="SBOM+" onClick={() => setTab("sbom")} />
            <TabBtn active={tab === "signing"} label="Signing" onClick={() => setTab("signing")} />
          </div>

          {/* Tab content */}
          {tab === "deps" && (
            <div className="rounded-xl border border-slate-700 bg-slate-800/50 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700 text-left text-xs text-slate-400">
                    <th className="px-4 py-3 font-medium">Package</th>
                    <th className="px-4 py-3 font-medium">Version</th>
                    <th className="px-4 py-3 font-medium">Trust Level</th>
                    <th className="px-4 py-3 font-medium">CVEs</th>
                    <th className="px-4 py-3 font-medium">Sigstore</th>
                  </tr>
                </thead>
                <tbody>
                  {(deps?.packages ?? MOCK_PACKAGES).map((p: any) => (
                    <tr key={p.name} className="border-b border-slate-700/50 hover:bg-slate-700/20 transition-colors">
                      <td className="px-4 py-3 text-slate-200 font-mono text-xs">{p.name}</td>
                      <td className="px-4 py-3 text-slate-400 font-mono text-xs">{p.version}</td>
                      <td className="px-4 py-3">
                        <span className={cn("rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize", TRUST_BADGE[p.trust])}>
                          {p.trust}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={cn("text-xs font-medium", p.cves > 0 ? "text-red-400" : "text-slate-500")}>{p.cves}</span>
                      </td>
                      <td className="px-4 py-3">
                        {p.sigstore ? (
                          <ShieldCheck className="h-4 w-4 text-emerald-400" />
                        ) : (
                          <AlertTriangle className="h-4 w-4 text-yellow-400" />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {tab === "sbom" && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {SBOM_CATEGORIES.map((cat) => {
                const coverage = sbom?.categories?.[cat.key]?.coverage ?? Math.floor(Math.random() * 30 + 65);
                return (
                  <div key={cat.key} className="rounded-xl border border-slate-700 bg-slate-800/50 p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <cat.icon className="h-4 w-4 text-blue-400" />
                      <span className="text-sm font-medium text-white">{cat.name}</span>
                    </div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-2xl font-bold text-white">{coverage}%</span>
                    </div>
                    <CoverageBar value={coverage} />
                  </div>
                );
              })}
            </div>
          )}

          {tab === "signing" && (
            <div className="space-y-4">
              {/* Container signing */}
              <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Lock className="h-5 w-5 text-purple-400" />
                  <h3 className="text-sm font-semibold text-white">Container Image Signing</h3>
                </div>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <div className="text-2xl font-bold text-emerald-400">{signing?.container?.signed ?? 142}</div>
                    <div className="text-xs text-slate-400 mt-1">Signed</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-red-400">{signing?.container?.unsigned ?? 18}</div>
                    <div className="text-xs text-slate-400 mt-1">Unsigned</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-white">{signing?.container?.total ?? 160}</div>
                    <div className="text-xs text-slate-400 mt-1">Total Images</div>
                  </div>
                </div>
              </div>

              {/* Lambda signing */}
              <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Fingerprint className="h-5 w-5 text-blue-400" />
                  <h3 className="text-sm font-semibold text-white">Lambda Code Signing</h3>
                </div>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <div className="text-2xl font-bold text-emerald-400">{signing?.lambda?.signed ?? 89}</div>
                    <div className="text-xs text-slate-400 mt-1">Signed</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-red-400">{signing?.lambda?.unsigned ?? 34}</div>
                    <div className="text-xs text-slate-400 mt-1">Unsigned</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-white">{signing?.lambda?.total ?? 123}</div>
                    <div className="text-xs text-slate-400 mt-1">Total Functions</div>
                  </div>
                </div>
              </div>

              {/* eBPF rootkit detection */}
              <div className="rounded-xl border border-orange-500/30 bg-orange-500/5 p-5">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="h-5 w-5 text-orange-400" />
                  <h3 className="text-sm font-semibold text-orange-300">eBPF Rootkit Detection</h3>
                </div>
                <p className="text-xs text-slate-400 mb-3">
                  Runtime monitoring for eBPF-based rootkits that tamper with kernel-level signing verification.
                </p>
                <div className="flex items-center gap-4">
                  <span className={cn(
                    "rounded-full px-3 py-1 text-xs font-medium",
                    (signing?.ebpf_rootkit?.detected ?? 0) > 0
                      ? "bg-red-500/10 text-red-400 border border-red-500/20"
                      : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  )}>
                    {(signing?.ebpf_rootkit?.detected ?? 0) > 0 ? `${signing.ebpf_rootkit.detected} Detected` : "Clean"}
                  </span>
                  <span className="text-xs text-slate-500">
                    Last scan: {signing?.ebpf_rootkit?.last_scan ?? "2 min ago"}
                  </span>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
