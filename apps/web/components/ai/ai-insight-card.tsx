"use client";

/**
 * AiInsightCard — displays AI-generated augmentation for a security finding.
 *
 * AI Safe Layer rules enforced in this component:
 * - Insight is displayed ALONGSIDE authoritative fields, never replacing them.
 * - Severity and risk_score are never read from the insight object.
 * - All content is clearly labelled as "AI-generated".
 * - Human feedback loop (Helpful / Edit / Reject) is always shown.
 */

import { useState } from "react";
import { Sparkles, ThumbsUp, ThumbsDown, Edit2, RefreshCw, AlertCircle } from "lucide-react";
import { generateInsight, submitAiFeedback, useAiInsight } from "@/lib/hooks/use-ai";
import type { AiFeedbackVerdict } from "@/lib/types";

interface AiInsightCardProps {
  findingId: string;
}

export function AiInsightCard({ findingId }: AiInsightCardProps) {
  const { insight, isLoading, mutate } = useAiInsight(findingId);
  const [generating, setGenerating] = useState(false);
  const [submittingFeedback, setSubmittingFeedback] = useState(false);
  const [feedbackDone, setFeedbackDone] = useState<AiFeedbackVerdict | null>(null);
  const [showEditBox, setShowEditBox] = useState(false);
  const [editedText, setEditedText] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    setFeedbackDone(null);
    setShowEditBox(false);
    try {
      await generateInsight(findingId);
      await mutate();
    } catch (e: any) {
      setError(e?.detail ?? "Failed to generate AI insight");
    } finally {
      setGenerating(false);
    }
  }

  async function handleFeedback(verdict: AiFeedbackVerdict, text?: string) {
    if (!insight) return;
    setSubmittingFeedback(true);
    try {
      await submitAiFeedback(insight.id, {
        verdict,
        edited_text: text ?? null,
      });
      setFeedbackDone(verdict);
      setShowEditBox(false);
    } catch (e: any) {
      setError(e?.detail ?? "Failed to submit feedback");
    } finally {
      setSubmittingFeedback(false);
    }
  }

  // ── Empty state — no insight yet ──────────────────────────────────────────
  if (!isLoading && !insight) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="h-4 w-4 text-violet-500" />
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
            AI Insight
          </h3>
          <span className="text-xs bg-violet-100 text-violet-600 px-1.5 py-0.5 rounded font-medium">
            Beta
          </span>
        </div>
        <p className="text-sm text-slate-500 mb-3">
          Generate an AI-powered plain-English summary and suggested remediation steps for this finding.
        </p>
        {error && (
          <div className="mb-3 flex items-center gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            {error}
          </div>
        )}
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50 transition-colors"
        >
          {generating ? (
            <RefreshCw className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4" />
          )}
          {generating ? "Generating…" : "Generate AI Insight"}
        </button>
      </div>
    );
  }

  // ── Loading ────────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-5 animate-pulse">
        <div className="h-4 bg-slate-100 rounded w-32 mb-3" />
        <div className="space-y-2">
          <div className="h-3 bg-slate-100 rounded w-full" />
          <div className="h-3 bg-slate-100 rounded w-4/5" />
        </div>
      </div>
    );
  }

  // ── Failed generation ──────────────────────────────────────────────────────
  if (insight?.generation_status === "failed") {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50/50 p-5">
        <div className="flex items-center gap-2 mb-2">
          <AlertCircle className="h-4 w-4 text-red-500" />
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">AI Insight</h3>
        </div>
        <p className="text-sm text-red-600 mb-3">
          {insight.error_message ?? "AI insight generation failed."}
        </p>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="text-sm text-violet-600 hover:underline disabled:opacity-50"
        >
          {generating ? "Retrying…" : "Retry"}
        </button>
      </div>
    );
  }

  // ── Completed insight ─────────────────────────────────────────────────────
  return (
    <div className="rounded-xl border border-violet-200 bg-violet-50/30 p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-violet-500" />
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
            AI Insight
          </h3>
          <span className="text-xs bg-violet-100 text-violet-600 px-1.5 py-0.5 rounded font-medium">
            Beta · AI-generated
          </span>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="text-xs text-slate-400 hover:text-slate-600 disabled:opacity-50 flex items-center gap-1"
          title="Regenerate"
        >
          <RefreshCw className={`h-3 w-3 ${generating ? "animate-spin" : ""}`} />
          Regenerate
        </button>
      </div>

      {/* Summary */}
      {insight?.summary && (
        <p className="text-sm text-slate-700 leading-relaxed mb-4">
          {insight.summary}
        </p>
      )}

      {/* Suggested actions */}
      {insight?.suggested_actions && insight.suggested_actions.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
            Suggested Actions
          </p>
          <ul className="space-y-1.5">
            {insight.suggested_actions.map((action, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                <span className="mt-0.5 flex-shrink-0 text-violet-500 font-bold">·</span>
                {action}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="mb-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {/* Feedback section */}
      {feedbackDone ? (
        <div className="text-xs text-slate-500 border-t border-violet-100 pt-3">
          Feedback recorded: <span className="font-medium capitalize">{feedbackDone}</span>. Thank you!
        </div>
      ) : (
        <div className="border-t border-violet-100 pt-3">
          {!showEditBox ? (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Was this helpful?</span>
              <button
                onClick={() => handleFeedback("accepted")}
                disabled={submittingFeedback}
                className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1 text-xs text-slate-600 hover:bg-green-50 hover:border-green-300 hover:text-green-700 disabled:opacity-50 transition-colors"
              >
                <ThumbsUp className="h-3 w-3" /> Helpful
              </button>
              <button
                onClick={() => setShowEditBox(true)}
                disabled={submittingFeedback}
                className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1 text-xs text-slate-600 hover:bg-amber-50 hover:border-amber-300 hover:text-amber-700 disabled:opacity-50 transition-colors"
              >
                <Edit2 className="h-3 w-3" /> Edit
              </button>
              <button
                onClick={() => handleFeedback("rejected")}
                disabled={submittingFeedback}
                className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1 text-xs text-slate-600 hover:bg-red-50 hover:border-red-300 hover:text-red-700 disabled:opacity-50 transition-colors"
              >
                <ThumbsDown className="h-3 w-3" /> Not helpful
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-xs text-slate-500">Your corrected version:</p>
              <textarea
                value={editedText}
                onChange={(e) => setEditedText(e.target.value)}
                placeholder="Enter your improved summary…"
                rows={3}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 resize-none"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => handleFeedback("edited", editedText)}
                  disabled={submittingFeedback || !editedText.trim()}
                  className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-500 disabled:opacity-50"
                >
                  Submit Edit
                </button>
                <button
                  onClick={() => setShowEditBox(false)}
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs hover:bg-slate-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
