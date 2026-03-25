"use client";
import { useState } from "react";
import {
  FileText,
  Sparkles,
  ChevronDown,
  ChevronRight,
  Cpu,
  Tag,
} from "lucide-react";
import {
  usePrompts,
  seedPrompts,
  type PromptTemplate,
} from "@/lib/hooks/use-prompts";
import { Spinner } from "@/components/ui/spinner";

const CATEGORIES = [
  "all",
  "finding_summary",
  "remediation",
  "root_cause",
  "governance",
  "general",
] as const;

type Category = (typeof CATEGORIES)[number];

const categoryColors: Record<string, string> = {
  finding_summary: "bg-blue-500/20 text-blue-400",
  remediation: "bg-green-500/20 text-green-400",
  root_cause: "bg-amber-500/20 text-amber-400",
  governance: "bg-purple-500/20 text-purple-400",
  general: "bg-slate-500/20 text-slate-400",
};

function CategoryBadge({ category }: { category: string }) {
  const color = categoryColors[category] ?? "bg-slate-500/20 text-slate-400";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${color}`}
    >
      <Tag className="h-3 w-3" />
      {category}
    </span>
  );
}

function VersionBadge({ version }: { version: number }) {
  return (
    <span className="inline-flex items-center rounded-md bg-indigo-500/20 text-indigo-400 px-1.5 py-0.5 text-xs font-mono font-medium">
      v{version}
    </span>
  );
}

function PromptRow({ prompt }: { prompt: PromptTemplate }) {
  const [expanded, setExpanded] = useState(false);
  const truncated =
    prompt.template.length > 100
      ? prompt.template.slice(0, 100) + "..."
      : prompt.template;

  return (
    <>
      <tr
        className="border-b border-slate-700/50 hover:bg-slate-800/50 cursor-pointer transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            {expanded ? (
              <ChevronDown className="h-4 w-4 text-slate-500 shrink-0" />
            ) : (
              <ChevronRight className="h-4 w-4 text-slate-500 shrink-0" />
            )}
            <span className="font-semibold text-white text-sm">
              {prompt.name}
            </span>
          </div>
        </td>
        <td className="px-4 py-3">
          <VersionBadge version={prompt.version} />
        </td>
        <td className="px-4 py-3">
          <CategoryBadge category={prompt.category} />
        </td>
        <td className="px-4 py-3">
          <span className="inline-flex items-center gap-1 text-xs text-slate-400">
            <Cpu className="h-3 w-3" />
            {prompt.model_id}
          </span>
        </td>
        <td className="px-4 py-3 max-w-xs">
          <span className="text-xs text-slate-400 font-mono">{truncated}</span>
        </td>
        <td className="px-4 py-3 text-center">
          <span
            className={`inline-block h-2.5 w-2.5 rounded-full ${
              prompt.is_active ? "bg-green-400" : "bg-slate-600"
            }`}
            title={prompt.is_active ? "Active" : "Inactive"}
          />
        </td>
      </tr>
      {expanded && (
        <tr className="border-b border-slate-700/50 bg-slate-800/30">
          <td colSpan={6} className="px-4 py-4">
            <div className="rounded-lg bg-slate-900 border border-slate-700 p-4">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-2 font-medium">
                Full Template
              </p>
              <pre className="text-sm text-slate-300 font-mono whitespace-pre-wrap leading-relaxed">
                {prompt.template}
              </pre>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function AIPromptRegistryPage() {
  const { prompts, isLoading, error, mutate } = usePrompts();
  const [seeding, setSeeding] = useState(false);
  const [seedResult, setSeedResult] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<Category>("all");

  async function handleSeed() {
    setSeeding(true);
    setSeedResult(null);
    try {
      const result = await seedPrompts();
      setSeedResult(`Seeded ${result.seeded} prompt template(s).`);
      mutate();
    } catch {
      setSeedResult("Failed to seed prompts.");
    } finally {
      setSeeding(false);
    }
  }

  const filtered =
    categoryFilter === "all"
      ? prompts
      : prompts.filter((p) => p.category === categoryFilter);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-blue-400" />
            <h1 className="text-xl font-bold text-white">
              AI Prompt Registry
            </h1>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Manage versioned prompt templates used by AI copilot features across
            the platform.
          </p>
        </div>
        <button
          onClick={handleSeed}
          disabled={seeding}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          <Sparkles className="h-4 w-4" />
          {seeding ? "Seeding..." : "Seed Defaults"}
        </button>
      </div>

      {/* Seed result banner */}
      {seedResult && (
        <div
          className={`rounded-lg border px-4 py-2.5 text-sm ${
            seedResult.startsWith("Failed")
              ? "border-red-500/30 bg-red-500/10 text-red-400"
              : "border-green-500/30 bg-green-500/10 text-green-400"
          }`}
        >
          {seedResult}
        </div>
      )}

      {/* Category filter */}
      <div className="flex items-center gap-3">
        <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">
          Category
        </label>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value as Category)}
          className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {CATEGORIES.map((cat) => (
            <option key={cat} value={cat}>
              {cat === "all" ? "All Categories" : cat.replace(/_/g, " ")}
            </option>
          ))}
        </select>
        <span className="text-xs text-slate-500">
          {filtered.length} template{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Loading / Error */}
      {isLoading && (
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Spinner className="h-4 w-4" /> Loading prompt templates...
        </div>
      )}
      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2.5 text-sm text-red-400">
          Failed to load prompts. Make sure the API is running.
        </div>
      )}

      {/* Table */}
      {!isLoading && !error && (
        <div className="rounded-xl border border-slate-700 bg-slate-800/50 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-700 bg-slate-800">
                  <th className="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Version
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Category
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Model
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Template
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider text-center">
                    Active
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-4 py-12 text-center text-sm text-slate-500"
                    >
                      No prompt templates found.{" "}
                      {prompts.length === 0
                        ? 'Click "Seed Defaults" to get started.'
                        : "Try a different category filter."}
                    </td>
                  </tr>
                ) : (
                  filtered.map((prompt) => (
                    <PromptRow key={prompt.id} prompt={prompt} />
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
