"use client";
import { useState } from "react";
import { ClipboardList } from "lucide-react";
import { useAuditLog } from "@/lib/hooks/use-audit-log";
import type { AuditLog } from "@/lib/types";

// ── Action metadata ──────────────────────────────────────────────────────

const ACTION_OPTIONS = [
  "user.invited",
  "user.role_changed",
  "user.deactivated",
  "aws_account.created",
  "aws_account.deleted",
  "finding.status_changed",
  "workspace.renamed",
] as const;

const ACTION_COLORS: Record<string, string> = {
  "user.invited":           "bg-blue-100 text-blue-700",
  "user.role_changed":      "bg-blue-100 text-blue-700",
  "user.deactivated":       "bg-red-100 text-red-700",
  "aws_account.created":    "bg-green-100 text-green-700",
  "aws_account.deleted":    "bg-red-100 text-red-700",
  "finding.status_changed": "bg-amber-100 text-amber-700",
  "workspace.renamed":      "bg-purple-100 text-purple-700",
};

const ACTION_LABELS: Record<string, string> = {
  "user.invited":           "User Invited",
  "user.role_changed":      "Role Changed",
  "user.deactivated":       "User Deactivated",
  "aws_account.created":    "Account Added",
  "aws_account.deleted":    "Account Removed",
  "finding.status_changed": "Finding Updated",
  "workspace.renamed":      "Workspace Renamed",
};

// ── Helpers ───────────────────────────────────────────────────────────────

function formatTimestamp(dateStr: string): string {
  return new Date(dateStr).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

function renderDetail(action: string, detail: Record<string, unknown> | null): string {
  if (!detail) return "—";
  if (action === "user.invited") return `Invited ${detail.invited_email} as ${detail.role}`;
  if (action === "user.role_changed") return `${detail.old_role} → ${detail.new_role}`;
  if (action === "user.deactivated") return `${detail.email}`;
  if (action === "aws_account.created") return `Account ${detail.account_id ?? ""}`;
  if (action === "aws_account.deleted") return `Account removed`;
  if (action === "finding.status_changed") return `${detail.old_status} → ${detail.new_status}`;
  if (action === "workspace.renamed") return `"${detail.new_name}"`;
  return JSON.stringify(detail).slice(0, 60);
}

// ── Skeleton ──────────────────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <tr className="border-b border-slate-100">
      {[...Array(5)].map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 rounded bg-slate-100 animate-pulse" style={{ width: i === 1 ? "120px" : i === 2 ? "80px" : "100px" }} />
        </td>
      ))}
    </tr>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function AuditLogPage() {
  const [page, setPage] = useState(1);
  const [actionFilter, setActionFilter] = useState("");
  const [actorSearch, setActorSearch] = useState("");

  const PAGE_SIZE = 50;
  const { data, isLoading, error } = useAuditLog(page, PAGE_SIZE);

  const items: AuditLog[] = (data?.items ?? []).filter((item) => {
    const matchesAction = actionFilter ? item.action === actionFilter : true;
    const matchesActor = actorSearch
      ? item.actor_email.toLowerCase().includes(actorSearch.toLowerCase())
      : true;
    return matchesAction && matchesActor;
  });

  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">Audit Log</h1>
        <p className="text-sm text-slate-500 mt-0.5">Track all actions across your workspace</p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <select
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All actions</option>
          {ACTION_OPTIONS.map((a) => (
            <option key={a} value={a}>{ACTION_LABELS[a] ?? a}</option>
          ))}
        </select>

        <input
          type="text"
          value={actorSearch}
          onChange={(e) => { setActorSearch(e.target.value); setPage(1); }}
          placeholder="Search by actor email…"
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 w-56"
        />
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
        {error ? (
          <div className="p-6 text-center text-sm text-red-500">Failed to load audit log</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Timestamp</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Actor</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Action</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Resource</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden lg:table-cell">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <>
                  <SkeletonRow />
                  <SkeletonRow />
                  <SkeletonRow />
                </>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={5}>
                    <div className="flex flex-col items-center justify-center py-16 text-slate-400">
                      <ClipboardList className="h-10 w-10 mb-3 opacity-40" />
                      <p className="text-sm font-medium">No audit events yet</p>
                      <p className="text-xs mt-1 text-slate-500">Actions taken in your workspace will appear here</p>
                    </div>
                  </td>
                </tr>
              ) : (
                items.map((item) => {
                  const colorClass = ACTION_COLORS[item.action] ?? "bg-slate-100 text-slate-600";
                  const label = ACTION_LABELS[item.action] ?? item.action;
                  return (
                    <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="text-xs text-slate-500 font-mono">{formatTimestamp(item.created_at)}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-slate-700 truncate max-w-[160px] block">{item.actor_email}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colorClass}`}>
                          {label}
                        </span>
                      </td>
                      <td className="px-4 py-3 hidden md:table-cell">
                        <span className="text-xs text-slate-500 font-mono truncate max-w-[160px] block">
                          {item.resource_type && item.resource_id
                            ? `${item.resource_type}/${item.resource_id}`
                            : item.resource_type ?? item.resource_id ?? "—"}
                        </span>
                      </td>
                      <td className="px-4 py-3 hidden lg:table-cell">
                        <span className="text-xs text-slate-500 truncate max-w-[240px] block">
                          {renderDetail(item.action, item.detail)}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-500">
            Page {page} of {pages} &middot; {total} total events
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm disabled:opacity-40 hover:bg-slate-50"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(pages, p + 1))}
              disabled={page === pages}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm disabled:opacity-40 hover:bg-slate-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
