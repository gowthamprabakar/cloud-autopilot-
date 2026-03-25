"use client";
import { useState } from "react";
import { UserCircle, X, CalendarDays } from "lucide-react";
import {
  useFindingAssignment,
  assignFinding,
  unassignFinding,
} from "@/lib/hooks/use-assignments";

interface Props {
  findingId: string;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "No deadline";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

interface AssignModalProps {
  findingId: string;
  onClose: () => void;
  onSaved: () => void;
}

function AssignModal({ findingId, onClose, onSaved }: AssignModalProps) {
  const [userId, setUserId] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!userId.trim()) {
      setError("User ID is required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await assignFinding(findingId, {
        assignee_user_id: userId.trim(),
        due_date: dueDate || null,
        note: note.trim() || null,
      });
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to assign.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-800">Assign Finding</h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              User ID <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="e.g. usr_abc123"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Due Date <span className="text-slate-400">(optional)</span>
            </label>
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Note <span className="text-slate-400">(optional)</span>
            </label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              placeholder="e.g. Check S3 bucket policy"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>

          {error && (
            <p className="text-xs text-red-600">{error}</p>
          )}

          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {saving ? "Assigning…" : "Assign"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function AssignmentWidget({ findingId }: Props) {
  const { assignment, isLoading, mutate } = useFindingAssignment(findingId);
  const [showModal, setShowModal] = useState(false);
  const [unassigning, setUnassigning] = useState(false);

  async function handleUnassign() {
    setUnassigning(true);
    try {
      await unassignFinding(findingId);
      await mutate();
    } finally {
      setUnassigning(false);
    }
  }

  if (isLoading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-5 animate-pulse">
        <div className="h-3 w-28 rounded bg-slate-100 mb-2" />
        <div className="h-4 w-48 rounded bg-slate-100" />
      </div>
    );
  }

  return (
    <>
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
          Assignment
        </h3>

        {assignment ? (
          <div className="space-y-2">
            <div className="flex items-start gap-2">
              <UserCircle className="h-4 w-4 text-slate-400 mt-0.5 shrink-0" />
              <div className="text-sm">
                <p className="font-medium text-slate-800">
                  {assignment.assignee_email ?? assignment.assignee_user_id}
                </p>
                {assignment.assigned_by_email && (
                  <p className="text-xs text-slate-500">
                    assigned by {assignment.assigned_by_email}
                  </p>
                )}
              </div>
            </div>

            {assignment.due_date && (
              <div className="flex items-center gap-2 text-sm text-slate-600">
                <CalendarDays className="h-4 w-4 text-slate-400 shrink-0" />
                <span>Due: {formatDate(assignment.due_date)}</span>
              </div>
            )}

            {assignment.note && (
              <p className="text-xs text-slate-500 bg-slate-50 rounded-lg px-3 py-2 border border-slate-100">
                &ldquo;{assignment.note}&rdquo;
              </p>
            )}

            <div className="flex items-center gap-2 pt-1">
              <button
                onClick={() => setShowModal(true)}
                className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
              >
                Reassign
              </button>
              <button
                onClick={handleUnassign}
                disabled={unassigning}
                className="rounded-lg border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50 transition-colors"
              >
                {unassigning ? "Removing…" : "Unassign"}
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-slate-500">No assignee</p>
            <button
              onClick={() => setShowModal(true)}
              className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 transition-colors"
            >
              Assign
            </button>
          </div>
        )}
      </div>

      {showModal && (
        <AssignModal
          findingId={findingId}
          onClose={() => setShowModal(false)}
          onSaved={() => mutate()}
        />
      )}
    </>
  );
}
