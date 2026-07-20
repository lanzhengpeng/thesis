import { useCallback, useEffect, useMemo } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { buildGraph, type ModuleNodeData } from "../lib/graphBuilder";
import { GatewayNode } from "./GatewayNode";
import { ModuleNode } from "./ModuleNode";
import type { CheatSheetResponse } from "../types/cheatSheet";

const nodeTypes = {
  gateway: GatewayNode,
  module: ModuleNode,
  failedModule: ModuleNode,
} as NodeTypes;

interface ArchitectureGraphProps {
  data: CheatSheetResponse;
  onSelectModule: (data: ModuleNodeData) => void;
}

export function ArchitectureGraph({ data, onSelectModule }: ArchitectureGraphProps) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => buildGraph(data.call_graph, data.modules, data.api_map),
    [data]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes as Node[]);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges as Edge[]);

  // 当 data 变化时同步节点和边状态
  useEffect(() => {
    setNodes(initialNodes as Node[]);
    setEdges(initialEdges as Edge[]);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (node.data) {
        onSelectModule(node.data as ModuleNodeData);
      }
    },
    [onSelectModule]
  );

  return (
    <div style={{ flex: 1, position: "relative" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        attributionPosition="bottom-left"
      >
        <Background color="#cbd5e1" gap={16} />
        <Controls />
        <MiniMap
          nodeStrokeWidth={3}
          nodeColor={(node) => {
            if (node.type === "gateway") return "#1e293b";
            if (node.type === "failedModule") return "#ef4444";
            return "#3b82f6";
          }}
        />
      </ReactFlow>
    </div>
  );
}
