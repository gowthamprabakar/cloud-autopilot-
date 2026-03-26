"use client";

import { useState } from "react";
import {
  Plus, Loader2, AlertCircle, Trash2, Play, X,
  MessageSquare, Ticket, Bell, Monitor, Github, GitlabIcon,
  Plug,
} from "lucide-react";
import {
  useIntegrations,
  createIntegration,
  deleteIntegration,
  testIntegration,
  type Integration,
} from "@/lib/hooks/use-integration-hub";

/* ---------- constants ---------- */

const TYPE_META: Record<
  Integration["integration_type"],
  { label: string; icon: any; color: string }
> = {
  slack:     { label: "Slack",     icon: MessageSquare, color: "text-pink-400" },
  jira:      { label: "Jira",      icon: Ticket,        color: "text-blue-400" },
  pagerduty: { label: "PagerDuty", icon: Bell,          color: "text-green-400" },
  siem:      { label: "SIEM",      icon: Monitor,       color: "text-amber-400" },
  github:    { label: "GitHub",    icon: Github,        color: "text-slate-300" },
  gitlab:    { label: "GitLab",    icon: GitlabIcon,    color: "text-orange-400" },
};

const INTEGRATION_TYPES = Object.keys(TYPE_META) as Integration["integration_type"][];

/* ---------- config field definitions per type ---------- */

interface FieldDef {
  key: string;
  label: string;
  placeholder?: string;
  type?: string;
}

const CONFIG_FIELDS: Record<Integration["integration_type"], FieldDef[]> = {
  slack: [
    { key: "webhook_url", label: "Webhook URL", placeholder: "https://hooks.slack.com/services/..." },
    { key: "channel", label: "Channel", placeholder: "#security-alerts" },
  ],
  jira: [
    { key: "base_url", label: "Base URL", placeholder: "https://yourteam.atlassian.net" },
    { key: "project_key", label: "Project Key", placeholder: "SEC" },
    { key: "api_token", label: "API Token", type: "password" },
    { key: "email", label: "Email", placeholder: "user@company.com" },
  ],
  pagerduty: [
    { key: "api_key", label: "API Key", type: "password" },
    { key: "service_id", label: "Service ID", placeholder: "PXXXXXX" },
  ],
  siem: [
    { key: "endpoint_url", label: "Endpoint URL", placeholder: "https://siem.example.com/ingest" },
    { key: "format", label: "Format", placeholder: "CEF / LEEF / JSON" },
  ],
  github: [
    { key: "token", label: "Personal Access Token", type: "password" },
    { key: "org", label: "Organization", placeholder: "my-org" },
    { key: "repo", label: "Repository", placeholder: "my-repo" },
  ],
  gitlab: [
    { key: "token", label: "Access Token", type: "password" },
    { key: "project_id", label: "Project ID", placeholder: "12345" },
  ],
};

/* ---------- small components ---------- */

function Badge({ children, variant }: { children: React.ReactNode; variant: "error" | "success" | "neutral" }) {
  const colors = {
    error: "bg-red-900/40 text-red-400 border-red-800",
    success: "bg-green-900/40 text-green-400 border-green-800",
    neutral: "bg-slate-700/50 text-slate-400 border-slate-600",
  };
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs ${colors[variant]}`}>
      {children}
    </span>
  );
}

/* ---------- integration card ---------- */

function IntegrationCard({
  item,
  onTest,
  onDelete,
}: {
  item: Integration;
  onTest: () => void;
  onDelete: () => void;
}) {
  const meta = TYPE_META[item.integration_type];
  const Icon = meta.icon;
  const [testing, setTesting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  async function handleTest() {
    setTesting(true);
    setTestResult(null);
    try {
      await testIntegration(item.id);
      setTestResult("OK");
    } catch (e: any) {
      setTestResult(`Failed: ${e.message ?? "Unknown"}`);
    } finally {
      setTesting(false);
    }
  }

  async function handleDelete() {
    if (!confirm(`Delete integration "${item.name}"?`)) return;
    setDeleting(true);
    try {
      await deleteIntegration(item.id);
      onDelete();
    } catch {
      setDeleting(false);
    }
  }

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/60 p-5 flex flex-col gap-3">
      {/* header */}
      <div className="flex items-center gap-3">
        <Icon className={`h-6 w-6 ${meta.color}`} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-white truncate">{item.name}</p>
          <p className="text-xs text-slate-500">{meta.label}</p>
        </div>
        <span
          className={`h-2.5 w-2.5 rounded-full ${item.is_enabled ? "bg-green-500" : "bg-slate-600"}`}
          title={item.is_enabled ? "Enabled" : "Disabled"}
        />
      </div>

      {/* meta */}
      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
        {item.last_sync_at && (
          <span>Last sync: {new Date(item.last_sync_at).toLocaleString()}</span>
        )}
        {item.last_error && (
          <Badge variant="error">
            <AlertCircle className="h-3 w-3" /> Error
          </Badge>
        )}
      </div>

      {item.last_error && (
        <p className="text-xs text-red-400 bg-red-900/20 rounded-lg p-2 break-words">
          {item.last_error}
        </p>
      )}

      {testResult && (
        <p className={`text-xs rounded-lg p-2 ${testResult === "OK" ? "text-green-400 bg-green-900/20" : "text-red-400 bg-red-900/20"}`}>
          {testResult}
        </p>
      )}

      {/* actions */}
      <div className="flex items-center gap-2 mt-auto pt-2 border-t border-slate-700">
        <button
          onClick={handleTest}
          disabled={testing}
          className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium text-blue-400 hover:bg-blue-600/20 transition-colors disabled:opacity-50"
        >
          {testing ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
          Test
        </button>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-600/20 transition-colors disabled:opacity-50 ml-auto"
        >
          {deleting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
          Delete
        </button>
      </div>
    </div>
  );
}

/* ---------- add dialog ---------- */

function AddIntegrationDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [selectedType, setSelectedType] = useState<Integration["integration_type"]>("slack");
  const [name, setName] = useState("");
  const [configValues, setConfigValues] = useState<Record<string, string>>({});
  const [creating, setCreating] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  function reset() {
    setSelectedType("slack");
    setName("");
    setConfigValues({});
    setErrorMsg(null);
  }

  async function handleCreate() {
    if (!name.trim()) {
      setErrorMsg("Name is required.");
      return;
    }
    setCreating(true);
    setErrorMsg(null);
    try {
      await createIntegration(selectedType, name.trim(), configValues);
      reset();
      onCreated();
      onClose();
    } catch (e: any) {
      setErrorMsg(e.message ?? "Unknown error");
    } finally {
      setCreating(false);
    }
  }

  if (!open) return null;

  const fields = CONFIG_FIELDS[selectedType];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-semibold text-white">Add Integration</h3>
          <button onClick={() => { reset(); onClose(); }} className="text-slate-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          {/* type selector */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Type</label>
            <div className="grid grid-cols-3 gap-2">
              {INTEGRATION_TYPES.map((t) => {
                const meta = TYPE_META[t];
                const Icon = meta.icon;
                return (
                  <button
                    key={t}
                    onClick={() => { setSelectedType(t); setConfigValues({}); }}
                    className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors ${
                      selectedType === t
                        ? "border-blue-500 bg-blue-600/20 text-blue-400"
                        : "border-slate-700 bg-slate-800 text-slate-400 hover:text-white hover:border-slate-500"
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {meta.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* name */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Production Slack"
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
            />
          </div>

          {/* config fields */}
          {fields.map((f) => (
            <div key={f.key}>
              <label className="block text-sm font-medium text-slate-300 mb-1">{f.label}</label>
              <input
                type={f.type ?? "text"}
                value={configValues[f.key] ?? ""}
                onChange={(e) => setConfigValues((prev) => ({ ...prev, [f.key]: e.target.value }))}
                placeholder={f.placeholder}
                className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none"
              />
            </div>
          ))}
        </div>

        {errorMsg && (
          <p className="mt-3 text-sm text-red-400 flex items-center gap-1">
            <AlertCircle className="h-4 w-4" /> {errorMsg}
          </p>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={() => { reset(); onClose(); }}
            className="rounded-lg px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={creating}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
          >
            {creating && <Loader2 className="h-4 w-4 animate-spin" />}
            Create
          </button>
        </div>
      </div>
    </div>
  );
}

/* ---------- page ---------- */

export default function IntegrationHubPage() {
  const { integrations, isLoading, error, mutate } = useIntegrations();
  const [dialogOpen, setDialogOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin text-blue-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-red-400 p-8">
        <AlertCircle className="h-5 w-5" />
        Failed to load integrations.
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      {/* header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Plug className="h-6 w-6 text-blue-400" />
          Integration Hub
        </h1>
        <button
          onClick={() => setDialogOpen(true)}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Add Integration
        </button>
      </div>

      {/* grid */}
      {integrations.length === 0 ? (
        <div className="text-center py-20 text-slate-500">
          <Plug className="h-10 w-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No integrations configured yet.</p>
          <p className="text-xs mt-1">Click "Add Integration" to get started.</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {integrations.map((item) => (
            <IntegrationCard
              key={item.id}
              item={item}
              onTest={() => {}}
              onDelete={() => mutate()}
            />
          ))}
        </div>
      )}

      {/* dialog */}
      <AddIntegrationDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onCreated={() => mutate()}
      />
    </div>
  );
}
