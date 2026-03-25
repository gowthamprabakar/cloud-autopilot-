"use client";
import { useState } from "react";
import { KeyRound, Plus, Trash2, Copy, Check } from "lucide-react";
import { useApiKeys, createApiKey, revokeApiKey } from "@/lib/hooks/use-api-keys";
import type { ApiKeyCreate, ApiKeyCreatedResponse } from "@/lib/types";

function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return "Never";
  const diff = Date.now() - new Date(dateStr).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "Just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} day${days === 1 ? "" : "s"} ago`;
  const months = Math.floor(days / 30);
  return `${months} month${months === 1 ? "" : "s"} ago`;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "Never";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function SkeletonRow() {
  return (
    <tr className="border-b border-slate-100">
      {[...Array(6)].map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div
            className="h-4 rounded bg-slate-100 animate-pulse"
            style={{ width: i === 0 ? "120px" : i === 1 ? "100px" : i === 2 ? "90px" : i === 3 ? "80px" : i === 4 ? "60px" : "60px" }}
          />
        </td>
      ))}
    </tr>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  async function handleCopy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }
  return (
    <button
      onClick={handleCopy}
      className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 bg-slate-100 hover:bg-slate-200 px-2.5 py-1.5 rounded-lg transition-colors"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-green-600" /> : <Copy className="h-3.5 w-3.5" />}
      {copied ? "Copied!" : "Copy"}
    </button>
  );
}

const DEFAULT_FORM: ApiKeyCreate = { name: "", expires_at: null };

export default function ApiKeysPage() {
  const { apiKeys, isLoading, error, mutate } = useApiKeys();

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [form, setForm] = useState<ApiKeyCreate>(DEFAULT_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [formLoading, setFormLoading] = useState(false);

  const [createdKey, setCreatedKey] = useState<ApiKeyCreatedResponse | null>(null);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setFormLoading(true);
    try {
      const payload: ApiKeyCreate = { name: form.name };
      if (form.expires_at) payload.expires_at = form.expires_at;
      const result = await createApiKey(payload);
      await mutate();
      setShowCreateModal(false);
      setForm(DEFAULT_FORM);
      setCreatedKey(result);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create API key");
    } finally {
      setFormLoading(false);
    }
  }

  async function handleRevoke(keyId: string, keyName: string) {
    if (!window.confirm(`Revoke API key "${keyName}"? This cannot be undone.`)) return;
    try {
      await revokeApiKey(keyId);
      await mutate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to revoke key");
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">API Keys</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Long-lived tokens for CI/CD and machine-to-machine access
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="h-4 w-4" />
          Create API Key
        </button>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
        {error ? (
          <div className="p-6 text-center text-sm text-red-500">Failed to load API keys</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Name</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Prefix</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">Last Used</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden lg:table-cell">Expires</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
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
              ) : apiKeys.length === 0 ? (
                <tr>
                  <td colSpan={6}>
                    <div className="flex flex-col items-center justify-center py-16 text-slate-400">
                      <KeyRound className="h-10 w-10 mb-3 opacity-40" />
                      <p className="text-sm font-medium">No API keys yet</p>
                      <p className="text-xs mt-1 text-slate-500">
                        Create one to enable programmatic access
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                apiKeys.map((key) => (
                  <tr key={key.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-800 truncate max-w-[160px]">{key.name}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs text-slate-700 bg-slate-100 px-2 py-1 rounded">
                        {key.key_prefix}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <span className="text-xs text-slate-500">{formatRelativeTime(key.last_used_at)}</span>
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell">
                      <span className="text-xs text-slate-500">{formatDate(key.expires_at)}</span>
                    </td>
                    <td className="px-4 py-3">
                      {key.is_active ? (
                        <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700">
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-700">
                          Revoked
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {key.is_active && (
                        <button
                          onClick={() => handleRevoke(key.id, key.name)}
                          className="inline-flex items-center gap-1.5 text-xs text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 px-2.5 py-1.5 rounded-lg transition-colors"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          Revoke
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => { setShowCreateModal(false); setForm(DEFAULT_FORM); setFormError(null); }}
          />
          <div className="relative z-10 w-full max-w-md rounded-xl bg-white shadow-xl p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Create API Key</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. GitHub Actions CI"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Expires At <span className="text-slate-400 font-normal">(optional)</span>
                </label>
                <input
                  type="date"
                  value={form.expires_at ?? ""}
                  onChange={(e) => setForm(f => ({ ...f, expires_at: e.target.value || null }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {formError && <p className="text-sm text-red-500">{formError}</p>}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowCreateModal(false); setForm(DEFAULT_FORM); setFormError(null); }}
                  className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formLoading}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-60 transition-colors"
                >
                  {formLoading ? "Creating…" : "Create Key"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Key Created Modal */}
      {createdKey && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" />
          <div className="relative z-10 w-full max-w-lg rounded-xl bg-white shadow-xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100">
                <Check className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-slate-900">Key Created</h2>
                <p className="text-sm text-slate-500">{createdKey.name}</p>
              </div>
            </div>

            <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 mb-4">
              <p className="text-sm text-amber-800 font-medium">
                This key will not be shown again. Copy it now.
              </p>
            </div>

            <div className="rounded-lg bg-slate-950 p-4 mb-4 flex items-start justify-between gap-3">
              <code className="font-mono text-sm text-green-400 break-all select-all">
                {createdKey.raw_key}
              </code>
              <CopyButton text={createdKey.raw_key} />
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setCreatedKey(null)}
                className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
