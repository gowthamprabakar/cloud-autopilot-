"use client";

import { useState } from "react";
import {
  UserCog, ShieldAlert, ArrowRightLeft, Globe, KeyRound,
  AlertTriangle, ChevronRight, Users, Lock, Unlock,
} from "lucide-react";
import { useCIEMSummary, useCIEMEntities, useEscalationPaths } from "@/lib/hooks/use-ciem";
import type { CIEMEntity, EscalationPath } from "@/lib/hooks/use-ciem";
import { Spinner } from "@/components/ui/spinner";
import Link from "next/link";

// ── Helpers ───────────────────────────────────────────────────────────────────

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ");
}

const RISK_BADGE: Record<string, string> = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high:     "bg-orange-100 text-orange-700 border-orange-200",
  medium:   "bg-yellow-100 text-yellow-700 border-yellow-200",
  low:      "bg-blue-100 text-blue-700 border-blue-200",
};

const SCOPE_BADGE: Record<string, string> = {
  admin:   "bg-red-50 text-red-700 border-red-200",
  write:   "bg-orange-50 text-orange-600 border-orange-200",
  read:    "bg-green-50 text-green-700 border-green-200",
  limited: "bg-slate-50 text-slate-600 border-slate-200",
  unknown: "bg-slate-50 text-slate-400 border-slate-200",
};

const SEV_BADGE: Record<string, string> = {
  critical: "bg-red-100 text-red-700",
  high:     "bg-orange-100 text-orange-700",
  medium:   "bg-yellow-100 text-yellow-700",
  low:      "bg-blue-100 text-blue-700",
  info:     "bg-slate-100 text-slate-500",
};

// ── Stat Card ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, color }: { label: string; value: number | string; sub?: string; color?: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
      <p className="text-xs text-slate-500 font-medium mb-1">{label}</p>
      <p className={cn("text-2xl font-bold", color ?? "text-slate-800")}>{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}

// ── Entity Row ────────────────────────────────────────────────────────────────

function EntityRow({ entity }: { entity: CIEMEntity }) {
  const [expanded, setExpanded] = useState(false);
  const isRole = entity.type === "iam_role";

  return (
    <div className="border-b border-slate-100 last:border-0">
      <div
        className="flex items-center gap-3 px-4 py-3 hover:bg-slate-50 cursor-pointer transition-colors"
        onClick={() => setExpanded(e => !e)}
      >
        {/* Icon */}
        <div className={cn(
          "w-7 h-7 rounded-md flex items-center justify-center shrink-0",
          isRole ? "bg-purple-100" : "bg-blue-100"
        )}>
          {isRole ? <UserCog className="h-4 w-4 text-purple-600" /> : <Users className="h-4 w-4 text-blue-600" />}
        </div>

        {/* Name */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-800 truncate">{entity.name}</p>
          <p className="text-xs text-slate-400">{entity.type.replace("_", " ")}{entity.region ? ` · ${entity.region}` : ""}</p>
        </div>

        {/* Scope badge */}
        <span className={cn(
          "text-xs font-semibold capitalize px-2 py-0.5 rounded border shrink-0",
          SCOPE_BADGE[entity.permission_scope]
        )}>
          {entity.permission_scope}
        </span>

        {/* Escalation risk */}
        <span className={cn(
          "text-xs font-semibold capitalize px-2 py-0.5 rounded border shrink-0",
          RISK_BADGE[entity.escalation_risk]
        )}>
          {entity.escalation_risk}
        </span>

        {/* Flags */}
        <div className="flex items-center gap-1.5 shrink-0">
          {entity.is_internet_facing && (
            <span title="Internet-facing" className="text-red-500"><Globe className="h-3.5 w-3.5" /></span>
          )}
          {entity.has_mfa === false && (
            <span title="No MFA" className="text-orange-500"><Unlock className="h-3.5 w-3.5" /></span>
          )}
          {entity.has_mfa === true && (
            <span title="MFA enabled" className="text-green-500"><Lock className="h-3.5 w-3.5" /></span>
          )}
          {entity.open_findings > 0 && (
            <span className="text-xs bg-red-50 text-red-600 rounded px-1.5 py-0.5 font-semibold">
              {entity.open_findings}
            </span>
          )}
        </div>

        <ChevronRight className={cn("h-4 w-4 text-slate-300 transition-transform shrink-0", expanded && "rotate-90")} />
      </div>

      {expanded && (
        <div className="px-14 pb-3 space-y-2">
          {entity.resource_arn && (
            <p className="text-xs text-slate-500 font-mono break-all">{entity.resource_arn}</p>
          )}
          {entity.policies.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {entity.policies.map(p => (
                <span key={p} className="text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">{p}</span>
              ))}
            </div>
          )}
          {entity.escalation_patterns.length > 0 && (
            <div className="flex flex-wrap gap-1">
              <span className="text-xs text-red-600 font-semibold mr-1">Escalation signals:</span>
              {entity.escalation_patterns.map(p => (
                <span key={p} className="text-xs bg-red-50 text-red-700 px-1.5 py-0.5 rounded font-mono">{p}</span>
              ))}
            </div>
          )}
          <div className="flex gap-3 text-xs text-slate-400">
            <span>Risk score: <strong className="text-slate-600">{entity.risk_score?.toFixed(1) ?? "—"}</strong></span>
            <span>Cross-account: <strong className={entity.cross_account ? "text-orange-600" : "text-slate-600"}>{entity.cross_account ? "Yes" : "No"}</strong></span>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Escalation Path Row ───────────────────────────────────────────────────────

function PathRow({ path }: { path: EscalationPath }) {
  return (
    <div className="flex items-start gap-3 px-4 py-3 border-b border-slate-100 last:border-0 hover:bg-slate-50">
      <div className={cn(
        "mt-0.5 shrink-0 w-6 h-6 rounded flex items-center justify-center",
        path.is_attack_path ? "bg-red-100" : "bg-orange-50"
      )}>
        <ShieldAlert className={cn("h-3.5 w-3.5", path.is_attack_path ? "text-red-600" : "text-orange-500")} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 flex-wrap mb-0.5">
          <span className="text-xs font-medium text-slate-700 truncate">{path.source}</span>
          <ArrowRightLeft className="h-3 w-3 text-slate-400 shrink-0" />
          <span className="text-xs text-slate-500 truncate">{path.target}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">{path.pattern}</span>
          <span className={cn("text-[10px] font-semibold capitalize px-1.5 py-0.5 rounded", SEV_BADGE[path.severity])}>
            {path.severity}
          </span>
          {path.is_attack_path && (
            <span className="text-[10px] bg-red-50 text-red-600 font-semibold px-1.5 py-0.5 rounded">Attack Path</span>
          )}
          {path.finding_title && (
            <span className="text-[10px] text-slate-400 truncate max-w-[200px]">{path.finding_title}</span>
          )}
        </div>
      </div>

      {path.risk_contribution != null && (
        <span className="text-xs font-bold text-slate-500 shrink-0">{path.risk_contribution.toFixed(1)}</span>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

type Tab = "entities" | "escalation";

export default function CIEMPage() {
  const { summary, isLoading: sumLoading } = useCIEMSummary();
  const { entities, isLoading: entLoading } = useCIEMEntities();
  const { paths, isLoading: pathLoading } = useEscalationPaths();
  const [tab, setTab] = useState<Tab>("entities");
  const [scopeFilter, setScopeFilter] = useState<string>("all");
  const [riskFilter, setRiskFilter] = useState<string>("all");

  const filteredEntities = entities.filter(e => {
    if (scopeFilter !== "all" && e.permission_scope !== scopeFilter) return false;
    if (riskFilter !== "all" && e.escalation_risk !== riskFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">CIEM</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Cloud Identity & Entitlement Management · IAM entity inventory + privilege escalation detection
        </p>
      </div>

      {/* Summary stats */}
      {sumLoading ? (
        <div className="flex justify-center h-20 items-center"><Spinner /></div>
      ) : summary ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          <StatCard label="Total IAM Entities" value={summary.total_entities} sub={`${summary.roles} roles · ${summary.users} users`} />
          <StatCard label="Admin Permissions" value={summary.admin_entities} color={summary.admin_entities > 0 ? "text-red-600" : "text-slate-800"} sub="broad privilege scope" />
          <StatCard label="Escalation Paths" value={summary.escalation_paths_count} color={summary.escalation_paths_count > 0 ? "text-orange-600" : "text-slate-800"} sub={`${summary.critical_paths} critical`} />
          <StatCard label="No MFA" value={summary.no_mfa_count} color={summary.no_mfa_count > 0 ? "text-orange-600" : "text-green-600"} sub="missing MFA protection" />
          <StatCard label="Cross-Account Trusts" value={summary.cross_account_trusts} sub="role assumption paths" />
        </div>
      ) : null}

      {/* Risk breakdown bar */}
      {summary && (
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <p className="text-xs font-semibold text-slate-600 mb-3">Entity Escalation Risk Distribution</p>
          <div className="flex items-center gap-2">
            {(["critical", "high", "medium", "low"] as const).map(r => {
              const count = summary.risk_breakdown[r];
              const total = summary.total_entities || 1;
              const pct = Math.round((count / total) * 100);
              const colors = { critical: "bg-red-500", high: "bg-orange-400", medium: "bg-yellow-400", low: "bg-blue-300" };
              return count > 0 ? (
                <div
                  key={r}
                  className={cn("h-6 rounded flex items-center justify-center text-white text-[10px] font-bold", colors[r])}
                  style={{ width: `${pct}%`, minWidth: "2rem" }}
                  title={`${r}: ${count}`}
                >
                  {count}
                </div>
              ) : null;
            })}
          </div>
          <div className="flex gap-4 mt-2">
            {(["critical", "high", "medium", "low"] as const).map(r => (
              <span key={r} className="text-[10px] text-slate-500 capitalize">{r}: {summary.risk_breakdown[r]}</span>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="flex border-b border-slate-200">
          {([
            { key: "entities",   label: "IAM Inventory",       icon: UserCog },
            { key: "escalation", label: "Escalation Paths",    icon: ShieldAlert },
          ] as const).map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={cn(
                "flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors",
                tab === key
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-slate-500 hover:text-slate-700"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
              <span className={cn(
                "ml-1 text-xs px-1.5 py-0.5 rounded-full font-semibold",
                tab === key ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-500"
              )}>
                {key === "entities" ? entities.length : paths.length}
              </span>
            </button>
          ))}
        </div>

        {/* Entities tab */}
        {tab === "entities" && (
          <>
            {/* Filters */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-100 bg-slate-50">
              <span className="text-xs text-slate-500 font-medium">Filter:</span>
              <select
                value={scopeFilter}
                onChange={e => setScopeFilter(e.target.value)}
                className="text-xs border border-slate-200 rounded px-2 py-1 bg-white text-slate-700"
              >
                <option value="all">All scopes</option>
                <option value="admin">Admin</option>
                <option value="write">Write</option>
                <option value="read">Read</option>
                <option value="limited">Limited</option>
              </select>
              <select
                value={riskFilter}
                onChange={e => setRiskFilter(e.target.value)}
                className="text-xs border border-slate-200 rounded px-2 py-1 bg-white text-slate-700"
              >
                <option value="all">All risk levels</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
              <span className="text-xs text-slate-400">{filteredEntities.length} entities</span>
            </div>

            {entLoading ? (
              <div className="flex justify-center py-12"><Spinner /></div>
            ) : filteredEntities.length === 0 ? (
              <p className="text-center py-12 text-slate-400 text-sm">No entities match filters.</p>
            ) : (
              <div>
                {filteredEntities.map(e => <EntityRow key={e.id} entity={e} />)}
              </div>
            )}
          </>
        )}

        {/* Escalation tab */}
        {tab === "escalation" && (
          pathLoading ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : paths.length === 0 ? (
            <p className="text-center py-12 text-slate-400 text-sm">No escalation paths detected.</p>
          ) : (
            <div>
              {paths.map(p => <PathRow key={p.id + p.pattern} path={p} />)}
            </div>
          )
        )}
      </div>
    </div>
  );
}
