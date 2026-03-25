"use client";
import { useState } from "react";
import { useFindings } from "@/lib/hooks/use-findings";
import { bulkUpdateFindings } from "@/lib/hooks/use-suppression";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import type { Severity, FindingStatus } from "@/lib/types";
import Link from "next/link";
import { Download } from "lucide-react";
import { LastSyncBanner } from "@/components/scanner/last-sync-banner";

const SEVERITY_OPTIONS: Severity[] = ["critical", "high", "medium", "low", "info"];
const STATUS_OPTIONS: FindingStatus[] = ["open", "in_progress", "resolved", "accepted", "suppressed"];

export default function FindingsPage() {
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("open");
  const [page, setPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkLoading, setBulkLoading] = useState(false);

  const { findings, total, pages, isLoading, error, mutate } = useFindings({
    severity: severityFilter || undefined,
    status: statusFilter || undefined,
    page,
    page_size: 50,
  });

  function toggleSelect(id: string) {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (selectedIds.size === (findings?.length ?? 0)) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(findings?.map(f => f.id) ?? []));
    }
  }

  function buildExportUrl() {
    const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const params = new URLSearchParams();
    if (severityFilter) params.set("severity", severityFilter);
    if (statusFilter) params.set("status", statusFilter);
    return `${API}/api/v1/findings/export?${params.toString()}`;
  }

  async function handleBulkAction(status: string) {
    if (bulkLoading) return;
    const ids = Array.from(selectedIds);
    setBulkLoading(true);
    try {
      await bulkUpdateFindings(ids, status);
      setSelectedIds(new Set());
      mutate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Bulk update failed");
    } finally {
      setBulkLoading(false);
    }
  }

  const allSelected = (findings?.length ?? 0) > 0 && selectedIds.size === (findings?.length ?? 0);
  const someSelected = selectedIds.size > 0 && !allSelected;

  return (
    <div className="space-y-4">
      <LastSyncBanner />
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Findings</h1>
          <p className="text-sm text-slate-500 mt-0.5">{total ?? 0} findings match current filters</p>
        </div>
        <button
          onClick={() => {
            const url = buildExportUrl();
            const a = document.createElement("a");
            a.href = url;
            a.download = "findings-export.csv";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
          }}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
        >
          <Download className="h-4 w-4" />
          Export CSV
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <select
          value={severityFilter}
          onChange={(e) => { setSeverityFilter(e.target.value); setPage(1); }}
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All severities</option>
          {SEVERITY_OPTIONS.map(s => <option key={s} value={s} className="capitalize">{s}</option>)}
        </select>

        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All statuses</option>
          {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center p-12"><Spinner className="h-6 w-6" /></div>
        ) : error ? (
          <div className="p-6 text-center text-sm text-red-500">Failed to load findings</div>
        ) : !findings?.length ? (
          <div className="p-12 text-center text-sm text-slate-500">No findings match the current filters</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="px-4 py-3 w-10">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    ref={el => { if (el) el.indeterminate = someSelected; }}
                    onChange={toggleSelectAll}
                    className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                  />
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Severity</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Title</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Resource</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden lg:table-cell">Risk</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden lg:table-cell">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {findings.map((finding) => (
                <tr
                  key={finding.id}
                  className={`hover:bg-slate-50 transition-colors ${selectedIds.has(finding.id) ? "bg-blue-50/50" : ""}`}
                >
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(finding.id)}
                      onChange={() => toggleSelect(finding.id)}
                      className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={finding.severity}>{finding.severity}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Link href={`/dashboard/findings/${finding.id}`} className="font-medium text-slate-800 hover:text-blue-600 line-clamp-2">
                      {finding.title}
                    </Link>
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    <p className="text-xs text-slate-500 font-mono truncate max-w-[200px]">
                      {finding.resource_arn ?? finding.resource_type ?? "—"}
                    </p>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={finding.status as any}>{finding.status.replace("_", " ")}</Badge>
                  </td>
                  <td className="px-4 py-3 hidden lg:table-cell">
                    <span className="font-mono text-xs text-slate-600">{finding.risk_score?.toFixed(1) ?? "—"}</span>
                  </td>
                  <td className="px-4 py-3 hidden lg:table-cell">
                    <span className="text-xs text-slate-400">{finding.primary_source.replace("_", " ")}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {pages && pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-500">Page {page} of {pages}</p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm disabled:opacity-40 hover:bg-slate-50"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(p => Math.min(pages, p + 1))}
              disabled={page === pages}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm disabled:opacity-40 hover:bg-slate-50"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Bulk Action Bar */}
      {selectedIds.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-3 bg-slate-900 text-white rounded-2xl px-5 py-3 shadow-2xl border border-slate-700 z-50">
          <span className="text-sm font-medium">{selectedIds.size} selected</span>
          <div className="w-px h-4 bg-slate-600" />
          <button
            onClick={() => handleBulkAction("resolved")}
            disabled={bulkLoading}
            className="text-sm text-green-400 hover:text-green-300 transition-colors disabled:opacity-50"
          >
            Mark Resolved
          </button>
          <button
            onClick={() => handleBulkAction("accepted")}
            disabled={bulkLoading}
            className="text-sm text-blue-400 hover:text-blue-300 transition-colors disabled:opacity-50"
          >
            Accept Risk
          </button>
          <button
            onClick={() => handleBulkAction("in_progress")}
            disabled={bulkLoading}
            className="text-sm text-amber-400 hover:text-amber-300 transition-colors disabled:opacity-50"
          >
            In Progress
          </button>
          <div className="w-px h-4 bg-slate-600" />
          <button
            onClick={() => setSelectedIds(new Set())}
            className="text-sm text-slate-400 hover:text-white transition-colors"
          >
            Clear
          </button>
        </div>
      )}
    </div>
  );
}
