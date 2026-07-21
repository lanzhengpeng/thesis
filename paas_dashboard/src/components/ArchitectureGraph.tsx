import { useCallback, useEffect, useMemo, type MouseEvent } from "react";
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

import { buildGraph, type MethodNodeData, type ModuleNodeData } from "../lib/graphBuilder";
import { ComponentNode } from "./ComponentNode";
import { GatewayNode } from "./GatewayNode";
import { MethodNode } from "./MethodNode";
import { ModuleNode } from "./ModuleNode";
import type { CheatSheetResponse } from "../types/cheatSheet";

const nodeTypes = {
  gateway: GatewayNode,
  module: ModuleNode,
  failedModule: ModuleNode,
  component: ComponentNode,
  method: MethodNode,
} as NodeTypes;

interface ArchitectureGraphProps {
  data: CheatSheetResponse;
  onSelectModule: (data: ModuleNodeData) => void;
  onSelectComponent: (componentId: string) => void;
}

export function ArchitectureGraph({ data, onSelectModule, onSelectComponent }: ArchitectureGraphProps) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => buildGraph(data.call_graph, data.modules, data.api_map, data.components),
    [data]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes as Node[]);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges as Edge[]);

  // 当 data 变化时同步节点和边状态
  useEffect(() => {
    setNodes(initialNodes as Node[]);
    setEdges(initialEdges as Edge[]);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  // 使用 onNodeClick 处理节点选中，拖拽不会触发点击
  const onNodeClick = useCallback(
    (_event: MouseEvent, node: Node) => {
      if (node.type === "component" && node.id) {
        onSelectComponent(node.id);
      } else if (node.type === "method" && node.data) {
        // 点击方法节点时展示其所属 CSM 组件详情
        const data = node.data as MethodNodeData;
        onSelectComponent(data.componentId);
      } else if (node.data) {
        onSelectModule(node.data as ModuleNodeData);
      }
    },
    [onSelectModule, onSelectComponent]
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
            if (node.type === "component") {
              const type = (node.data as { componentType?: string })?.componentType;
              if (type === "controller") return "#3b82f6";
              if (type === "service") return "#22c55e";
              if (type === "mapper") return "#8b5cf6";
            }
            return "#3b82f6";
          }}
        />
      </ReactFlow>
    </div>
  );
}
