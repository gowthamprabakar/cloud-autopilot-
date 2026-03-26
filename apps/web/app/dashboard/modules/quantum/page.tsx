"use client";

import { useState } from "react";
import { Lock, ShieldAlert, Clock, Atom, FileKey } from "lucide-react";
import { useModuleEndpoint } from "@/lib/hooks/use-module-data";
import { cn } from "@/lib/utils";

// -- Data hooks ---------------------------------------------------------------

function useQuantumData() {
  const cryptoBom = useModuleEndpoint("quantum", "crypto-bom");
  const harvestSignals = useModuleEndpoint("quantum", "harvest-signals");
  const pqcReadiness = useModuleEndpoint("quantum", "pqc-readiness");
  return { cryptoBom, harvestSignals, pqcReadiness };
}

// -- Types --------------------------------------------------------------------

interface CryptoAlgorithm {
  id: string;
  algorithm: string;
  type: "Symmetric" | "Asymmetric" | "Hash" | "KEM" | "Signature";
  keySize: number;
  usage: string;
  qVulnerable: boolean;
  pqcAlternative: string;
  instances: number;
}

interface HarvestSignal {
  id: string;
  source: string;
  protocol: string;
  cipherSuite: string;
  interceptionPoint: string;
  dataClassification: "Top Secret" | "Secret" | "Confidential" | "Internal";
  riskLevel: "Critical" | "High" | "Medium" | "Low";
}

interface PqcPhase {
  id: string;
  phase: string;
  description: string;
  status: "Complete" | "In Progress" | "Planned";
  progress: number;
  timeline: string;
}

interface NistCard {
  id: string;
  standard: string;
  algorithm: string;
  type: string;
  status: "Finalized" | "Draft" | "Candidate";
  fips: string;
}

// -- Fallback data ------------------------------------------------------------

const FALLBACK_CRYPTO_BOM: CryptoAlgorithm[] = [
  { id: "1", algorithm: "RSA-2048", type: "Asymmetric", keySize: 2048, usage: "TLS Certificates", qVulnerable: true, pqcAlternative: "ML-KEM-768", instances: 342 },
  { id: "2", algorithm: "ECDSA P-256", type: "Signature", keySize: 256, usage: "Code Signing", qVulnerable: true, pqcAlternative: "ML-DSA-65", instances: 128 },
  { id: "3", algorithm: "AES-256-GCM", type: "Symmetric", keySize: 256, usage: "Data Encryption", qVulnerable: false, pqcAlternative: "N/A (Q-Safe)", instances: 1204 },
  { id: "4", algorithm: "ECDH P-384", type: "Asymmetric", keySize: 384, usage: "Key Exchange", qVulnerable: true, pqcAlternative: "ML-KEM-1024", instances: 89 },
  { id: "5", algorithm: "SHA-256", type: "Hash", keySize: 256, usage: "Integrity", qVulnerable: false, pqcAlternative: "N/A (Q-Safe)", instances: 2100 },
  { id: "6", algorithm: "RSA-4096", type: "Asymmetric", keySize: 4096, usage: "API Authentication", qVulnerable: true, pqcAlternative: "ML-KEM-1024", instances: 56 },
  { id: "7", algorithm: "Ed25519", type: "Signature", keySize: 256, usage: "SSH Keys", qVulnerable: true, pqcAlternative: "SLH-DSA-128f", instances: 215 },
  { id: "8", algorithm: "ChaCha20-Poly1305", type: "Symmetric", keySize: 256, usage: "VPN Tunnels", qVulnerable: false, pqcAlternative: "N/A (Q-Safe)", instances: 67 },
];

const FALLBACK_HARVEST: HarvestSignal[] = [
  { id: "1", source: "External API Gateway", protocol: "TLS 1.2", cipherSuite: "RSA-AES-256-GCM", interceptionPoint: "CDN Edge", dataClassification: "Confidential", riskLevel: "Critical" },
  { id: "2", source: "VPN Concentrator", protocol: "IKEv2", cipherSuite: "ECDH-P256", interceptionPoint: "ISP Peering", dataClassification: "Secret", riskLevel: "Critical" },
  { id: "3", source: "Email Gateway", protocol: "TLS 1.2", cipherSuite: "RSA-2048", interceptionPoint: "MX Record", dataClassification: "Internal", riskLevel: "High" },
  { id: "4", source: "Database Replication", protocol: "TLS 1.3", cipherSuite: "ECDH-X25519", interceptionPoint: "Cross-Region Link", dataClassification: "Top Secret", riskLevel: "High" },
  { id: "5", source: "S3 Transfer", protocol: "HTTPS", cipherSuite: "RSA-2048", interceptionPoint: "Public Endpoint", dataClassification: "Confidential", riskLevel: "Medium" },
];

const FALLBACK_PHASES: PqcPhase[] = [
  { id: "1", phase: "Phase 1: Discovery", description: "Inventory all cryptographic assets, map dependencies, identify Q-vulnerable algorithms", status: "Complete", progress: 100, timeline: "Q1-Q2 2025" },
  { id: "2", phase: "Phase 2: Hybrid Migration", description: "Deploy hybrid PQC+classical for TLS, VPN, and key exchange. Test ML-KEM and ML-DSA", status: "In Progress", progress: 42, timeline: "Q3 2025 - Q4 2026" },
  { id: "3", phase: "Phase 3: Full PQC", description: "Complete transition to NIST-approved PQC algorithms, retire classical asymmetric crypto", status: "Planned", progress: 0, timeline: "2027 - 2029" },
];

const FALLBACK_NIST: NistCard[] = [
  { id: "1", standard: "FIPS 203", algorithm: "ML-KEM (Kyber)", type: "Key Encapsulation", status: "Finalized", fips: "FIPS 203" },
  { id: "2", standard: "FIPS 204", algorithm: "ML-DSA (Dilithium)", type: "Digital Signature", status: "Finalized", fips: "FIPS 204" },
  { id: "3", standard: "FIPS 205", algorithm: "SLH-DSA (SPHINCS+)", type: "Hash-Based Signature", status: "Finalized", fips: "FIPS 205" },
  { id: "4", standard: "FIPS 206", algorithm: "FN-DSA (Falcon)", type: "Lattice Signature", status: "Draft", fips: "FIPS 206" },
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

function QVulnerableBadge({ vulnerable }: { vulnerable: boolean }) {
  return vulnerable ? (
    <span className="inline-flex items-center rounded-full border border-red-500/20 bg-red-500/10 text-red-400 px-2 py-0.5 text-xs font-medium">Q-Vulnerable</span>
  ) : (
    <span className="inline-flex items-center rounded-full border border-emerald-500/20 bg-emerald-500/10 text-emerald-400 px-2 py-0.5 text-xs font-medium">Q-Safe</span>
  );
}

function ClassificationBadge({ level }: { level: string }) {
  const styles: Record<string, string> = {
    "Top Secret": "bg-red-500/10 text-red-400 border-red-500/20",
    Secret: "bg-orange-500/10 text-orange-400 border-orange-500/20",
    Confidential: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    Internal: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  };
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium", styles[level] ?? styles.Internal)}>
      {level}
    </span>
  );
}

// -- PQC Readiness Gauge ------------------------------------------------------

function PqcGauge({ score }: { score: number }) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 70 ? "#34d399" : score >= 40 ? "#fbbf24" : "#f87171";
  return (
    <div className="flex items-center gap-6">
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx="70" cy="70" r={radius} stroke="#334155" strokeWidth="10" fill="none" />
        <circle
          cx="70" cy="70" r={radius}
          stroke={color} strokeWidth="10" fill="none"
          strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset}
          transform="rotate(-90 70 70)"
        />
        <text x="70" y="66" textAnchor="middle" className="fill-white text-2xl font-bold" fontSize="28">{score}%</text>
        <text x="70" y="86" textAnchor="middle" className="fill-slate-400" fontSize="11">PQC Ready</text>
      </svg>
      <div className="flex flex-col gap-1">
        <h3 className="text-sm font-semibold text-white">Post-Quantum Readiness</h3>
        <p className="text-xs text-slate-400">Estimated Q-Day window: 2028 - 2032</p>
        <p className="text-xs text-slate-500 mt-1">NIST PQC standards finalized Aug 2024</p>
      </div>
    </div>
  );
}

// -- Tabs ---------------------------------------------------------------------

const TABS = ["Crypto-BOM", "Harvest Signals", "PQC Readiness"] as const;
type Tab = (typeof TABS)[number];

// -- Main page ----------------------------------------------------------------

export default function QuantumPage() {
  const { cryptoBom, harvestSignals, pqcReadiness } = useQuantumData();
  const [activeTab, setActiveTab] = useState<Tab>("Crypto-BOM");

  const bomList: CryptoAlgorithm[] = (cryptoBom.data as any)?.items ?? FALLBACK_CRYPTO_BOM;
  const harvestList: HarvestSignal[] = (harvestSignals.data as any)?.items ?? FALLBACK_HARVEST;
  const phases: PqcPhase[] = (pqcReadiness.data as any)?.phases ?? FALLBACK_PHASES;
  const nistCards: NistCard[] = (pqcReadiness.data as any)?.nist ?? FALLBACK_NIST;

  const totalAlgorithms = bomList.length;
  const qVulnerable = bomList.filter((b) => b.qVulnerable).length;
  const qSafe = bomList.filter((b) => !b.qVulnerable).length;
  const migrationMonths = 42;
  const readinessScore = Math.round((phases.reduce((s, p) => s + p.progress, 0) / (phases.length * 100)) * 100);

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-900 min-h-screen">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Atom className="h-6 w-6 text-blue-400" />
        <div>
          <h1 className="text-xl font-bold text-white">Quantum Cryptography Readiness</h1>
          <p className="text-sm text-slate-400 mt-0.5">Crypto-BOM inventory, harvest-now-decrypt-later signals &amp; PQC migration roadmap</p>
        </div>
      </div>

      {/* PQC Gauge Hero */}
      <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-6">
        <PqcGauge score={readinessScore} />
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard icon={FileKey} label="Total Algorithms" value={totalAlgorithms} accent="bg-blue-600/80" />
        <SummaryCard icon={ShieldAlert} label="Q-Vulnerable" value={qVulnerable} accent="bg-red-600/80" />
        <SummaryCard icon={Lock} label="Q-Safe" value={qSafe} accent="bg-emerald-600/80" />
        <SummaryCard icon={Clock} label="Migration Months" value={migrationMonths} accent="bg-orange-600/80" />
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

      {/* Crypto-BOM Tab */}
      {activeTab === "Crypto-BOM" && (
        <div className="rounded-xl border border-slate-700 bg-slate-800/40 overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-800/80 text-slate-400 text-xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Algorithm</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3 text-center">Key Size</th>
                <th className="px-4 py-3">Usage</th>
                <th className="px-4 py-3 text-center">Status</th>
                <th className="px-4 py-3">PQC Alternative</th>
                <th className="px-4 py-3 text-center">Instances</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {bomList.map((b) => (
                <tr key={b.id} className="hover:bg-slate-800/60 transition-colors">
                  <td className="px-4 py-3 text-white font-medium font-mono text-xs">{b.algorithm}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs font-medium text-slate-300 bg-slate-700/50 rounded px-2 py-0.5">{b.type}</span>
                  </td>
                  <td className="px-4 py-3 text-center text-slate-300 font-mono text-xs">{b.keySize}</td>
                  <td className="px-4 py-3 text-slate-300">{b.usage}</td>
                  <td className="px-4 py-3 text-center"><QVulnerableBadge vulnerable={b.qVulnerable} /></td>
                  <td className="px-4 py-3 text-slate-300 font-mono text-xs">{b.pqcAlternative}</td>
                  <td className="px-4 py-3 text-center text-slate-300">{b.instances.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Harvest Signals Tab */}
      {activeTab === "Harvest Signals" && (
        <div className="rounded-xl border border-slate-700 bg-slate-800/40 overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-800/80 text-slate-400 text-xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Source</th>
                <th className="px-4 py-3">Protocol</th>
                <th className="px-4 py-3">Cipher Suite</th>
                <th className="px-4 py-3">Interception Point</th>
                <th className="px-4 py-3 text-center">Classification</th>
                <th className="px-4 py-3 text-center">Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {harvestList.map((h) => (
                <tr key={h.id} className="hover:bg-slate-800/60 transition-colors">
                  <td className="px-4 py-3 text-white font-medium">{h.source}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs font-medium text-slate-300 bg-slate-700/50 rounded px-2 py-0.5">{h.protocol}</span>
                  </td>
                  <td className="px-4 py-3 text-slate-300 font-mono text-xs">{h.cipherSuite}</td>
                  <td className="px-4 py-3 text-slate-300">{h.interceptionPoint}</td>
                  <td className="px-4 py-3 text-center"><ClassificationBadge level={h.dataClassification} /></td>
                  <td className="px-4 py-3 text-center">
                    <span className={cn(
                      "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium",
                      h.riskLevel === "Critical" ? "bg-red-500/10 text-red-400 border-red-500/20" :
                      h.riskLevel === "High" ? "bg-orange-500/10 text-orange-400 border-orange-500/20" :
                      "bg-yellow-500/10 text-yellow-400 border-yellow-500/20"
                    )}>
                      {h.riskLevel}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* PQC Readiness Tab */}
      {activeTab === "PQC Readiness" && (
        <div className="space-y-6">
          {/* 3-Phase Roadmap */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Migration Roadmap</h3>
            {phases.map((p) => {
              const statusColor = p.status === "Complete" ? "text-emerald-400" : p.status === "In Progress" ? "text-blue-400" : "text-slate-500";
              const barColor = p.status === "Complete" ? "bg-emerald-500" : p.status === "In Progress" ? "bg-blue-500" : "bg-slate-600";
              return (
                <div key={p.id} className="rounded-xl border border-slate-700 bg-slate-800/50 p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-white">{p.phase}</h4>
                    <span className={cn("text-xs font-medium", statusColor)}>{p.status}</span>
                  </div>
                  <p className="text-xs text-slate-400">{p.description}</p>
                  <div className="flex items-center gap-3">
                    <div className="flex-1 h-2 rounded-full bg-slate-700 overflow-hidden">
                      <div className={cn("h-full rounded-full transition-all", barColor)} style={{ width: `${p.progress}%` }} />
                    </div>
                    <span className="text-xs font-semibold text-slate-300 w-10 text-right">{p.progress}%</span>
                  </div>
                  <span className="text-xs text-slate-500">{p.timeline}</span>
                </div>
              );
            })}
          </div>

          {/* NIST FIPS Cards */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">NIST PQC Standards</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {nistCards.map((n) => (
                <div key={n.id} className="rounded-xl border border-slate-700 bg-slate-800/50 p-5 flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-blue-400 bg-blue-500/10 border border-blue-500/20 rounded px-2 py-0.5">{n.fips}</span>
                    <span className={cn(
                      "text-xs font-medium rounded-full px-2 py-0.5 border",
                      n.status === "Finalized" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                      n.status === "Draft" ? "bg-yellow-500/10 text-yellow-400 border-yellow-500/20" :
                      "bg-slate-600/10 text-slate-400 border-slate-600/20"
                    )}>
                      {n.status}
                    </span>
                  </div>
                  <h4 className="text-sm font-semibold text-white">{n.algorithm}</h4>
                  <p className="text-xs text-slate-400">{n.type}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
