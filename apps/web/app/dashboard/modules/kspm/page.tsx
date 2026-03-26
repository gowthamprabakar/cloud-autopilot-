"use client";

import { useState } from "react";
import { Shield, Network, KeyRound, Bug, Container } from "lucide-react";
import { useModuleEndpoint } from "@/lib/hooks/use-module-data";
import { cn } from "@/lib/utils";

// -- Data hooks ---------------------------------------------------------------

function useKspmData() {
  const rbac = useModuleEndpoint("kspm", "rbac");
  const network = useModuleEndpoint("kspm", "network");
  const admission = useModuleEndpoint("kspm", "admission");
  const podPivots = useModuleEndpoint("kspm", "pod-pivots");
  return { rbac, network, admission, podPivots };
}

// -- Types --------------------------------------------------------------------

interface RbacViolation {
  id: string;
  cluster: string;
  namespace: string;
  subject: string;
  kind: "ClusterRole" | "Role";
  issue: "Wildcard Verbs" | "Wildcard Resources" | "Privilege Escalation" | "Secrets Access";
  severity: "Critical" | "High" | "Medium";
}

interface NetworkGap {
  id: string;
  cluster: string;
  namespace: string;
  policyCount: number;
  podsCovered: number;
  podsTotal: number;
  coveragePercent: number;
}

interface AdmissionRule {
  id: string;
  cluster: string;
  engine: "PSA" | "OPA" | "Gatekeeper" | "Kyverno";
  policy: string;
  enforced: boolean;
  violations: number;
  lastViolation: string;
}

interface PodPivot {
  id: string;
  cluster: string;
  namespace: string;
  pod: string;
  path: "IMDS" | "IRSA" | "Service Account Token" | "Host PID/Network";
  targetRole: string;
  riskScore: number;
}

// -- Fallback data ------------------------------------------------------------

const FALLBACK_RBAC: RbacViolation[] = [
  { id: "1", cluster: "prod-us-east", namespace: "kube-system", subject: "cluster-admin-legacy", kind: "ClusterRole", issue: "Wildcard Verbs", severity: "Critical" },
  { id: "2", cluster: "prod-us-east", namespace: "default", subject: "deploy-bot", kind: "ClusterRole", issue: "Privilege Escalation", severity: "Critical" },
  { id: "3", cluster: "prod-eu-west", namespace: "monitoring", subject: "prometheus-sa", kind: "Role", issue: "Secrets Access", severity: "High" },
  { id: "4", cluster: "staging", namespace: "ci-cd", subject: "jenkins-runner", kind: "ClusterRole", issue: "Wildcard Resources", severity: "High" },
  { id: "5", cluster: "prod-us-east", namespace: "payments", subject: "payment-svc-sa", kind: "Role", issue: "Secrets Access", severity: "Medium" },
  { id: "6", cluster: "dev", namespace: "default", subject: "dev-admin", kind: "ClusterRole", issue: "Wildcard Verbs", severity: "Medium" },
];

const FALLBACK_NETWORK: NetworkGap[] = [
  { id: "1", cluster: "prod-us-east", namespace: "default", policyCount: 0, podsCovered: 0, podsTotal: 14, coveragePercent: 0 },
  { id: "2", cluster: "prod-us-east", namespace: "payments", policyCount: 3, podsCovered: 8, podsTotal: 10, coveragePercent: 80 },
  { id: "3", cluster: "prod-eu-west", namespace: "frontend", policyCount: 1, podsCovered: 3, podsTotal: 6, coveragePercent: 50 },
  { id: "4", cluster: "prod-eu-west", namespace: "backend", policyCount: 5, podsCovered: 12, podsTotal: 12, coveragePercent: 100 },
  { id: "5", cluster: "staging", namespace: "default", policyCount: 0, podsCovered: 0, podsTotal: 22, coveragePercent: 0 },
  { id: "6", cluster: "dev", namespace: "default", policyCount: 0, podsCovered: 0, podsTotal: 8, coveragePercent: 0 },
];

const FALLBACK_ADMISSION: AdmissionRule[] = [
  { id: "1", cluster: "prod-us-east", engine: "PSA", policy: "baseline", enforced: true, violations: 3, lastViolation: "2h ago" },
  { id: "2", cluster: "prod-us-east", engine: "OPA", policy: "no-privileged-containers", enforced: true, violations: 0, lastViolation: "N/A" },
  { id: "3", cluster: "prod-eu-west", engine: "Gatekeeper", policy: "required-labels", enforced: true, violations: 12, lastViolation: "15m ago" },
  { id: "4", cluster: "prod-eu-west", engine: "Gatekeeper", policy: "allowed-repos", enforced: false, violations: 8, lastViolation: "1h ago" },
  { id: "5", cluster: "staging", engine: "PSA", policy: "restricted", enforced: false, violations: 27, lastViolation: "5m ago" },
  { id: "6", cluster: "dev", engine: "Kyverno", policy: "disallow-latest-tag", enforced: true, violations: 5, lastViolation: "3h ago" },
];

const FALLBACK_PIVOTS: PodPivot[] = [
  { id: "1", cluster: "prod-us-east", namespace: "default", pod: "legacy-api-7b8c", path: "IMDS", targetRole: "arn:aws:iam::123:role/EC2-Admin", riskScore: 95 },
  { id: "2", cluster: "prod-us-east", namespace: "payments", pod: "payment-worker-4d", path: "IRSA", targetRole: "arn:aws:iam::123:role/S3-Full", riskScore: 88 },
  { id: "3", cluster: "prod-eu-west", namespace: "backend", pod: "data-processor-9f", path: "Service Account Token", targetRole: "cluster-admin", riskScore: 92 },
  { id: "4", cluster: "staging", namespace: "ci-cd", pod: "jenkins-agent-2a", path: "Host PID/Network", targetRole: "node-proxy", riskScore: 78 },
  { id: "5", cluster: "dev", namespace: "default", pod: "debug-shell-x1", path: "IMDS", targetRole: "arn:aws:iam::123:role/Dev-Admin", riskScore: 65 },
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

// -- Tabs ---------------------------------------------------------------------

const TABS = ["RBAC", "Network Policies", "Admission Control", "Pod Pivots"] as const;
type Tab = (typeof TABS)[number];

// -- Main page ----------------------------------------------------------------

export default function KspmPage() {
  const { rbac, network, admission, podPivots } = useKspmData();
  const [activeTab, setActiveTab] = useState<Tab>("RBAC");

  const rbacList: RbacViolation[] = (rbac.data as any)?.items ?? FALLBACK_RBAC;
  const networkList: NetworkGap[] = (network.data as any)?.items ?? FALLBACK_NETWORK;
  const admissionList: AdmissionRule[] = (admission.data as any)?.items ?? FALLBACK_ADMISSION;
  const pivotList: PodPivot[] = (podPivots.data as any)?.items ?? FALLBACK_PIVOTS;

  const clusters = new Set([...rbacList.map((r) => r.cluster), ...networkList.map((n) => n.cluster)]).size;
  const rbacViolations = rbacList.length;
  const networkGaps = networkList.filter((n) => n.coveragePercent < 100).length;
  const podPivotCount = pivotList.length;

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-900 min-h-screen">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Container className="h-6 w-6 text-blue-400" />
        <div>
          <h1 className="text-xl font-bold text-white">Kubernetes Security Posture Management</h1>
          <p className="text-sm text-slate-400 mt-0.5">RBAC analysis, network policy coverage, admission control &amp; lateral movement paths</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard icon={Container} label="Clusters" value={clusters} accent="bg-blue-600/80" />
        <SummaryCard icon={KeyRound} label="RBAC Violations" value={rbacViolations} accent="bg-red-600/80" />
        <SummaryCard icon={Network} label="Network Gaps" value={networkGaps} accent="bg-orange-600/80" />
        <SummaryCard icon={Bug} label="Pod Pivots" value={podPivotCount} accent="bg-purple-600/80" />
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

      {/* RBAC Tab */}
      {activeTab === "RBAC" && (
        <div className="rounded-xl border border-slate-700 bg-slate-800/40 overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-800/80 text-slate-400 text-xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Cluster</th>
                <th className="px-4 py-3">Namespace</th>
                <th className="px-4 py-3">Subject</th>
                <th className="px-4 py-3">Kind</th>
                <th className="px-4 py-3">Issue</th>
                <th className="px-4 py-3 text-center">Severity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {rbacList.map((r) => (
                <tr key={r.id} className="hover:bg-slate-800/60 transition-colors">
                  <td className="px-4 py-3 text-white font-medium">{r.cluster}</td>
                  <td className="px-4 py-3 text-slate-300 font-mono text-xs">{r.namespace}</td>
                  <td className="px-4 py-3 text-slate-300">{r.subject}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs font-medium text-slate-300 bg-slate-700/50 rounded px-2 py-0.5">{r.kind}</span>
                  </td>
                  <td className="px-4 py-3 text-slate-300">{r.issue}</td>
                  <td className="px-4 py-3 text-center"><SeverityBadge severity={r.severity} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Network Policies Tab */}
      {activeTab === "Network Policies" && (
        <div className="rounded-xl border border-slate-700 bg-slate-800/40 overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-800/80 text-slate-400 text-xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Cluster</th>
                <th className="px-4 py-3">Namespace</th>
                <th className="px-4 py-3 text-center">Policies</th>
                <th className="px-4 py-3 text-center">Pods Covered</th>
                <th className="px-4 py-3">Coverage</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {networkList.map((n) => {
                const barColor = n.coveragePercent === 100 ? "bg-emerald-500" : n.coveragePercent >= 50 ? "bg-yellow-500" : "bg-red-500";
                const textColor = n.coveragePercent === 100 ? "text-emerald-400" : n.coveragePercent >= 50 ? "text-yellow-400" : "text-red-400";
                return (
                  <tr key={n.id} className="hover:bg-slate-800/60 transition-colors">
                    <td className="px-4 py-3 text-white font-medium">{n.cluster}</td>
                    <td className="px-4 py-3 text-slate-300 font-mono text-xs">{n.namespace}</td>
                    <td className="px-4 py-3 text-center text-slate-300">{n.policyCount}</td>
                    <td className="px-4 py-3 text-center text-slate-300">{n.podsCovered}/{n.podsTotal}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="flex-1 h-2 rounded-full bg-slate-700 overflow-hidden">
                          <div className={cn("h-full rounded-full", barColor)} style={{ width: `${n.coveragePercent}%` }} />
                        </div>
                        <span className={cn("text-xs font-semibold w-10 text-right", textColor)}>{n.coveragePercent}%</span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Admission Control Tab */}
      {activeTab === "Admission Control" && (
        <div className="rounded-xl border border-slate-700 bg-slate-800/40 overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-800/80 text-slate-400 text-xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Cluster</th>
                <th className="px-4 py-3">Engine</th>
                <th className="px-4 py-3">Policy</th>
                <th className="px-4 py-3 text-center">Enforced</th>
                <th className="px-4 py-3 text-center">Violations</th>
                <th className="px-4 py-3">Last Violation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {admissionList.map((a) => (
                <tr key={a.id} className="hover:bg-slate-800/60 transition-colors">
                  <td className="px-4 py-3 text-white font-medium">{a.cluster}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs font-medium text-slate-300 bg-slate-700/50 rounded px-2 py-0.5">{a.engine}</span>
                  </td>
                  <td className="px-4 py-3 text-slate-300">{a.policy}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={a.enforced ? "text-emerald-400" : "text-red-400"}>{a.enforced ? "Yes" : "No"}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={cn("font-semibold", a.violations > 10 ? "text-red-400" : a.violations > 0 ? "text-yellow-400" : "text-emerald-400")}>
                      {a.violations}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{a.lastViolation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pod Pivots Tab */}
      {activeTab === "Pod Pivots" && (
        <div className="rounded-xl border border-slate-700 bg-slate-800/40 overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-800/80 text-slate-400 text-xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Cluster</th>
                <th className="px-4 py-3">Pod</th>
                <th className="px-4 py-3">Pivot Path</th>
                <th className="px-4 py-3">Target Role</th>
                <th className="px-4 py-3 text-center">Risk Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {pivotList.map((p) => (
                <tr key={p.id} className="hover:bg-slate-800/60 transition-colors">
                  <td className="px-4 py-3 text-white font-medium">{p.cluster}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col">
                      <span className="text-slate-300 font-mono text-xs">{p.pod}</span>
                      <span className="text-slate-500 text-xs">{p.namespace}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn(
                      "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium",
                      p.path === "IMDS" ? "bg-red-500/10 text-red-400 border-red-500/20" :
                      p.path === "IRSA" ? "bg-orange-500/10 text-orange-400 border-orange-500/20" :
                      "bg-yellow-500/10 text-yellow-400 border-yellow-500/20"
                    )}>
                      {p.path}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-300 font-mono text-xs truncate max-w-[200px]">{p.targetRole}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={cn("font-semibold", p.riskScore > 85 ? "text-red-400" : p.riskScore > 70 ? "text-orange-400" : "text-yellow-400")}>
                      {p.riskScore}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
