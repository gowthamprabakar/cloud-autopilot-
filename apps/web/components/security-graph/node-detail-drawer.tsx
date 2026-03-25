"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { apiClient } from "@/lib/api-client";
import type { SecurityGraphNode } from "@/lib/types";

interface Props {
  node: SecurityGraphNode | null;
  onClose: () => void;
  findingTitles?: Record<string, string>;
}

function MetaRow({ k, v }: { k: string; v: unknown }) {
  const display = typeof v === "object" ? JSON.stringify(v) : String(v);
  return (
    <tr className="border-b border-slate-100 last:border-0">
      <td className="py-1.5 pr-3 text-xs font-medium text-slate-500 capitalize align-top whitespace-nowrap">
        {k.replace(/_/g, " ")}
      </td>
      <td className="py-1.5 text-xs text-slate-700 break-all font-mono">{display}</td>
    </tr>
  );
}

export default function NodeDetailDrawer({ node, onClose, findingTitles = {} }: Props) {
  const router = useRouter();
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState(false);

  if (!node) return null;

  const metaEntries = Object.entries(node.metadata ?? {});
  const riskScore = node.risk_score ?? 0;

  const riskBarColor =
    riskScore >= 8 ? "bg-red-500" :
    riskScore >= 6 ? "bg-orange-500" :
    riskScore >= 4 ? "bg-amber-500" :
    riskScore >= 2 ? "bg-yellow-400" : "bg-green-500";

  async function handleGenerateIntelligence() {
    if (!node?.finding_ids.length) return;
    setGenerating(true);
    try {
      // Generate for the first finding on this node
      await apiClient.post(`/api/v1/intelligence/findings/${node.finding_ids[0]}`, {});
      setGenerated(true);
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="fixed inset-x-0 bottom-0 z-40 flex justify-center pointer-events-none">
      <div
        className={cn(
          "w-full max-w-3xl pointer-events-auto bg-white border border-slate-200 border-b-0 rounded-t-xl shadow-2xl transition-transform",
          node ? "translate-y-0" : "translate-y-full"
        )}
        style={{ height: 350 }}
      >
        {/* Handle bar */}
        <div className="flex justify-center pt-2 pb-1">
          <div className="h-1 w-10 rounded-full bg-slate-200" />
        </div>

        <div className="flex h-full flex-col px-5 pb-4 overflow-hidden">
          {/* Header */}
          <div className="flex items-start justify-between gap-3 mb-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-bold text-slate-900 truncate">
                  {node.resource_name ?? node.node_type}
                </span>
                {node.region && (
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                    {node.region}
                  </span>
                )}
                {node.is_internet_facing && (
                  <span className="rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-700">⚡ Internet-facing</span>
                )}
                {node.is_sensitive_data && (
                  <span className="rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700">🔒 Sensitive Data</span>
                )}
              </div>
              {node.resource_arn && (
                <p className="text-xs font-mono text-slate-400 truncate mt-0.5" title={node.resource_arn}>
                  {node.resource_arn.length > 70 ? node.resource_arn.slice(0, 70) + "…" : node.resource_arn}
                </p>
              )}
            </div>
            <button onClick={onClose} className="shrink-0 rounded-full p-1 hover:bg-slate-100 transition-colors">
              <X className="h-4 w-4 text-slate-500" />
            </button>
          </div>

          {/* Scrollable content */}
          <div className="flex-1 overflow-y-auto grid grid-cols-2 gap-4">
            {/* Left col */}
            <div className="space-y-3">
              {/* Risk score */}
              {node.risk_score !== null && (
                <div>
                  <p className="text-xs font-medium text-slate-500 mb-1">Risk Score</p>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 rounded-full bg-slate-100">
                      <div
                        className={cn("h-2 rounded-full transition-all", riskBarColor)}
                        style={{ width: `${(riskScore / 10) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs font-bold text-slate-700">{riskScore.toFixed(1)}/10</span>
                  </div>
                </div>
              )}

              {/* Findings */}
              {node.finding_ids.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-slate-500 mb-1">
                    {node.finding_ids.length} finding{node.finding_ids.length !== 1 ? "s" : ""} on this resource
                  </p>
                  <ul className="space-y-1 mb-2">
                    {node.finding_ids.slice(0, 3).map((fid) => (
                      <li key={fid} className="text-xs text-slate-600 truncate">
                        {findingTitles[fid] ?? fid}
                      </li>
                    ))}
                  </ul>
                  <button
                    onClick={() => router.push(`/dashboard/findings?resource_arn=${encodeURIComponent(node.resource_arn ?? "")}`)}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    View findings →
                  </button>
                </div>
              )}

              {/* Generate intelligence */}
              {node.finding_ids.length > 0 && (
                <button
                  onClick={handleGenerateIntelligence}
                  disabled={generating || generated}
                  className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {generated ? "Analysis Queued ✓" : generating ? "Generating..." : "Generate Intelligence"}
                </button>
              )}
            </div>

            {/* Right col — metadata */}
            {metaEntries.length > 0 && (
              <div>
                <p className="text-xs font-medium text-slate-500 mb-1">Metadata</p>
                <table className="w-full">
                  <tbody>
                    {metaEntries.slice(0, 8).map(([k, v]) => (
                      <MetaRow key={k} k={k} v={v} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
