"use client";

import { useState } from "react";
import {
  Factory, ShieldAlert, Wifi, Radio, Globe,
  AlertTriangle, Server, Layers, Lock,
  Gauge, Activity, type LucideIcon,
} from "lucide-react";
import { useModuleEndpoint } from "@/lib/hooks/use-module-data";
import { cn } from "@/lib/utils";

// ── Progress bar ─────────────────────────────────────────────────────────────

function ScoreBar({ value, className }: { value: number; className?: string }) {
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

// ── Purdue zone visual ───────────────────────────────────────────────────────

const PURDUE_ZONES = [
  { level: 5, name: "Enterprise", color: "border-blue-500/40 bg-blue-500/5", items: ["ERP", "Email", "Web"] },
  { level: 4, name: "IT/OT DMZ", color: "border-purple-500/40 bg-purple-500/5", items: ["Historian", "Jump Server"] },
  { level: 3, name: "Operations", color: "border-yellow-500/40 bg-yellow-500/5", items: ["SCADA Server", "HMI"] },
  { level: 2, name: "Area Control", color: "border-orange-500/40 bg-orange-500/5", items: ["PLC", "RTU", "DCS"] },
  { level: 1, name: "Basic Control", color: "border-red-500/40 bg-red-500/5", items: ["Sensors", "Actuators"] },
  { level: 0, name: "Process", color: "border-red-600/40 bg-red-600/5", items: ["Physical Plant"] },
];

// ── Protocol data ────────────────────────────────────────────────────────────

const MOCK_PROTOCOLS = [
  { name: "Modbus TCP", port: 502, status: "whitelisted", violations: 0 },
  { name: "DNP3", port: 20000, status: "whitelisted", violations: 2 },
  { name: "IEC 61850", port: 102, status: "whitelisted", violations: 0 },
  { name: "IEC 60870-5-104", port: 2404, status: "whitelisted", violations: 1 },
  { name: "EtherNet/IP", port: 44818, status: "whitelisted", violations: 0 },
  { name: "OPC UA", port: 4840, status: "monitoring", violations: 3 },
  { name: "BACnet", port: 47808, status: "whitelisted", violations: 0 },
];

// ── Nation-state threat actors ───────────────────────────────────────────────

const THREAT_ACTORS = [
  {
    name: "Salt Typhoon",
    origin: "China",
    color: "text-red-400",
    borderColor: "border-red-500/30",
    ttps: ["T1190 — Exploit Public-Facing App", "T1133 — External Remote Services", "T1059 — Command & Scripting"],
    targets: "Telecom, ISPs, Critical Infrastructure",
    risk: "critical",
  },
  {
    name: "Sandworm",
    origin: "Russia (GRU)",
    color: "text-orange-400",
    borderColor: "border-orange-500/30",
    ttps: ["T1485 — Data Destruction", "T1562 — Impair Defenses", "T1021 — Remote Services"],
    targets: "Power Grid, Water Treatment, ICS/SCADA",
    risk: "critical",
  },
  {
    name: "Volt Typhoon",
    origin: "China",
    color: "text-yellow-400",
    borderColor: "border-yellow-500/30",
    ttps: ["T1078 — Valid Accounts", "T1036 — Masquerading", "T1218 — System Binary Proxy Exec"],
    targets: "US Critical Infrastructure, Maritime, Aviation",
    risk: "high",
  },
];

const RISK_BADGE: Record<string, string> = {
  critical: "bg-red-500/10 text-red-400 border border-red-500/20",
  high: "bg-orange-500/10 text-orange-400 border border-orange-500/20",
  medium: "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20",
};

// ── Skeleton ─────────────────────────────────────────────────────────────────

function Skeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="grid grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-24 bg-slate-800 rounded-xl" />)}
      </div>
      <div className="h-72 bg-slate-800 rounded-xl" />
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function OTICSPage() {
  const [tab, setTab] = useState<"twin" | "airgap" | "protocol" | "nationstate">("twin");
  const { data: twin, isLoading: l1 } = useModuleEndpoint("ot-ics", "digital-twin");
  const { data: airGap, isLoading: l2 } = useModuleEndpoint("ot-ics", "air-gap");
  const { data: proto, isLoading: l3 } = useModuleEndpoint("ot-ics", "protocol-whitelist");
  const { data: nation, isLoading: l4 } = useModuleEndpoint("ot-ics", "nation-state");

  const loading = l1 || l2 || l3 || l4;

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Factory className="h-6 w-6 text-orange-400" />
        <h1 className="text-xl font-bold text-white">OT/ICS Critical Infrastructure</h1>
      </div>

      {loading && <Skeleton />}

      {!loading && (
        <>
          {/* Stat cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard icon={Server} label="Industrial Assets" value={twin?.total_assets ?? 347} color="text-blue-400" />
            <StatCard icon={Lock} label="Air Gap Score" value={`${airGap?.score ?? 82}%`} color="text-emerald-400" />
            <StatCard icon={Radio} label="Protocol Violations" value={proto?.total_violations ?? 6} color="text-orange-400" />
            <StatCard icon={ShieldAlert} label="Nation-State Risk" value={nation?.risk_level ?? "High"} color="text-red-400" />
          </div>

          {/* Tabs */}
          <div className="flex items-center gap-2 flex-wrap">
            <TabBtn active={tab === "twin"} label="Digital Twin" onClick={() => setTab("twin")} />
            <TabBtn active={tab === "airgap"} label="Air Gap" onClick={() => setTab("airgap")} />
            <TabBtn active={tab === "protocol"} label="Protocol Whitelist" onClick={() => setTab("protocol")} />
            <TabBtn active={tab === "nationstate"} label="Nation-State" onClick={() => setTab("nationstate")} />
          </div>

          {/* Digital Twin */}
          {tab === "twin" && (
            <div className="space-y-4">
              <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-5">
                <h3 className="text-sm font-semibold text-white mb-2">PLC / SCADA Asset Inventory</h3>
                <div className="grid grid-cols-3 gap-4 text-center mb-4">
                  <div>
                    <div className="text-2xl font-bold text-blue-400">{twin?.plc_count ?? 128}</div>
                    <div className="text-xs text-slate-400 mt-1">PLCs</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-purple-400">{twin?.scada_count ?? 42}</div>
                    <div className="text-xs text-slate-400 mt-1">SCADA Systems</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-orange-400">{twin?.hmi_count ?? 67}</div>
                    <div className="text-xs text-slate-400 mt-1">HMI Panels</div>
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-5">
                <h3 className="text-sm font-semibold text-white mb-4">Purdue Model Zones</h3>
                <div className="space-y-2">
                  {PURDUE_ZONES.map((zone) => (
                    <div key={zone.level} className={cn("rounded-lg border p-3 flex items-center gap-4", zone.color)}>
                      <span className="text-xs font-bold text-slate-300 w-8">L{zone.level}</span>
                      <span className="text-sm font-medium text-white w-28">{zone.name}</span>
                      <div className="flex items-center gap-2 flex-wrap">
                        {zone.items.map((item) => (
                          <span key={item} className="rounded-full bg-slate-700/50 px-2.5 py-0.5 text-xs text-slate-300">
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Air Gap */}
          {tab === "airgap" && (
            <div className="space-y-4">
              <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-white">Air Gap Integrity Score</h3>
                  <span className={cn(
                    "text-3xl font-bold",
                    (airGap?.score ?? 82) >= 80 ? "text-emerald-400" : "text-yellow-400"
                  )}>
                    {airGap?.score ?? 82}%
                  </span>
                </div>
                <ScoreBar value={airGap?.score ?? 82} />
              </div>

              <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-5">
                <h3 className="text-sm font-semibold text-white mb-3">Detected Paths (IT-to-OT Leakage)</h3>
                <div className="space-y-2">
                  {(airGap?.paths ?? [
                    { from: "Corporate VPN", to: "SCADA Subnet", severity: "high" },
                    { from: "Cloud Historian", to: "PLC Network", severity: "critical" },
                    { from: "Vendor Laptop", to: "HMI Segment", severity: "medium" },
                  ]).map((path: any, i: number) => (
                    <div key={i} className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-900/50 p-3">
                      <span className={cn(
                        "rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize",
                        RISK_BADGE[path.severity] ?? RISK_BADGE.medium
                      )}>
                        {path.severity}
                      </span>
                      <span className="text-xs text-slate-300">{path.from}</span>
                      <Activity className="h-3 w-3 text-slate-500" />
                      <span className="text-xs text-slate-300">{path.to}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Protocol Whitelist */}
          {tab === "protocol" && (
            <div className="rounded-xl border border-slate-700 bg-slate-800/50 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700 text-left text-xs text-slate-400">
                    <th className="px-4 py-3 font-medium">Protocol</th>
                    <th className="px-4 py-3 font-medium">Port</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Violations</th>
                  </tr>
                </thead>
                <tbody>
                  {(proto?.protocols ?? MOCK_PROTOCOLS).map((p: any) => (
                    <tr key={p.name} className="border-b border-slate-700/50 hover:bg-slate-700/20 transition-colors">
                      <td className="px-4 py-3 text-slate-200 font-medium text-xs">{p.name}</td>
                      <td className="px-4 py-3 text-slate-400 font-mono text-xs">{p.port}</td>
                      <td className="px-4 py-3">
                        <span className={cn(
                          "rounded-full px-2.5 py-0.5 text-xs font-medium capitalize",
                          p.status === "whitelisted"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20"
                        )}>
                          {p.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={cn("text-xs font-medium", p.violations > 0 ? "text-red-400" : "text-slate-500")}>
                          {p.violations}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Nation-State */}
          {tab === "nationstate" && (
            <div className="space-y-4">
              {THREAT_ACTORS.map((actor) => (
                <div key={actor.name} className={cn("rounded-xl border bg-slate-800/50 p-5", actor.borderColor)}>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <Globe className={cn("h-5 w-5", actor.color)} />
                      <div>
                        <h3 className="text-sm font-semibold text-white">{actor.name}</h3>
                        <span className="text-xs text-slate-400">{actor.origin}</span>
                      </div>
                    </div>
                    <span className={cn("rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize", RISK_BADGE[actor.risk])}>
                      {actor.risk}
                    </span>
                  </div>
                  <div className="mb-3">
                    <span className="text-xs text-slate-500">Targets:</span>
                    <span className="text-xs text-slate-300 ml-2">{actor.targets}</span>
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs text-slate-500">MITRE ATT&CK TTPs:</span>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {actor.ttps.map((ttp) => (
                        <span key={ttp} className="rounded-md bg-slate-700/50 px-2 py-1 text-xs text-slate-300 font-mono">
                          {ttp}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
