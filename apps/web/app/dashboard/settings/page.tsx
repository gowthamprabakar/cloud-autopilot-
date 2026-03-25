"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/lib/hooks/use-auth";
import { useWorkspace, updateWorkspace } from "@/lib/hooks/use-workspace";
import type { UserRole } from "@/lib/types";

const ROLE_BADGE_CLASSES: Record<UserRole, string> = {
  super_admin: "bg-purple-100 text-purple-800",
  admin: "bg-blue-100 text-blue-800",
  analyst: "bg-green-100 text-green-800",
  viewer: "bg-slate-100 text-slate-600",
  msp_partner: "bg-orange-100 text-orange-800",
};

function RoleBadge({ role }: { role: UserRole }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${ROLE_BADGE_CLASSES[role] ?? "bg-slate-100 text-slate-600"}`}
    >
      {role.replace("_", " ")}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const isActive = status === "active";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
        isActive ? "bg-green-100 text-green-800" : "bg-slate-100 text-slate-600"
      }`}
    >
      {status}
    </span>
  );
}

export default function SettingsPage() {
  const { user } = useAuth();
  const { workspace, isLoading: wsLoading, error: wsError, mutate: wsMutate } = useWorkspace();

  const [workspaceName, setWorkspaceName] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const isAdmin =
    user?.role === "super_admin" || user?.role === "admin";

  // Sync local state when workspace data arrives
  useEffect(() => {
    if (workspace) {
      setWorkspaceName(workspace.name);
    }
  }, [workspace]);

  async function handleSaveWorkspace(e: React.FormEvent) {
    e.preventDefault();
    setSaveError(null);
    setSaving(true);
    try {
      await updateWorkspace({ name: workspaceName });
      await wsMutate();
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save changes");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold text-slate-900">Settings</h1>

      {/* ── Section 1: Profile ─────────────────────────────── */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <h2 className="text-base font-semibold text-slate-900 mb-4">Profile</h2>

        {!user ? (
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-4 w-64 rounded bg-slate-200 animate-pulse" />
            ))}
          </div>
        ) : (
          <dl className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-0">
              <dt className="text-sm font-medium text-slate-500 sm:w-36">Full Name</dt>
              <dd className="text-sm text-slate-900">{user.full_name}</dd>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-0">
              <dt className="text-sm font-medium text-slate-500 sm:w-36">Email</dt>
              <dd className="text-sm text-slate-900">{user.email}</dd>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-0">
              <dt className="text-sm font-medium text-slate-500 sm:w-36">Role</dt>
              <dd>
                <RoleBadge role={user.role} />
              </dd>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-0">
              <dt className="text-sm font-medium text-slate-500 sm:w-36">Member Since</dt>
              <dd className="text-sm text-slate-900">
                {new Date(user.created_at).toLocaleDateString("en-US", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </dd>
            </div>
          </dl>
        )}

        <p className="mt-4 text-xs text-slate-400">Profile updates coming soon</p>
      </div>

      {/* ── Section 2: Workspace ───────────────────────────── */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <h2 className="text-base font-semibold text-slate-900 mb-4">Workspace</h2>

        {wsLoading ? (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-4 w-56 rounded bg-slate-200 animate-pulse" />
            ))}
          </div>
        ) : wsError ? (
          <p className="text-sm text-red-500">Failed to load workspace settings</p>
        ) : workspace === null ? (
          <p className="text-sm text-slate-500">No workspace found</p>
        ) : isAdmin ? (
          <form onSubmit={handleSaveWorkspace} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Workspace Name
              </label>
              <input
                type="text"
                required
                value={workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Slug
              </label>
              <input
                type="text"
                readOnly
                value={workspace.slug}
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500 cursor-not-allowed"
              />
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-0">
              <span className="text-sm font-medium text-slate-700 sm:w-36">Status</span>
              <StatusBadge status={workspace.status} />
            </div>

            {saveError && <p className="text-sm text-red-500">{saveError}</p>}

            <div className="flex items-center gap-3 pt-1">
              <button
                type="submit"
                disabled={saving}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-60 transition-colors"
              >
                {saving ? "Saving…" : "Save Changes"}
              </button>
              {saveSuccess && (
                <span className="text-sm font-medium text-green-600">Saved!</span>
              )}
            </div>
          </form>
        ) : (
          // Read-only for non-admins
          <dl className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-0">
              <dt className="text-sm font-medium text-slate-500 sm:w-36">Name</dt>
              <dd className="text-sm text-slate-900">{workspace.name}</dd>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-0">
              <dt className="text-sm font-medium text-slate-500 sm:w-36">Slug</dt>
              <dd className="text-sm font-mono text-slate-600">{workspace.slug}</dd>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-0">
              <dt className="text-sm font-medium text-slate-500 sm:w-36">Status</dt>
              <dd>
                <StatusBadge status={workspace.status} />
              </dd>
            </div>
          </dl>
        )}
      </div>
    </div>
  );
}
