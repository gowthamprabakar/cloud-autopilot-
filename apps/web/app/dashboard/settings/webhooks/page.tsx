"use client";
import { useState } from "react";
import { Globe, Plus, Trash2, Copy, Check, Zap } from "lucide-react";
import { useWebhooks, createWebhook, deleteWebhook, testWebhook } from "@/lib/hooks/use-webhooks";
import type { WebhookCreate, WebhookCreatedResponse } from "@/lib/types";

const ALL_EVENTS = [
  "finding.created",
  "finding.critical",
  "finding.status_changed",
  "finding.resolved",
] as const;

type WebhookEvent = (typeof ALL_EVENTS)[number];

const EVENT_BADGE_CLASSES: Record<string, string> = {
  "finding.critical": "bg-red-100 text-red-700",
  "finding.created": "bg-blue-100 text-blue-700",
  "finding.status_changed": "bg-amber-100 text-amber-700",
  "finding.resolved": "bg-green-100 text-green-700",
};

function EventBadge({ event }: { event: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${EVENT_BADGE_CLASSES[event] ?? "bg-slate-100 text-slate-600"}`}
    >
      {event}
    </span>
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

function SkeletonRow() {
  return (
    <tr className="border-b border-slate-100">
      {[...Array(5)].map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div
            className="h-4 rounded bg-slate-100 animate-pulse"
            style={{ width: i === 0 ? "120px" : i === 1 ? "200px" : i === 2 ? "180px" : i === 3 ? "60px" : "80px" }}
          />
        </td>
      ))}
    </tr>
  );
}

interface Toast {
  id: number;
  message: string;
  type: "success" | "error";
}

const DEFAULT_FORM: WebhookCreate = { name: "", url: "", events: [] };

export default function WebhooksPage() {
  const { webhooks, isLoading, error, mutate } = useWebhooks();

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [form, setForm] = useState<WebhookCreate>(DEFAULT_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [formLoading, setFormLoading] = useState(false);

  const [createdWebhook, setCreatedWebhook] = useState<WebhookCreatedResponse | null>(null);
  const [testingIds, setTestingIds] = useState<Set<string>>(new Set());
  const [toasts, setToasts] = useState<Toast[]>([]);

  function addToast(message: string, type: "success" | "error") {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  }

  function toggleEvent(event: WebhookEvent) {
    setForm(f => ({
      ...f,
      events: f.events.includes(event)
        ? f.events.filter(e => e !== event)
        : [...f.events, event],
    }));
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (form.events.length === 0) {
      setFormError("Select at least one event");
      return;
    }
    setFormLoading(true);
    try {
      const result = await createWebhook(form);
      await mutate();
      setShowCreateModal(false);
      setForm(DEFAULT_FORM);
      setCreatedWebhook(result);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create webhook");
    } finally {
      setFormLoading(false);
    }
  }

  async function handleDelete(webhookId: string, webhookName: string) {
    if (!window.confirm(`Delete webhook "${webhookName}"?`)) return;
    try {
      await deleteWebhook(webhookId);
      await mutate();
    } catch (err) {
      addToast(err instanceof Error ? err.message : "Failed to delete webhook", "error");
    }
  }

  async function handleTest(webhookId: string) {
    setTestingIds(prev => new Set(prev).add(webhookId));
    try {
      const result = await testWebhook(webhookId);
      if (result.delivered) {
        addToast("Ping delivered", "success");
      } else {
        addToast(`Ping failed: ${result.error ?? "Unknown error"}`, "error");
      }
    } catch (err) {
      addToast(err instanceof Error ? err.message : "Test failed", "error");
    } finally {
      setTestingIds(prev => {
        const next = new Set(prev);
        next.delete(webhookId);
        return next;
      });
    }
  }

  return (
    <div className="space-y-6">
      {/* Toast notifications */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {toasts.map(toast => (
          <div
            key={toast.id}
            className={`rounded-lg px-4 py-3 text-sm font-medium shadow-lg ${
              toast.type === "success"
                ? "bg-green-600 text-white"
                : "bg-red-600 text-white"
            }`}
          >
            {toast.message}
          </div>
        ))}
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Webhook Destinations</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Receive real-time event notifications at external HTTP endpoints
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="h-4 w-4" />
          Add Webhook
        </button>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
        {error ? (
          <div className="p-6 text-center text-sm text-red-500">Failed to load webhooks</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Name</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">URL</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide hidden lg:table-cell">Events</th>
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
              ) : webhooks.length === 0 ? (
                <tr>
                  <td colSpan={5}>
                    <div className="flex flex-col items-center justify-center py-16 text-slate-400">
                      <Globe className="h-10 w-10 mb-3 opacity-40" />
                      <p className="text-sm font-medium">No webhooks configured</p>
                      <p className="text-xs mt-1 text-slate-500">
                        Add one to start receiving event notifications
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                webhooks.map((webhook) => (
                  <tr key={webhook.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-800 truncate max-w-[160px]">{webhook.name}</p>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <span className="text-xs font-mono text-slate-600 truncate block max-w-[260px]">
                        {webhook.url.length > 50 ? `${webhook.url.slice(0, 50)}…` : webhook.url}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell">
                      <div className="flex flex-wrap gap-1">
                        {webhook.events.map(evt => (
                          <EventBadge key={evt} event={evt} />
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {webhook.is_active ? (
                        <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700">
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">
                          Inactive
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleTest(webhook.id)}
                          disabled={testingIds.has(webhook.id)}
                          className="inline-flex items-center gap-1.5 text-xs text-amber-700 hover:text-amber-800 bg-amber-50 hover:bg-amber-100 px-2.5 py-1.5 rounded-lg transition-colors disabled:opacity-50"
                        >
                          <Zap className="h-3.5 w-3.5" />
                          {testingIds.has(webhook.id) ? "Testing…" : "Test"}
                        </button>
                        <button
                          onClick={() => handleDelete(webhook.id, webhook.name)}
                          className="inline-flex items-center gap-1.5 text-xs text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 px-2.5 py-1.5 rounded-lg transition-colors"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          Delete
                        </button>
                      </div>
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
          <div className="relative z-10 w-full max-w-lg rounded-xl bg-white shadow-xl p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Add Webhook</h2>
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
                  placeholder="e.g. PagerDuty Critical Alerts"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  URL <span className="text-red-500">*</span>
                </label>
                <input
                  type="url"
                  required
                  value={form.url}
                  onChange={(e) => setForm(f => ({ ...f, url: e.target.value }))}
                  placeholder="https://hooks.example.com/..."
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Events <span className="text-red-500">*</span>
                </label>
                <div className="space-y-2">
                  {ALL_EVENTS.map(event => (
                    <label key={event} className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.events.includes(event)}
                        onChange={() => toggleEvent(event)}
                        className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                      />
                      <EventBadge event={event} />
                    </label>
                  ))}
                </div>
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
                  {formLoading ? "Creating…" : "Add Webhook"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Webhook Created Modal */}
      {createdWebhook && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" />
          <div className="relative z-10 w-full max-w-lg rounded-xl bg-white shadow-xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100">
                <Check className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-slate-900">Webhook Created</h2>
                <p className="text-sm text-slate-500">{createdWebhook.name}</p>
              </div>
            </div>

            <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 mb-4">
              <p className="text-sm text-amber-800 font-medium">
                Save this secret — it won&apos;t be shown again. Use it to verify{" "}
                <code className="font-mono text-xs">X-Copilot-Signature</code> headers.
              </p>
            </div>

            <div className="rounded-lg bg-slate-950 p-4 mb-4 flex items-start justify-between gap-3">
              <code className="font-mono text-sm text-green-400 break-all select-all">
                {createdWebhook.secret}
              </code>
              <CopyButton text={createdWebhook.secret} />
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setCreatedWebhook(null)}
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
