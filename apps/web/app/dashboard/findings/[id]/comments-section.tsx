"use client";
import { useState } from "react";
import { useFindingComments, addComment, deleteComment } from "@/lib/hooks/use-finding-comments";
import { Trash2 } from "lucide-react";

interface CommentsSectionProps {
  findingId: string;
}

export function CommentsSection({ findingId }: CommentsSectionProps) {
  const { comments, isLoading, mutate } = useFindingComments(findingId);
  const [commentBody, setCommentBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  async function handleAddComment(e: React.FormEvent) {
    e.preventDefault();
    if (!commentBody.trim()) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await addComment(findingId, commentBody.trim());
      await mutate();
      setCommentBody("");
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Failed to post comment");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeleteComment(commentId: string) {
    if (!window.confirm("Delete this comment?")) return;
    try {
      await deleteComment(findingId, commentId);
      await mutate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete comment");
    }
  }

  return (
    <section className="mt-6">
      <h2 className="text-sm font-semibold text-slate-700 mb-3">Comments</h2>

      {/* Comment list */}
      <div className="space-y-3">
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(2)].map((_, i) => (
              <div key={i} className="bg-white border border-slate-200 rounded-lg p-4 animate-pulse">
                <div className="flex items-center justify-between mb-2">
                  <div className="h-3 w-32 rounded bg-slate-200" />
                  <div className="h-3 w-24 rounded bg-slate-200" />
                </div>
                <div className="h-4 w-full rounded bg-slate-100 mt-1" />
                <div className="h-4 w-3/4 rounded bg-slate-100 mt-1" />
              </div>
            ))}
          </div>
        ) : (
          <>
            {comments.map(c => (
              <div key={c.id} className="bg-white border border-slate-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-slate-600">
                    {c.author_email ?? "Unknown"}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">
                      {new Date(c.created_at).toLocaleString()}
                    </span>
                    <button
                      onClick={() => handleDeleteComment(c.id)}
                      className="text-slate-300 hover:text-red-500 transition-colors"
                      aria-label="Delete comment"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
                <p className="text-sm text-slate-700 whitespace-pre-wrap">{c.body}</p>
              </div>
            ))}
            {comments.length === 0 && (
              <p className="text-sm text-slate-400 italic">No comments yet.</p>
            )}
          </>
        )}
      </div>

      {/* Add comment form */}
      <form onSubmit={handleAddComment} className="mt-4">
        <textarea
          value={commentBody}
          onChange={e => setCommentBody(e.target.value)}
          placeholder="Add a comment..."
          className="w-full rounded-lg border border-slate-300 p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          rows={3}
        />
        {submitError && <p className="text-sm text-red-500 mt-1">{submitError}</p>}
        <div className="flex justify-end mt-2">
          <button
            type="submit"
            disabled={!commentBody.trim() || submitting}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {submitting ? "Posting…" : "Post Comment"}
          </button>
        </div>
      </form>
    </section>
  );
}
