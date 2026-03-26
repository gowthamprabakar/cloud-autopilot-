"use client";

import Link from "next/link";
import {
  AlertTriangle, Atom, Camera, Package, Brain,
  Factory, CreditCard, Fingerprint, Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

// ── Domain data ──────────────────────────────────────────────────────────────

interface GapDomain {
  key: string;
  name: string;
  icon: LucideIcon;
  color: string;
  dotColor: string;
  description: string;
  tags: string[];
}

const GAP_DOMAINS: GapDomain[] = [
  {
    key: "quantum",
    name: "Quantum-Resilient Crypto",
    icon: Atom,
    color: "border-blue-500/30 hover:border-blue-500/50",
    dotColor: "bg-blue-400",
    description: "Post-quantum cryptographic readiness assessment, harvest-now-decrypt-later threat modeling, and lattice-based algorithm migration planning for cloud workloads.",
    tags: ["PQC", "NIST FIPS 203/204", "Key Encapsulation", "Crypto Agility"],
  },
  {
    key: "deepfake",
    name: "Deepfake & Synthetic Identity",
    icon: Camera,
    color: "border-purple-500/30 hover:border-purple-500/50",
    dotColor: "bg-purple-400",
    description: "Detection of AI-generated voice, video, and document fraud targeting authentication flows, KYC processes, and executive impersonation in cloud environments.",
    tags: ["Voice Cloning", "Face Swap", "Liveness Detection", "KYC Bypass"],
  },
  {
    key: "supply-chain",
    name: "Supply Chain Security",
    icon: Package,
    color: "border-emerald-500/30 hover:border-emerald-500/50",
    dotColor: "bg-emerald-400",
    description: "End-to-end software supply chain integrity: SBOM generation, dependency poisoning detection, Sigstore attestation verification, and eBPF rootkit scanning.",
    tags: ["SBOM", "Sigstore", "Dependency Confusion", "Build Provenance"],
  },
  {
    key: "agentic-ai",
    name: "Agentic AI Threats",
    icon: Brain,
    color: "border-cyan-500/30 hover:border-cyan-500/50",
    dotColor: "bg-cyan-400",
    description: "Multi-agent orchestration threat detection, autonomous AI swarm behavioral analysis, prompt injection chains, and tool-use abuse in LLM agent frameworks.",
    tags: ["Agent Swarms", "Tool Abuse", "Prompt Injection", "Autonomous Threats"],
  },
  {
    key: "ot-ics",
    name: "OT/ICS Critical Infrastructure",
    icon: Factory,
    color: "border-orange-500/30 hover:border-orange-500/50",
    dotColor: "bg-orange-400",
    description: "Industrial control system security: digital twin modeling, Purdue zone enforcement, protocol whitelisting (Modbus/DNP3/IEC 104), and nation-state TTP mapping.",
    tags: ["SCADA", "PLC", "Air Gap", "Purdue Model"],
  },
  {
    key: "llmjacking",
    name: "LLMjacking & GPU Abuse",
    icon: CreditCard,
    color: "border-red-500/30 hover:border-red-500/50",
    dotColor: "bg-red-400",
    description: "Detection of stolen LLM API credentials for unauthorized inference, GPU cryptojacking on ML instances, and model weight exfiltration from SageMaker/Bedrock.",
    tags: ["API Key Theft", "GPU Cryptojacking", "Model Theft", "Cost Explosion"],
  },
  {
    key: "federated-id",
    name: "Federated Identity Abuse",
    icon: Fingerprint,
    color: "border-pink-500/30 hover:border-pink-500/50",
    dotColor: "bg-pink-400",
    description: "Cross-cloud federated identity attack surface: SAML/OIDC token manipulation, golden SAML, Azure AD to AWS role chaining, and workload identity federation abuse.",
    tags: ["Golden SAML", "OIDC", "Role Chaining", "Token Replay"],
  },
];

// ── Domain card ──────────────────────────────────────────────────────────────

function DomainCard({ domain }: { domain: GapDomain }) {
  return (
    <div className={cn(
      "rounded-xl border bg-slate-800/50 p-5 flex flex-col gap-4 transition-colors",
      domain.color
    )}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className={cn("h-2.5 w-2.5 rounded-full", domain.dotColor)} />
          <h3 className="text-sm font-semibold text-white">{domain.name}</h3>
        </div>
        <span className="rounded-full bg-pink-500/10 border border-pink-500/20 px-2.5 py-0.5 text-[10px] font-semibold text-pink-400 uppercase tracking-wider">
          Wiz Cannot Cover
        </span>
      </div>

      {/* Description */}
      <p className="text-xs text-slate-400 leading-relaxed">{domain.description}</p>

      {/* Tags */}
      <div className="flex flex-wrap gap-1.5">
        {domain.tags.map((tag) => (
          <span key={tag} className="rounded-md bg-slate-700/50 px-2 py-0.5 text-[10px] text-slate-300 font-medium">
            {tag}
          </span>
        ))}
      </div>

      {/* Action button */}
      <div className="mt-auto pt-1">
        <Link
          href={`/dashboard/simulations?domain=${domain.key}` as any}
          className="inline-flex items-center gap-1.5 rounded-lg bg-pink-600 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-pink-500 transition-colors"
        >
          <Zap className="h-3.5 w-3.5" />
          Run Swarm Autopsy
        </Link>
      </div>
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function GapDomainsPage() {
  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <AlertTriangle className="h-6 w-6 text-pink-400" />
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-pink-400 tracking-wide">GAP DOMAINS</h1>
          <span className="rounded-full bg-pink-500/10 border border-pink-500/20 px-3 py-0.5 text-xs font-medium text-pink-300">
            {GAP_DOMAINS.length} Domains Wiz Cannot Cover
          </span>
        </div>
      </div>

      <p className="text-sm text-slate-400 max-w-2xl">
        Security domains beyond Wiz CNAPP coverage that require Swarm multi-agent simulation.
        Each domain represents an emerging threat category with no native cloud-vendor tooling.
      </p>

      {/* Domain grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {GAP_DOMAINS.map((domain) => (
          <DomainCard key={domain.key} domain={domain} />
        ))}
      </div>
    </div>
  );
}
