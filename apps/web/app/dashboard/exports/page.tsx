"use client";

import { useState, useCallback } from "react";
import useSWR from "swr";
import {
  Download, FileJson, FileText, Code2, Shield, FileDown,
  ChevronDown, Loader2, CheckCircle2, Copy, Eye,
} from "lucide-react";
import { apiFetcher } from "@/lib/api-client";
import {
  exportJSON,
  exportMarkdown,
  exportExecutive,
  exportIaC,
} from "@/lib/hooks/use-exports";
import type { SimulationRun } from "@/lib/hooks/use-simulations";

// ── Constants ────────────────────────────────────────────────────────────────

type ExportFormat = "json" | "markdown" | "executive" | "iac";

interface IaCBundle {
  terraform?: string;
  cloudformation?: string;
  iam_policies?: string;
  detection_rules?: string;
  [key: string]: string | undefined;
}

const IAC_TAB_LABELS: Record<string, string> = {
  terraform: "Terraform",
  cloudformation: "CloudFormation",
  iam_policies: "IAM Policies",
  detection_rules: "Detection Rules",
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function downloadBlob(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Page Component ───────────────────────────────────────────────────────────

export default function ExportsPage() {
  // Fetch completed simulations
  const { data: simulations, isLoading: simsLoading } = useSWR<SimulationRun[]>(
    "/api/v1/simulations?status=completed&limit=50",
    apiFetcher,
  );

  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [activeFormat, setActiveFormat] = useState<ExportFormat | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [iacBundle, setIacBundle] = useState<IaCBundle | null>(null);
  const [iacTab, setIacTab] = useState<string>("terraform");
  const [generating, setGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const selectedSim = simulations?.find((s) => s.id === selectedRunId) ?? null;

  // ── Generate / Fetch ─────────────────────────────────────────────────────

  const generate = useCallback(
    async (format: ExportFormat) => {
      if (!selectedRunId) return;
      setGenerating(true);
      setActiveFormat(format);
      setPreview(null);
      setIacBundle(null);
      try {
        switch (format) {
          case "json": {
            const data = await exportJSON(selectedRunId);
            setPreview(JSON.stringify(data, null, 2));
            break;
          }
          case "markdown": {
            const md = await exportMarkdown(selectedRunId);
            setPreview(md);
            break;
          }
          case "executive": {
            const ex = await exportExecutive(selectedRunId);
            setPreview(ex);
            break;
          }
          case "iac": {
            const bundle = (await exportIaC(selectedRunId)) as IaCBundle;
            setIacBundle(bundle);
            const firstKey = Object.keys(bundle)[0] ?? "terraform";
            setIacTab(firstKey);
            setPreview(bundle[firstKey] ?? "");
            break;
          }
        }
      } catch (err: any) {
        setPreview(`Error: ${err.message ?? "Failed to generate export"}`);
      } finally {
        setGenerating(false);
      }
    },
    [selectedRunId],
  );

  // ── Download ─────────────────────────────────────────────────────────────

  const handleDownload = useCallback(() => {
    if (!preview || !activeFormat || !selectedRunId) return;
    const slug = selectedSim?.domain ?? selectedRunId;
    switch (activeFormat) {
      case "json":
        downloadBlob(preview, `${slug}-export.json`, "application/json");
        break;
      case "markdown":
        downloadBlob(preview, `${slug}-report.md`, "text/markdown");
        break;
      case "executive":
        downloadBlob(preview, `${slug}-executive-summary.md`, "text/markdown");
        break;
      case "iac": {
        const content = iacBundle?.[iacTab] ?? preview;
        downloadBlob(content, `${slug}-${iacTab}.tf`, "text/plain");
        break;
      }
    }
  }, [preview, activeFormat, selectedRunId, selectedSim, iacBundle, iacTab]);

  // ── Copy ─────────────────────────────────────────────────────────────────

  const handleCopy = useCallback(async () => {
    if (!preview) return;
    const content = activeFormat === "iac" ? (iacBundle?.[iacTab] ?? preview) : preview;
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [preview, activeFormat, iacBundle, iacTab]);

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-7xl px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Download className="h-6 w-6 text-blue-400" />
            <h1 className="text-2xl font-bold">Export Center</h1>
          </div>
          <p className="text-slate-400 text-sm">
            Generate and download simulation reports in multiple formats. Select a
            completed simulation to get started.
          </p>
        </div>

        {/* Simulation Selector */}
        <div className="mb-8 relative">
          <label className="block text-xs font-medium text-slate-400 mb-1.5">
            Simulation
          </label>
          <button
            onClick={() => setDropdownOpen((o) => !o)}
            className="flex items-center justify-between w-full max-w-md rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-left hover:border-slate-600 transition-colors"
          >
            {selectedSim ? (
              <span>
                <span className="font-medium text-white">{selectedSim.domain}</span>
                <span className="mx-2 text-slate-600">|</span>
                <span className="text-slate-400">{fmtDate(selectedSim.created_at)}</span>
                <span className="mx-2 text-slate-600">|</span>
                <span className="text-emerald-400">
                  {(selectedSim.confidence_score * 100).toFixed(0)}% confidence
                </span>
              </span>
            ) : (
              <span className="text-slate-500">
                {simsLoading ? "Loading simulations..." : "Select a simulation"}
              </span>
            )}
            <ChevronDown className="h-4 w-4 text-slate-500 shrink-0 ml-2" />
          </button>

          {dropdownOpen && (
            <div className="absolute z-50 mt-1 w-full max-w-md rounded-lg border border-slate-700 bg-slate-900 shadow-xl max-h-64 overflow-y-auto">
              {!simulations?.length && (
                <p className="px-4 py-3 text-sm text-slate-500">
                  No completed simulations found.
                </p>
              )}
              {simulations?.map((sim) => (
                <button
                  key={sim.id}
                  onClick={() => {
                    setSelectedRunId(sim.id);
                    setDropdownOpen(false);
                    setPreview(null);
                    setActiveFormat(null);
                    setIacBundle(null);
                  }}
                  className="flex w-full items-center gap-3 px-4 py-2.5 text-sm hover:bg-slate-800 transition-colors text-left"
                >
                  <Shield className="h-4 w-4 text-blue-400 shrink-0" />
                  <span className="flex-1 truncate">
                    <span className="font-medium text-white">{sim.domain}</span>
                    <span className="mx-2 text-slate-600">|</span>
                    <span className="text-slate-400">{fmtDate(sim.created_at)}</span>
                  </span>
                  <span className="text-emerald-400 text-xs">
                    {(sim.confidence_score * 100).toFixed(0)}%
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Export Option Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {/* JSON */}
          <ExportCard
            icon={FileJson}
            title="JSON Export"
            description="Full structured data dump of the simulation run, findings, agents, and gates."
            buttonLabel="Download JSON"
            active={activeFormat === "json"}
            disabled={!selectedRunId}
            loading={generating && activeFormat === "json"}
            onClick={() => generate("json")}
          />
          {/* Markdown */}
          <ExportCard
            icon={FileText}
            title="Markdown Report"
            description="Formatted human-readable report with findings, recommendations, and scoring."
            buttonLabel="Generate Report"
            active={activeFormat === "markdown"}
            disabled={!selectedRunId}
            loading={generating && activeFormat === "markdown"}
            onClick={() => generate("markdown")}
          />
          {/* Executive */}
          <ExportCard
            icon={Shield}
            title="Executive Summary"
            description="CISO-ready one-pager with risk posture, critical findings, and remediation priorities."
            buttonLabel="Generate"
            active={activeFormat === "executive"}
            disabled={!selectedRunId}
            loading={generating && activeFormat === "executive"}
            onClick={() => generate("executive")}
          />
          {/* IaC */}
          <ExportCard
            icon={Code2}
            title="IaC Bundle"
            description="Terraform, CloudFormation, IAM policies, and detection rules extracted from findings."
            buttonLabel="Extract Code"
            active={activeFormat === "iac"}
            disabled={!selectedRunId}
            loading={generating && activeFormat === "iac"}
            onClick={() => generate("iac")}
          />
        </div>

        {/* Preview Panel */}
        {(preview || generating) && (
          <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
            {/* Preview Header */}
            <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3">
              <div className="flex items-center gap-2">
                <Eye className="h-4 w-4 text-blue-400" />
                <span className="text-sm font-medium text-white">
                  Preview
                  {activeFormat && (
                    <span className="ml-2 text-slate-500">
                      ({activeFormat === "iac" ? "IaC Bundle" : activeFormat})
                    </span>
                  )}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopy}
                  disabled={!preview}
                  className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition-colors disabled:opacity-40"
                >
                  {copied ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                  {copied ? "Copied" : "Copy"}
                </button>
                <button
                  onClick={handleDownload}
                  disabled={!preview}
                  className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-500 transition-colors disabled:opacity-40"
                >
                  <FileDown className="h-3.5 w-3.5" />
                  Download
                </button>
              </div>
            </div>

            {/* IaC Tabs */}
            {activeFormat === "iac" && iacBundle && (
              <div className="flex border-b border-slate-800 bg-slate-900/50">
                {Object.keys(iacBundle).map((key) => (
                  <button
                    key={key}
                    onClick={() => {
                      setIacTab(key);
                      setPreview(iacBundle[key] ?? "");
                    }}
                    className={`px-4 py-2 text-xs font-medium transition-colors border-b-2 ${
                      iacTab === key
                        ? "border-blue-400 text-blue-400"
                        : "border-transparent text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    {IAC_TAB_LABELS[key] ?? key}
                  </button>
                ))}
              </div>
            )}

            {/* Content */}
            <div className="max-h-[32rem] overflow-auto p-5">
              {generating ? (
                <div className="flex items-center justify-center py-16">
                  <Loader2 className="h-6 w-6 text-blue-400 animate-spin" />
                  <span className="ml-3 text-sm text-slate-400">Generating...</span>
                </div>
              ) : activeFormat === "json" || activeFormat === "iac" ? (
                <pre className="text-xs leading-relaxed text-slate-300 font-mono whitespace-pre-wrap break-words">
                  {activeFormat === "iac" ? (iacBundle?.[iacTab] ?? preview) : preview}
                </pre>
              ) : (
                <div className="prose prose-invert prose-sm max-w-none text-slate-300">
                  <pre className="whitespace-pre-wrap text-sm leading-relaxed">
                    {preview}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Export Card ───────────────────────────────────────────────────────────────

function ExportCard({
  icon: Icon,
  title,
  description,
  buttonLabel,
  active,
  disabled,
  loading,
  onClick,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  buttonLabel: string;
  active: boolean;
  disabled: boolean;
  loading: boolean;
  onClick: () => void;
}) {
  return (
    <div
      className={`rounded-xl border p-5 transition-colors ${
        active
          ? "border-blue-500/50 bg-blue-600/10"
          : "border-slate-800 bg-slate-900 hover:border-slate-700"
      }`}
    >
      <div className="flex items-center gap-2.5 mb-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-800">
          <Icon className="h-4 w-4 text-blue-400" />
        </div>
        <h3 className="text-sm font-semibold text-white">{title}</h3>
      </div>
      <p className="text-xs text-slate-400 leading-relaxed mb-4">{description}</p>
      <button
        onClick={onClick}
        disabled={disabled || loading}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-slate-800 px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {loading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Download className="h-3.5 w-3.5" />
        )}
        {loading ? "Generating..." : buttonLabel}
      </button>
    </div>
  );
}
