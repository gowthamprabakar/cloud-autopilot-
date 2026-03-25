"use client";
import { useState } from "react";
import { ShieldOff, Trash2, Plus, Play } from "lucide-react";
import {
  useSuppressionRules,
  createSuppressionRule,
  deleteSuppressionRule,
  applySuppressionRules,
} from "@/lib/hooks/use-suppression";
import type { SuppressionRule, SuppressionRuleCreate } from "@/lib/types";

const SEVERITY_OPTIONS = ["critical", "high", "medium", "low", "info"];

function summarizeConditions(rule: SuppressionRule): string {
  const parts: string[] = [];
  if (rule.match_title_contains) parts.push(`title contains "${rule.match_title_contains}"`);
  if (rule.match_resource_type) parts.push(`type = ${rule.match_resource_type}`);
  if (rule.match_resource_arn_contains) parts.push(`ARN contains "${rule.match_resource_arn_contains}"`);
  if (rule.match_severity) parts.push(`severity = ${rule.match_severity}`);
  return parts.length ? parts.join(", ") : "Matches all findings";
}

function SkeletonRow() {
  return (
    <tr className="border-b border-slate-100">
      {[...Array(5)].map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 rounded bg-slate-100 animate-pulse" style={{ width: i === 0 ? "120px" : i === 1 ? "200px" : i === 2 ? "160px" : i === 3 ? "80px" : "60px" }} />
        </td>
      ))}
    </tr>
  );
}

const DEFAULT_FORM: SuppressionRuleCreate = {
  name: "",
  reason: "",
  match_title_contains: "",
  match_resource_type: "",
  match_resource_arn_contains: "",
  match_severity: "",
};

export default function SuppressionPage() {
  const { rules, isLoading, error, mutate } = useSuppressionRules();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<SuppressionRuleCreate>(DEFAULT_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [formLoading, setFormLoading] = useState(false);
  const [applyLoading, setApplyLoading] = useState(false);
  const [applyResult, setApplyResult] = useState<string | null>(null);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setFormLoading(true);
    try {
      const payload: SuppressionRuleCreate = {
        name: form.name,
        reason: form.reason,
      };
      if (form.match_title_contains) payload.match_title_contains = form.match_title_contains;
      if (form.match_resource_type) payload.match_resource_type = form.match_resource_type;
      if (form.match_resource_arn_contains) payload.match_resource_arn_contains = form.match_resource_arn_contains;
      if (form.match_severity) payload.match_severity = form.match_severity;
      await createSuppressionRule(payload);
      await mutate();
      setShowModal(false);
      setForm(DEFAULT_FORM);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create rule");
    } finally {
      setFormLoading(false);
    }
  }

  async function handleDelete(ruleId: string, ruleName: string) {
    if (!window.confirm(`Delete suppression rule "${ruleName}"?`)) return;
    try {
      await deleteSuppressionRule(ruleId);
      await mutate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete rule");
    }
  }

  async function handleApply() {
    setApplyLoading(true);
    setApplyResult(null);
    try {
      const result = await applySuppressionRules();
      setApplyResult(`${result.suppressed} findings suppressed`);
      await mutate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to apply rules");
    } finally {
      setApplyLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Suppression Rules</h1>
          <p className="text-sm text-slate-500 mt-0.5">Mute findings that match defined patterns</p>
        </div>
        <div className="flex items-center gap-3">
          {applyResult && (
            <span className="text-sm text-green-600 font-medium">{applyResult}</span>
          )}
          <button
            onClick={handleApply}
            disabled={applyLoading}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors disabled:opacity-50"
          >
            <Play className="h-3.5 w-3.5" />
            {applyLoading ? "Applying…" : "Apply Rules"}
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            <Plus className="h-4 w-4" />
            New Rule
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
        {error ? (
          <div className="p-6 text-center text-sm text-red-500">Failed to load suppression rules</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Name</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Conditions</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Reason</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden lg:table-cell">Created</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <>
                  <SkeletonRow />
                  <SkeletonRow />
                  <SkeletonRow />
                </>
              ) : rules.length === 0 ? (
                <tr>
                  <td colSpan={5}>
                    <div className="flex flex-col items-center justify-center py-16 text-slate-400">
                      <ShieldOff className="h-10 w-10 mb-3 opacity-40" />
                      <p className="text-sm font-medium">No suppression rules yet</p>
                      <p className="text-xs mt-1 text-slate-500">Create rules to automatically mute noisy findings</p>
                    </div>
                  </td>
                </tr>
              ) : (
                rules.map((rule) => (
                  <tr key={rule.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-800 truncate max-w-[180px]">{rule.name}</p>
                      {!rule.is_active && (
                        <span className="text-xs text-slate-400">inactive</span>
                      )}
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <p className="text-xs text-slate-500 truncate max-w-[280px]">{summarizeConditions(rule)}</p>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-xs text-slate-600 truncate max-w-[200px]">{rule.reason}</p>
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell">
                      <span className="text-xs text-slate-400">
                        {new Date(rule.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleDelete(rule.id, rule.name)}
                        className="inline-flex items-center gap-1.5 text-xs text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 px-2.5 py-1.5 rounded-lg transition-colors"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* New Rule Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => { setShowModal(false); setForm(DEFAULT_FORM); setFormError(null); }}
          />
          <div className="relative z-10 w-full max-w-lg rounded-xl bg-white shadow-xl p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Create Suppression Rule</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Name <span className="text-red-500">*</span></label>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. Suppress dev bucket findings"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Reason <span className="text-red-500">*</span></label>
                <textarea
                  required
                  value={form.reason}
                  onChange={(e) => setForm(f => ({ ...f, reason: e.target.value }))}
                  placeholder="Why are these findings being suppressed?"
                  rows={2}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                />
              </div>

              <div className="border-t border-slate-100 pt-3">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Match Conditions (leave blank to match all)</p>
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Title contains</label>
                    <input
                      type="text"
                      value={form.match_title_contains ?? ""}
                      onChange={(e) => setForm(f => ({ ...f, match_title_contains: e.target.value }))}
                      placeholder="e.g. S3 bucket"
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Resource type</label>
                    <input
                      type="text"
                      value={form.match_resource_type ?? ""}
                      onChange={(e) => setForm(f => ({ ...f, match_resource_type: e.target.value }))}
                      placeholder="e.g. AWS::S3::Bucket"
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">ARN contains</label>
                    <input
                      type="text"
                      value={form.match_resource_arn_contains ?? ""}
                      onChange={(e) => setForm(f => ({ ...f, match_resource_arn_contains: e.target.value }))}
                      placeholder="e.g. arn:aws:s3:::my-dev-bucket"
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Severity</label>
                    <select
                      value={form.match_severity ?? ""}
                      onChange={(e) => setForm(f => ({ ...f, match_severity: e.target.value }))}
                      className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Any severity</option>
                      {SEVERITY_OPTIONS.map(s => (
                        <option key={s} value={s} className="capitalize">{s}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {formError && (
                <p className="text-sm text-red-500">{formError}</p>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowModal(false); setForm(DEFAULT_FORM); setFormError(null); }}
                  className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formLoading}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-60 transition-colors"
                >
                  {formLoading ? "Creating…" : "Create Rule"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
