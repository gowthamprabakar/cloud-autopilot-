"use client";

import Link from "next/link";
import {
  ShieldCheck, Server, UserCog, Database, CloudCog,
  Radar, FileSearch, Bug, Brain, Globe,
  Zap, type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ── Coverage bar ─────────────────────────────────────────────────────────────

function CoverageBar({ value }: { value: number }) {
  const color =
    value >= 85 ? "bg-emerald-500" :
    value >= 75 ? "bg-yellow-500" : "bg-red-500";
  const textColor =
    value >= 85 ? "text-emerald-400" :
    value >= 75 ? "text-yellow-400" : "text-red-400";
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-400">Coverage</span>
        <span className={cn("text-sm font-bold", textColor)}>{value}%</span>
      </div>
      <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
        <div className={cn("h-full rounded-full transition-all duration-500", color)} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

// ── Module data ──────────────────────────────────────────────────────────────

interface WizModule {
  key: string;
  name: string;
  icon: LucideIcon;
  score: number;
  features: string;
  gap: string;
}

const WIZ_MODULES: WizModule[] = [
  {
    key: "cspm",
    name: "CSPM",
    icon: ShieldCheck,
    score: 92,
    features: "Cloud misconfiguration detection, compliance benchmarks, auto-remediation policies",
    gap: "Quantum-safe posture scoring, post-quantum encryption readiness checks",
  },
  {
    key: "cwpp",
    name: "CWPP",
    icon: Server,
    score: 88,
    features: "VM & container vulnerability scanning, runtime threat detection, serverless protection",
    gap: "eBPF rootkit detection, supply chain attestation for workloads",
  },
  {
    key: "ciem",
    name: "CIEM",
    icon: UserCog,
    score: 85,
    features: "IAM risk analysis, least-privilege recommendations, cross-cloud entitlement mapping",
    gap: "Federated identity abuse, deepfake-based social engineering detection",
  },
  {
    key: "dspm",
    name: "DSPM",
    icon: Database,
    score: 90,
    features: "Sensitive data discovery, data flow mapping, exposure monitoring",
    gap: "AI training data poisoning detection, LLM data exfiltration monitoring",
  },
  {
    key: "kspm",
    name: "KSPM",
    icon: CloudCog,
    score: 82,
    features: "Kubernetes cluster hardening, pod security policies, image scanning",
    gap: "Supply chain signing for Helm charts, SBOM coverage for cluster add-ons",
  },
  {
    key: "cdr",
    name: "CDR",
    icon: Radar,
    score: 87,
    features: "Real-time cloud threat detection, automated response playbooks, log correlation",
    gap: "Agentic AI swarm detection, multi-agent orchestration threat patterns",
  },
  {
    key: "iac",
    name: "IaC Scanning",
    icon: FileSearch,
    score: 94,
    features: "Terraform, CloudFormation & CDK pre-deploy scanning, drift detection",
    gap: "AI-generated IaC validation, LLM prompt injection in IaC pipelines",
  },
  {
    key: "uvm",
    name: "UVM",
    icon: Bug,
    score: 72,
    features: "Unified vulnerability management, agentless CVE scanning across compute",
    gap: "Zero-day prediction models, exploit chain simulation with AI agents",
  },
  {
    key: "ai-spm",
    name: "AI-SPM",
    icon: Brain,
    score: 78,
    features: "AI model inventory, ML pipeline security, model access governance",
    gap: "LLMjacking detection, GPU cryptojacking, model weight exfiltration",
  },
  {
    key: "asm",
    name: "ASM",
    icon: Globe,
    score: 98,
    features: "External attack surface monitoring, asset discovery, exposure scoring",
    gap: "Dark web credential correlation, nation-state campaign attribution",
  },
];

// ── Module card ──────────────────────────────────────────────────────────────

function ModuleCard({ mod }: { mod: WizModule }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-5 flex flex-col gap-4 hover:border-purple-500/30 transition-colors">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-purple-500/10">
          <mod.icon className="h-5 w-5 text-purple-400" />
        </div>
        <h3 className="text-base font-semibold text-white">{mod.name}</h3>
      </div>

      {/* Coverage score */}
      <CoverageBar value={mod.score} />

      {/* Features */}
      <p className="text-xs text-slate-400 leading-relaxed">{mod.features}</p>

      {/* Gap box */}
      <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-3">
        <div className="flex items-center gap-1.5 mb-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
          <span className="text-[10px] font-semibold text-red-400 uppercase tracking-wider">Covered by Swarm</span>
        </div>
        <p className="text-xs text-slate-400">{mod.gap}</p>
      </div>

      {/* Simulate button */}
      <div className="mt-auto">
        <Link
          href={`/dashboard/simulations?domain=${mod.key}` as any}
          className="inline-flex items-center gap-1.5 rounded-lg bg-purple-600 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-purple-500 transition-colors"
        >
          <Zap className="h-3.5 w-3.5" />
          Simulate
        </Link>
      </div>
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function WizCoveragePage() {
  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <ShieldCheck className="h-6 w-6 text-purple-400" />
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-purple-400 tracking-wide">WIZ CNAPP COVERAGE</h1>
          <span className="rounded-full bg-purple-500/10 border border-purple-500/20 px-3 py-0.5 text-xs font-medium text-purple-300">
            {WIZ_MODULES.length} Modules
          </span>
        </div>
      </div>

      <p className="text-sm text-slate-400 max-w-2xl">
        Comprehensive coverage analysis of Wiz CNAPP modules with gap identification.
        Each module shows current coverage score and areas requiring Swarm augmentation.
      </p>

      {/* Module grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {WIZ_MODULES.map((mod) => (
          <ModuleCard key={mod.key} mod={mod} />
        ))}
      </div>
    </div>
  );
}
