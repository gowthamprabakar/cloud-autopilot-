"use client";

import { useState } from "react";
import { ScanFace, ShieldCheck, AlertTriangle, Fingerprint, KeyRound } from "lucide-react";
import { useModuleEndpoint } from "@/lib/hooks/use-module-data";
import { cn } from "@/lib/utils";

// -- Data hooks ---------------------------------------------------------------

function useDeepfakeData() {
  const risk = useModuleEndpoint("deepfake", "risk");
  const authAudit = useModuleEndpoint("deepfake", "auth-audit");
  return { risk, authAudit };
}

// -- Types --------------------------------------------------------------------

interface AttackScenario {
  id: string;
  name: string;
  description: string;
  vector: string;
  likelihood: "Critical" | "High" | "Medium" | "Low";
  impact: "Critical" | "High" | "Medium" | "Low";
  mitigated: boolean;
}

interface AuthMethod {
  id: string;
  method: string;
  category: "Biometric" | "Knowledge" | "Possession" | "Behavioral";
  deepfakeResistance: number;
  deployed: boolean;
  coverage: number;
  fido2Compatible: boolean;
}

// -- Fallback data ------------------------------------------------------------

const FALLBACK_SCENARIOS: AttackScenario[] = [
  { id: "1", name: "Voice Cloning for MFA Bypass", description: "AI-generated voice clone used to defeat voice-based authentication and social-engineer helpdesk resets", vector: "Phone / VoIP", likelihood: "Critical", impact: "Critical", mitigated: false },
  { id: "2", name: "Real-time Face Swap (KYC)", description: "Live deepfake video injection during identity verification to impersonate legitimate users", vector: "Video Call / KYC", likelihood: "High", impact: "Critical", mitigated: false },
  { id: "3", name: "CEO Impersonation for Wire Transfer", description: "Deepfake video/audio of executive authorizing fraudulent financial transactions", vector: "Video / Audio", likelihood: "High", impact: "High", mitigated: true },
  { id: "4", name: "Synthetic Identity Creation", description: "AI-generated face photos combined with stolen PII to create entirely new fraudulent identities", vector: "Document Forgery", likelihood: "Medium", impact: "High", mitigated: false },
  { id: "5", name: "Liveness Detection Bypass", description: "Adversarial attacks against liveness detection using 3D masks or neural rendering pipelines", vector: "Biometric System", likelihood: "Medium", impact: "Medium", mitigated: true },
];

const FALLBACK_AUTH: AuthMethod[] = [
  { id: "1", method: "FIDO2 / WebAuthn", category: "Possession", deepfakeResistance: 98, deployed: true, coverage: 62, fido2Compatible: true },
  { id: "2", method: "Hardware Security Key", category: "Possession", deepfakeResistance: 99, deployed: true, coverage: 34, fido2Compatible: true },
  { id: "3", method: "Passkeys (Platform)", category: "Possession", deepfakeResistance: 96, deployed: true, coverage: 48, fido2Compatible: true },
  { id: "4", method: "Fingerprint Scan", category: "Biometric", deepfakeResistance: 88, deployed: true, coverage: 72, fido2Compatible: true },
  { id: "5", method: "3D Face Recognition", category: "Biometric", deepfakeResistance: 82, deployed: true, coverage: 55, fido2Compatible: false },
  { id: "6", method: "Iris Scan", category: "Biometric", deepfakeResistance: 91, deployed: false, coverage: 8, fido2Compatible: false },
  { id: "7", method: "Voice Authentication", category: "Biometric", deepfakeResistance: 35, deployed: true, coverage: 41, fido2Compatible: false },
  { id: "8", method: "SMS OTP", category: "Possession", deepfakeResistance: 45, deployed: true, coverage: 89, fido2Compatible: false },
  { id: "9", method: "Knowledge-Based Auth (KBA)", category: "Knowledge", deepfakeResistance: 22, deployed: true, coverage: 78, fido2Compatible: false },
  { id: "10", method: "Behavioral Biometrics", category: "Behavioral", deepfakeResistance: 76, deployed: false, coverage: 12, fido2Compatible: false },
  { id: "11", method: "Liveness Detection", category: "Biometric", deepfakeResistance: 71, deployed: true, coverage: 55, fido2Compatible: false },
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

// -- Main page ----------------------------------------------------------------

export default function DeepfakePage() {
  const { risk, authAudit } = useDeepfakeData();

  const scenarios: AttackScenario[] = (risk.data as any)?.scenarios ?? FALLBACK_SCENARIOS;
  const authMethods: AuthMethod[] = (authAudit.data as any)?.methods ?? FALLBACK_AUTH;

  const riskScore = Math.round(
    scenarios.reduce((s, sc) => {
      const w: Record<string, number> = { Critical: 25, High: 18, Medium: 10, Low: 4 };
      return s + (w[sc.likelihood] ?? 4) + (w[sc.impact] ?? 4);
    }, 0) / scenarios.length
  );
  const attackCount = scenarios.length;
  const fido2Coverage = Math.round(
    (authMethods.filter((a) => a.fido2Compatible && a.deployed).reduce((s, a) => s + a.coverage, 0)) /
    Math.max(authMethods.filter((a) => a.fido2Compatible && a.deployed).length, 1)
  );
  const resistanceScore = Math.round(
    authMethods.filter((a) => a.deployed).reduce((s, a) => s + a.deepfakeResistance, 0) /
    Math.max(authMethods.filter((a) => a.deployed).length, 1)
  );

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-900 min-h-screen">
      {/* Header */}
      <div className="flex items-center gap-3">
        <ScanFace className="h-6 w-6 text-blue-400" />
        <div>
          <h1 className="text-xl font-bold text-white">Deepfake Identity Fraud Protection</h1>
          <p className="text-sm text-slate-400 mt-0.5">Attack scenario modeling, authentication audit &amp; deepfake resistance scoring</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard icon={AlertTriangle} label="Risk Score" value={riskScore} accent="bg-red-600/80" />
        <SummaryCard icon={ScanFace} label="Attack Scenarios" value={attackCount} accent="bg-orange-600/80" />
        <SummaryCard icon={KeyRound} label="FIDO2 Coverage" value={`${fido2Coverage}%`} accent="bg-blue-600/80" />
        <SummaryCard icon={ShieldCheck} label="Resistance Score" value={`${resistanceScore}%`} accent="bg-emerald-600/80" />
      </div>

      {/* Attack Scenarios Section */}
      <div className="space-y-4">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Attack Scenarios</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {scenarios.map((sc) => (
            <div key={sc.id} className="rounded-xl border border-slate-700 bg-slate-800/50 p-5 flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white">{sc.name}</h3>
                {sc.mitigated ? (
                  <span className="inline-flex items-center rounded-full border border-emerald-500/20 bg-emerald-500/10 text-emerald-400 px-2 py-0.5 text-xs font-medium">Mitigated</span>
                ) : (
                  <span className="inline-flex items-center rounded-full border border-red-500/20 bg-red-500/10 text-red-400 px-2 py-0.5 text-xs font-medium">Active Risk</span>
                )}
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">{sc.description}</p>
              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-500">Vector:</span>
                <span className="font-medium text-slate-300 bg-slate-700/50 rounded px-2 py-0.5">{sc.vector}</span>
              </div>
              <div className="flex items-center gap-3 mt-auto pt-2 border-t border-slate-700/50">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-slate-500">Likelihood:</span>
                  <RiskBadge level={sc.likelihood} />
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-slate-500">Impact:</span>
                  <RiskBadge level={sc.impact} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Authentication Audit Section */}
      <div className="space-y-4">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Authentication Audit</h2>
        <div className="rounded-xl border border-slate-700 bg-slate-800/40 overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-800/80 text-slate-400 text-xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Method</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Deepfake Resistance</th>
                <th className="px-4 py-3 text-center">Deployed</th>
                <th className="px-4 py-3 text-center">Coverage</th>
                <th className="px-4 py-3 text-center">FIDO2</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {authMethods.map((a) => {
                const barColor = a.deepfakeResistance >= 80 ? "bg-emerald-500" : a.deepfakeResistance >= 50 ? "bg-yellow-500" : "bg-red-500";
                const textColor = a.deepfakeResistance >= 80 ? "text-emerald-400" : a.deepfakeResistance >= 50 ? "text-yellow-400" : "text-red-400";
                return (
                  <tr key={a.id} className="hover:bg-slate-800/60 transition-colors">
                    <td className="px-4 py-3 text-white font-medium">{a.method}</td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-medium text-slate-300 bg-slate-700/50 rounded px-2 py-0.5">{a.category}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="flex-1 h-2 rounded-full bg-slate-700 overflow-hidden">
                          <div className={cn("h-full rounded-full", barColor)} style={{ width: `${a.deepfakeResistance}%` }} />
                        </div>
                        <span className={cn("text-xs font-semibold w-10 text-right", textColor)}>{a.deepfakeResistance}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={a.deployed ? "text-emerald-400" : "text-slate-500"}>{a.deployed ? "Yes" : "No"}</span>
                    </td>
                    <td className="px-4 py-3 text-center text-slate-300">{a.coverage}%</td>
                    <td className="px-4 py-3 text-center">
                      {a.fido2Compatible ? (
                        <span className="inline-flex items-center rounded-full border border-blue-500/20 bg-blue-500/10 text-blue-400 px-2 py-0.5 text-xs font-medium">FIDO2</span>
                      ) : (
                        <span className="text-slate-600">-</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
