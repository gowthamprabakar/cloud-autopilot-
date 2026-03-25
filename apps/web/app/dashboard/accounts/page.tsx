"use client";
import { useState } from "react";
import { useAccounts } from "@/lib/hooks/use-accounts";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { apiClient, authHeaders } from "@/lib/api-client";
import { RefreshCw, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import type { AwsAccount } from "@/lib/types";

export default function AccountsPage() {
  const { accounts, isLoading, error, mutate } = useAccounts();
  const [syncing, setSyncing] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);

  async function handleSync(accountId: string) {
    setSyncing(accountId);
    try {
      await apiClient.post(`/api/v1/aws-accounts/${accountId}/sync`, {}, { headers: authHeaders() });
      await mutate();
    } catch (e: any) {
      alert(e.detail ?? "Sync failed");
    } finally {
      setSyncing(null);
    }
  }

  async function handleDelete(accountId: string) {
    if (!confirm("Delete this account? All associated findings will be removed.")) return;
    setDeleting(accountId);
    try {
      await apiClient.delete(`/api/v1/aws-accounts/${accountId}`, { headers: authHeaders() });
      await mutate();
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">AWS Accounts</h1>
          <p className="text-sm text-slate-500 mt-0.5">{accounts?.length ?? 0} accounts connected</p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-blue-500 transition-colors"
        >
          <Plus className="h-4 w-4" /> Add Account
        </button>
      </div>

      {showAdd && <AddAccountForm onSuccess={() => { setShowAdd(false); mutate(); }} onCancel={() => setShowAdd(false)} />}

      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center p-12"><Spinner className="h-6 w-6" /></div>
        ) : error ? (
          <div className="p-6 text-center text-sm text-red-500">Failed to load accounts</div>
        ) : !accounts?.length ? (
          <div className="p-12 text-center">
            <p className="text-sm text-slate-500 mb-3">No AWS accounts connected yet.</p>
            <button onClick={() => setShowAdd(true)} className="text-sm text-blue-600 hover:underline">
              + Connect your first AWS account
            </button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Account</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Last Synced</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {accounts.map((account) => (
                <tr key={account.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-slate-800">{account.account_alias ?? account.account_id}</p>
                    <p className="text-xs text-slate-400 font-mono">{account.account_id}</p>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={account.status as any}>{account.status}</Badge>
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell text-xs text-slate-400">
                    {account.last_synced_at ? new Date(account.last_synced_at).toLocaleDateString() : "Never"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex items-center gap-2">
                      {account.status === "active" && (
                        <button
                          onClick={() => handleSync(account.id)}
                          disabled={syncing === account.id}
                          className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1 text-xs hover:bg-slate-100 disabled:opacity-50"
                          title="Sync Security Hub findings"
                        >
                          <RefreshCw className={`h-3 w-3 ${syncing === account.id ? "animate-spin" : ""}`} />
                          Sync
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(account.id)}
                        disabled={deleting === account.id}
                        className="inline-flex items-center rounded-md border border-red-200 px-2.5 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// Add Account form (inline)
function AddAccountForm({ onSuccess, onCancel }: { onSuccess: () => void; onCancel: () => void }) {
  const [form, setForm] = useState({ account_id: "", account_alias: "", role_arn: "", external_id: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await apiClient.post("/api/v1/aws-accounts", {
        account_id: form.account_id,
        account_alias: form.account_alias || null,
        role_arn: form.role_arn,
        external_id: form.external_id || null,
      }, { headers: authHeaders() });
      onSuccess();
    } catch (e: any) {
      setError(e.detail ?? "Failed to add account");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-5">
      <h3 className="text-sm font-semibold text-slate-900 mb-4">Connect AWS Account</h3>
      {error && <div className="mb-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</div>}
      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {[
          { name: "account_id", label: "Account ID (12 digits)", placeholder: "123456789012", required: true },
          { name: "account_alias", label: "Alias (optional)", placeholder: "production-aws", required: false },
          { name: "role_arn", label: "Role ARN", placeholder: "arn:aws:iam::123456789012:role/CloudPostureCopilot", required: true },
          { name: "external_id", label: "External ID (optional)", placeholder: "ext-abc-123", required: false },
        ].map(field => (
          <div key={field.name}>
            <label className="block text-xs font-medium text-slate-600 mb-1">{field.label}</label>
            <input
              type="text"
              value={(form as any)[field.name]}
              onChange={e => setForm(f => ({ ...f, [field.name]: e.target.value }))}
              placeholder={field.placeholder}
              required={field.required}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        ))}
        <div className="md:col-span-2 flex gap-2 justify-end pt-1">
          <button type="button" onClick={onCancel} className="rounded-lg border border-slate-200 px-4 py-2 text-sm hover:bg-slate-50">Cancel</button>
          <button type="submit" disabled={loading} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50">
            {loading ? "Connecting…" : "Connect Account"}
          </button>
        </div>
      </form>
    </div>
  );
}
