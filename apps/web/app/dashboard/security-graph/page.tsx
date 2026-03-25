"use client";
import { useState, useMemo } from "react";
import dynamic from "next/dynamic";
import { Spinner } from "@/components/ui/spinner";
import { useSecurityGraph } from "@/lib/hooks/use-security-graph";
import { apiClient } from "@/lib/api-client";
import AttackPathSidebar from "@/components/security-graph/attack-path-sidebar";
import NodeDetailDrawer from "@/components/security-graph/node-detail-drawer";
import type { SecurityGraphNode } from "@/lib/types";

// Dynamic import prevents SSR — @xyflow/react relies on browser APIs
const GraphCanvas = dynamic(
  () => import("@/components/security-graph/graph-canvas"),
  {
    ssr: false,
    loading: () => (
      <div className="flex-1 flex items-center justify-center gap-3 text-slate-500">
        <Spinner className="h-5 w-5" />
        <p className="text-sm">Loading graph...</p>
      </div>
    ),
  }
);

export default function SecurityGraphPage() {
  const { data, error, isLoading, mutate } = useSecurityGraph();
  const [selectedNodeId, setSelectedNodeId]   = useState<string | null>(null);
  const [selectedPathId, setSelectedPathId]   = useState<string | null>(null);
  const [seeding, setSeeding]                  = useState(false);

  const attackPathNodeIds = useMemo<Set<string>>(() => {
    if (!data || !selectedPathId) {
      // When no path selected, highlight ALL attack-path nodes
      const allPathNodeIds = new Set<string>();
      data?.attack_paths?.forEach((p) => p.node_path.forEach((id) => allPathNodeIds.add(id)));
      return allPathNodeIds;
    }
    const path = data.attack_paths.find((p) => p.id === selectedPathId);
    return new Set(path?.node_path ?? []);
  }, [data, selectedPathId]);

  const selectedNode = useMemo<SecurityGraphNode | null>(
    () => data?.nodes.find((n) => n.id === selectedNodeId) ?? null,
    [data, selectedNodeId]
  );

  async function handleSeedData() {
    setSeeding(true);
    try {
      await apiClient.post("/api/v1/security-graph/seed", {});
      await mutate();
    } finally {
      setSeeding(false);
    }
  }

  const stats = data?.stats ?? null;
  const nodes = data?.nodes ?? [];
  const edges = data?.edges ?? [];
  const attackPaths = data?.attack_paths ?? [];

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Page header */}
      <div className="flex items-center justify-between gap-4 px-5 py-3 border-b border-slate-200 bg-white shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold text-slate-900">Security Graph</h1>
          {isLoading && <Spinner className="h-4 w-4" />}
          {error && <span className="text-xs text-red-500">Failed to load graph</span>}
        </div>

        {/* Stats bar */}
        {stats && (
          <div className="hidden md:flex items-center gap-4 text-xs">
            <span className="text-slate-500">{stats.total_nodes} nodes</span>
            <span className="text-red-600 font-semibold">{stats.attack_path_nodes} on attack paths</span>
            <span className="text-orange-600">{stats.internet_facing} internet-facing</span>
            <span className="text-purple-600">{stats.sensitive_data_nodes} sensitive data</span>
          </div>
        )}

        <button
          onClick={handleSeedData}
          disabled={seeding}
          className="shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition-colors"
        >
          {seeding ? "Seeding..." : "Seed Demo Data"}
        </button>
      </div>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Attack paths sidebar */}
        <AttackPathSidebar
          attackPaths={attackPaths}
          selectedPathId={selectedPathId}
          onSelectPath={setSelectedPathId}
          graphStats={stats}
        />

        {/* Graph canvas */}
        <div className="relative flex flex-1 overflow-hidden bg-slate-50">
          <GraphCanvas
            apiNodes={nodes}
            apiEdges={edges}
            attackPathNodeIds={attackPathNodeIds}
            selectedNodeId={selectedNodeId}
            onNodeClick={setSelectedNodeId}
          />
        </div>
      </div>

      {/* Node detail drawer */}
      <NodeDetailDrawer
        node={selectedNode}
        onClose={() => setSelectedNodeId(null)}
      />
    </div>
  );
}
