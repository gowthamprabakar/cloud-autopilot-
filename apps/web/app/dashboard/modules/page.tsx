"use client";

import Link from "next/link";
import {
  ShieldCheck, Bug, UserCog, Network, Radar, Route,
  CloudCog, Atom, Lock, Eye, FileSearch, Server,
  LayoutDashboard, Zap, Shield, Globe, Database,
  Brain, Workflow, Fingerprint, AlertTriangle, Radio,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ── Module definitions ───────────────────────────────────────────────────────

interface ModuleDef {
  id: string;
  name: string;
  description: string;
  icon: LucideIcon;
  domain: string;
  status: "active" | "available";
}

const WIZ_MODULES: ModuleDef[] = [
  { id: "cspm",  name: "CSPM",  description: "Cloud Security Posture Management — misconfig detection & compliance scoring", icon: ShieldCheck, domain: "cspm", status: "active" },
  { id: "cwpp",  name: "CWPP",  description: "Cloud Workload Protection — VM, container & serverless vulnerability assessment", icon: Server, domain: "cwpp", status: "active" },
  { id: "ciem",  name: "CIEM",  description: "Cloud Infrastructure Entitlement Management — IAM risk & least privilege", icon: UserCog, domain: "ciem", status: "active" },
  { id: "dspm",  name: "DSPM",  description: "Data Security Posture Management — sensitive data discovery & exposure tracking", icon: Database, domain: "dspm", status: "active" },
  { id: "cnapp", name: "CNAPP", description: "Cloud-Native Application Protection Platform — unified risk correlation", icon: Shield, domain: "cnapp", status: "active" },
  { id: "kspm",  name: "KSPM",  description: "Kubernetes Security Posture Management — cluster hardening & runtime policy", icon: CloudCog, domain: "kspm", status: "available" },
  { id: "iac",   name: "IaC Scanning", description: "Infrastructure-as-Code analysis — Terraform, CloudFormation & CDK scanning", icon: FileSearch, domain: "iac", status: "available" },
  { id: "vuln",  name: "Vulnerability Management", description: "Agentless CVE scanning across compute, containers & packages", icon: Bug, domain: "vuln", status: "active" },
  { id: "cdr",   name: "CDR",   description: "Cloud Detection & Response — real-time threat detection & automated response", icon: Radar, domain: "cdr", status: "active" },
  { id: "apm",   name: "Attack Path", description: "Attack path analysis — graph-based toxic combination discovery", icon: Route, domain: "attack-path", status: "active" },
];

const GAP_MODULES: ModuleDef[] = [
  { id: "omnisec",   name: "OmniSec Simulation", description: "15-agent swarm simulation engine for adversarial & compliance testing", icon: Atom, domain: "omnisec", status: "active" },
  { id: "drift",     name: "Drift Detection",    description: "Real-time config drift tracking across IaC baseline & live state", icon: Workflow, domain: "drift", status: "active" },
  { id: "identity",  name: "Identity Intelligence", description: "Behavioral identity analytics — anomalous access & credential abuse", icon: Fingerprint, domain: "identity", status: "available" },
  { id: "exposure",  name: "Exposure Management", description: "External attack surface monitoring — public asset & exposure scoring", icon: Globe, domain: "exposure", status: "available" },
  { id: "runtime",   name: "Runtime Protection",  description: "eBPF-powered workload runtime security — process & network anomaly", icon: Eye, domain: "runtime", status: "available" },
  { id: "ai-soc",    name: "AI SOC Copilot",      description: "LLM-powered security operations — alert triage, investigation & response", icon: Brain, domain: "ai-soc", status: "active" },
  { id: "threat-intel", name: "Threat Intelligence", description: "Curated threat feeds with cloud-native context enrichment", icon: Radio, domain: "threat-intel", status: "available" },
];

// ── Module card ──────────────────────────────────────────────────────────────

function ModuleCard({ mod }: { mod: ModuleDef }) {
  const isActive = mod.status === "active";
  return (
    <div className={cn(
      "group rounded-xl border p-5 flex flex-col gap-3 transition-all",
      isActive
        ? "border-slate-700 bg-slate-800/50 hover:border-blue-500/40 hover:bg-slate-800"
        : "border-slate-700/50 bg-slate-800/30 opacity-75 hover:opacity-100",
    )}>
      <div className="flex items-center justify-between">
        <div className={cn(
          "flex items-center justify-center h-10 w-10 rounded-lg",
          isActive ? "bg-blue-500/10" : "bg-slate-700/50"
        )}>
          <mod.icon className={cn("h-5 w-5", isActive ? "text-blue-400" : "text-slate-500")} />
        </div>
        <span className={cn(
          "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
          isActive
            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
            : "bg-slate-600/10 text-slate-400 border border-slate-600/20",
        )}>
          <span className={cn("h-1.5 w-1.5 rounded-full", isActive ? "bg-emerald-400" : "bg-slate-500")} />
          {isActive ? "Active" : "Available"}
        </span>
      </div>

      <div>
        <h3 className="text-sm font-semibold text-white">{mod.name}</h3>
        <p className="text-xs text-slate-400 mt-1 line-clamp-2">{mod.description}</p>
      </div>

      <div className="mt-auto pt-2">
        <Link
          href={`/dashboard/simulations?domain=${mod.domain}` as any}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-xs font-medium transition-colors",
            isActive
              ? "bg-blue-600 text-white hover:bg-blue-500"
              : "bg-slate-700 text-slate-300 hover:bg-slate-600",
          )}
        >
          <Zap className="h-3.5 w-3.5" />
          Launch
        </Link>
      </div>
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function ModulesPage() {
  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <LayoutDashboard className="h-6 w-6 text-blue-400" />
        <div>
          <h1 className="text-xl font-bold text-white">Security Modules</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            CNAPP &amp; Gap domain modules — click Launch to run simulations
          </p>
        </div>
      </div>

      {/* Wiz CNAPP Modules */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <Shield className="h-4 w-4 text-blue-400" />
          <h2 className="text-base font-semibold text-white">Wiz CNAPP Modules</h2>
          <span className="text-xs text-slate-500 ml-1">({WIZ_MODULES.length})</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {WIZ_MODULES.map((mod) => (
            <ModuleCard key={mod.id} mod={mod} />
          ))}
        </div>
      </section>

      {/* Gap Domain Modules */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="h-4 w-4 text-orange-400" />
          <h2 className="text-base font-semibold text-white">Gap Domain Modules</h2>
          <span className="text-xs text-slate-500 ml-1">({GAP_MODULES.length})</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {GAP_MODULES.map((mod) => (
            <ModuleCard key={mod.id} mod={mod} />
          ))}
        </div>
      </section>
    </div>
  );
}
