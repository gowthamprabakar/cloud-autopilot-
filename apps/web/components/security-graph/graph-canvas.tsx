"use client";
import { useEffect, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeProps,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "@dagrejs/dagre";
import {
  Database, Key, Zap, Server, Shield, Globe, Lock, EyeOff, Activity, Network,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { SecurityGraphNode, SecurityGraphEdge, GraphNodeType } from "@/lib/types";

// ── Node type styling maps ────────────────────────────────────────────────────

const NODE_BORDER_COLOR: Record<GraphNodeType, string> = {
  s3_bucket:       "border-l-blue-500",
  iam_role:        "border-l-purple-500",
  lambda:          "border-l-yellow-400",
  rds:             "border-l-orange-500",
  ec2:             "border-l-green-500",
  security_group:  "border-l-red-500",
  vpc:             "border-l-slate-400",
  subnet:          "border-l-slate-400",
  internet:        "border-l-red-600",
  kms_key:         "border-l-indigo-500",
  secrets_manager: "border-l-indigo-500",
  cloudtrail:      "border-l-teal-500",
};

const NODE_ICONS: Record<GraphNodeType, LucideIcon> = {
  s3_bucket:       Database,
  iam_role:        Key,
  lambda:          Zap,
  rds:             Database,
  ec2:             Server,
  security_group:  Shield,
  vpc:             Network,
  subnet:          Network,
  internet:        Globe,
  kms_key:         Lock,
  secrets_manager: EyeOff,
  cloudtrail:      Activity,
};

const NODE_ICON_COLOR: Record<GraphNodeType, string> = {
  s3_bucket:       "text-blue-500",
  iam_role:        "text-purple-500",
  lambda:          "text-yellow-400",
  rds:             "text-orange-500",
  ec2:             "text-green-500",
  security_group:  "text-red-500",
  vpc:             "text-slate-400",
  subnet:          "text-slate-400",
  internet:        "text-red-600",
  kms_key:         "text-indigo-500",
  secrets_manager: "text-indigo-500",
  cloudtrail:      "text-teal-500",
};

// ── Custom Node Component ─────────────────────────────────────────────────────

type SecurityNodeData = SecurityGraphNode & { isOnAttackPath: boolean };

function SecurityNode({ data, selected }: NodeProps) {
  const nodeData = data as SecurityNodeData;
  const Icon = NODE_ICONS[nodeData.node_type] ?? Server;
  const displayName = (nodeData.resource_name ?? nodeData.node_type).slice(0, 18);

  return (
    <div
      className={cn(
        "relative flex flex-col justify-between rounded-lg border border-l-4 bg-white shadow-md px-3 py-2 cursor-pointer transition-shadow hover:shadow-lg",
        NODE_BORDER_COLOR[nodeData.node_type],
        nodeData.isOnAttackPath && "ring-2 ring-red-500 ring-offset-1",
        selected && "shadow-lg ring-2 ring-blue-500 ring-offset-1"
      )}
      style={{ width: 180, minHeight: 80 }}
    >
      <Handle type="target" position={Position.Left} className="!bg-slate-300 !w-2 !h-2" />
      <Handle type="source" position={Position.Right} className="!bg-slate-300 !w-2 !h-2" />

      {/* Corner badges */}
      <div className="absolute top-1 right-1 flex gap-0.5">
        {nodeData.is_internet_facing && (
          <span className="text-xs" title="Internet-facing">⚡</span>
        )}
        {nodeData.is_sensitive_data && (
          <span className="text-xs" title="Sensitive data">🔒</span>
        )}
      </div>

      {/* Icon + name row */}
      <div className="flex items-center gap-2 pr-6">
        <Icon className={cn("h-4 w-4 shrink-0", NODE_ICON_COLOR[nodeData.node_type])} />
        <span className="text-xs font-bold text-slate-900 leading-tight truncate" title={nodeData.resource_name ?? undefined}>
          {displayName}
        </span>
      </div>

      {/* Node type label */}
      <p className="text-xs text-slate-400 mt-0.5 pl-6 capitalize">
        {nodeData.node_type.replace(/_/g, " ")}
      </p>

      {/* Bottom row */}
      {nodeData.finding_ids.length > 0 && (
        <div className="mt-1 flex items-center gap-1">
          <span className="rounded-full bg-red-100 px-1.5 py-0.5 text-xs font-semibold text-red-700">
            {nodeData.finding_ids.length} finding{nodeData.finding_ids.length !== 1 ? "s" : ""}
          </span>
        </div>
      )}
    </div>
  );
}

const NODE_TYPES = { securityNode: SecurityNode };

// ── Dagre layout ──────────────────────────────────────────────────────────────

function applyDagreLayout(nodes: Node[], edges: Edge[]): Node[] {
  if (nodes.length === 0) return nodes;

  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "LR", nodesep: 80, ranksep: 120 });

  nodes.forEach((node) => g.setNode(node.id, { width: 180, height: 80 }));
  edges.forEach((edge) => g.setEdge(edge.source, edge.target));

  dagre.layout(g);

  return nodes.map((node) => {
    const pos = g.node(node.id);
    if (!pos) return node;
    return { ...node, position: { x: pos.x - 90, y: pos.y - 40 } };
  });
}

// ── Transform helpers ─────────────────────────────────────────────────────────

function transformToFlowNodes(apiNodes: SecurityGraphNode[], attackPathNodeIds: Set<string>): Node[] {
  return apiNodes.map((node) => ({
    id: node.id,
    type: "securityNode",
    position: { x: 0, y: 0 },
    data: { ...node, isOnAttackPath: attackPathNodeIds.has(node.id) } as SecurityNodeData,
  }));
}

function transformToFlowEdges(apiEdges: SecurityGraphEdge[]): Edge[] {
  return apiEdges.map((edge) => ({
    id: edge.id,
    source: edge.source_node_id,
    target: edge.target_node_id,
    animated: edge.is_attack_path,
    style: edge.is_attack_path
      ? { stroke: "#ef4444", strokeWidth: 3 }
      : { stroke: "#6b7280", strokeWidth: 1, strokeDasharray: "5,5" },
    label: edge.edge_type.replace(/_/g, " "),
    labelStyle: { fontSize: 10, fill: "#6b7280" },
    data: edge,
  }));
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface GraphCanvasProps {
  apiNodes: SecurityGraphNode[];
  apiEdges: SecurityGraphEdge[];
  attackPathNodeIds: Set<string>;
  selectedNodeId: string | null;
  onNodeClick: (nodeId: string) => void;
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function GraphCanvas({
  apiNodes,
  apiEdges,
  attackPathNodeIds,
  onNodeClick,
}: GraphCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    const flowNodes = transformToFlowNodes(apiNodes, attackPathNodeIds);
    const flowEdges = transformToFlowEdges(apiEdges);
    const laid = applyDagreLayout(flowNodes, flowEdges);
    setNodes(laid);
    setEdges(flowEdges);
  }, [apiNodes, apiEdges, attackPathNodeIds, setNodes, setEdges]);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onNodeClick(node.id);
    },
    [onNodeClick]
  );

  if (apiNodes.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 text-slate-500 bg-slate-50">
        <Globe className="h-10 w-10 text-slate-300" />
        <p className="text-sm font-medium">No graph data available</p>
        <p className="text-xs">Seed demo data to visualise your security graph</p>
      </div>
    );
  }

  return (
    <div className="flex-1 h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={NODE_TYPES}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.2}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={20} color="#e2e8f0" />
        <Controls />
        <MiniMap
          nodeColor={(n) => {
            const d = n.data as SecurityNodeData | undefined;
            if (d?.isOnAttackPath) return "#ef4444";
            if (d?.is_internet_facing) return "#f97316";
            return "#94a3b8";
          }}
          maskColor="rgba(241,245,249,0.8)"
        />
      </ReactFlow>
    </div>
  );
}
