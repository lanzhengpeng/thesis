import { useCallback, useEffect, useMemo, useRef, type MouseEvent } from "react";
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

import {
  buildGraph,
  DEFAULT_EDGE_ZINDEX,
  DIMMED_EDGE_ZINDEX,
  DIMMED_NODE_ZINDEX,
  FOCUSED_EDGE_ZINDEX,
  type MethodNodeData,
  type ModuleNodeData,
} from "../lib/graphBuilder";
import { ComponentNode } from "../nodes/ComponentNode";
import { GatewayNode } from "../nodes/GatewayNode";
import { MethodNode } from "../nodes/MethodNode";
import { ModuleNode } from "../nodes/ModuleNode";
import type { CheatSheetResponse } from "../../../types/cheatSheet";

const nodeTypes: NodeTypes = {
  gateway: GatewayNode,
  module: ModuleNode,
  failedModule: ModuleNode,
  component: ComponentNode,
  method: MethodNode,
};

interface ArchitectureGraphProps {
  data: CheatSheetResponse;
  onSelectModule: (data: ModuleNodeData) => void;
  onSelectComponent: (componentId: string) => void;
}

function getParentModuleId(node: Node, nodeMap: Map<string, Node>): string | null {
  if (node.type === "module" || node.type === "failedModule") return node.id;
  if (!node.parentId) return null;

  const parent = nodeMap.get(node.parentId);
  if (!parent) return null;

  if (parent.type === "module" || parent.type === "failedModule") {
    return parent.id;
  }
  if (parent.parentId) {
    return parent.parentId;
  }
  return null;
}

export function ArchitectureGraph({ data, onSelectModule, onSelectComponent }: ArchitectureGraphProps) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => buildGraph(data.call_graph, data.modules, data.api_map, data.components),
    [data]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes as Node[]);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges as Edge[]);

  // 当前真实处于悬浮状态的最深层级节点 ID（方法级优先级由事件顺序 + stopPropagation 保证）
  const hoveredNodeIdRef = useRef<string | null>(null);
  const selectedModuleIdRef = useRef<string | null>(null);
  const selectedComponentIdRef = useRef<string | null>(null);

  const defaultNodeZIndexMap = useMemo(() => {
    const map = new Map<string, number>();
    initialNodes.forEach((n) => map.set(n.id, n.zIndex ?? 0));
    return map;
  }, [initialNodes]);

  // 当 data 变化时同步节点和边状态
  useEffect(() => {
    setNodes(initialNodes as Node[]);
    setEdges(initialEdges as Edge[]);
    hoveredNodeIdRef.current = null;
    selectedModuleIdRef.current = null;
    selectedComponentIdRef.current = null;
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  // 状态 1：默认基准状态（Mouse Leave 恢复状态）
  const resetToDefault = useCallback(() => {
    setNodes((prev) =>
      prev.map((node) => ({
        ...node,
        style: { ...node.style, opacity: 1 },
        zIndex: defaultNodeZIndexMap.get(node.id) ?? node.zIndex,
      }))
    );

    setEdges((prev) =>
      prev.map((edge) => {
        const edgeType = edge.data?.edgeType;
        const isGatewayEdge = !edgeType;

        if (edgeType === "crossMethod" || edgeType === "crossModule" || edgeType === "inner") {
          return {
            ...edge,
            hidden: true,
            animated: false,
            selected: false,
            zIndex: DEFAULT_EDGE_ZINDEX,
            style: edge.data?.defaultStyle || edge.style,
          };
        }

        return {
          ...edge,
          hidden: false,
          selected: false,
          animated: isGatewayEdge,
          zIndex: DEFAULT_EDGE_ZINDEX,
          style: edge.data?.defaultStyle || edge.style,
        };
      })
    );
  }, [defaultNodeZIndexMap, setEdges, setNodes]);

  // 状态 2：悬浮到模块外框上（Module-Level Hover）
  const enterModuleFocus = useCallback(
    (moduleId: string) => {
      const relatedModuleIds = new Set<string>([moduleId]);
      const highlightedCrossModuleEdgeIds = new Set<string>();

      edges.forEach((edge) => {
        if (edge.data?.edgeType === "crossModule") {
          if (edge.source === moduleId || edge.target === moduleId) {
            highlightedCrossModuleEdgeIds.add(edge.id);
            relatedModuleIds.add(edge.source);
            relatedModuleIds.add(edge.target);
          }
        }
      });

      setNodes((prev) => {
        const nodeMap = new Map(prev.map((n) => [n.id, n]));

        return prev.map((node) => {
          const nodeModuleId = getParentModuleId(node, nodeMap);
          const isRelated = nodeModuleId ? relatedModuleIds.has(nodeModuleId) : false;

          if (isRelated) {
            return {
              ...node,
              style: { ...node.style, opacity: 1 },
              zIndex: defaultNodeZIndexMap.get(node.id) ?? node.zIndex,
            };
          }
          return {
            ...node,
            style: { ...node.style, opacity: 0.2 },
            zIndex: DIMMED_NODE_ZINDEX,
          };
        });
      });

      setEdges((prev) =>
        prev.map((edge) => {
          const edgeType = edge.data?.edgeType;

          if (edgeType === "crossModule") {
            if (highlightedCrossModuleEdgeIds.has(edge.id)) {
              return {
                ...edge,
                hidden: false,
                animated: true,
                selected: true,
                zIndex: FOCUSED_EDGE_ZINDEX,
                style: { ...edge.style, opacity: 1, strokeWidth: 3 },
              };
            }
            return { ...edge, hidden: true, selected: false };
          }

          if (edgeType === "crossMethod" || edgeType === "inner") {
            return { ...edge, hidden: true, selected: false };
          }

          return {
            ...edge,
            hidden: false,
            selected: false,
            animated: false,
            zIndex: DEFAULT_EDGE_ZINDEX,
            style: edge.data?.defaultStyle || edge.style,
          };
        })
      );
    },
    [defaultNodeZIndexMap, edges, setEdges, setNodes]
  );

  // 状态 3：悬浮到具体方法上（Method-Level Hover）
  const enterMethodFocus = useCallback(
    (methodId: string) => {
      const relatedMethodIds = new Set<string>([methodId]);
      const relatedEdgeIds = new Set<string>();

      edges.forEach((edge) => {
        const edgeType = edge.data?.edgeType;
        if (edgeType === "inner" || edgeType === "crossMethod") {
          if (edge.source === methodId || edge.target === methodId) {
            relatedEdgeIds.add(edge.id);
            relatedMethodIds.add(edge.source);
            relatedMethodIds.add(edge.target);
          }
        }
      });

      setNodes((prev) => {
        return prev.map((node) => {
          // 方法级悬浮时，模块与组件保持中性不突出，仅对方法节点做高亮/暗化
          if (node.type === "method") {
            if (relatedMethodIds.has(node.id)) {
              return {
                ...node,
                style: { ...node.style, opacity: 1 },
                zIndex: defaultNodeZIndexMap.get(node.id) ?? node.zIndex,
              };
            }
            return {
              ...node,
              style: { ...node.style, opacity: 0.2 },
              zIndex: defaultNodeZIndexMap.get(node.id) ?? node.zIndex,
            };
          }

          return {
            ...node,
            style: { ...node.style, opacity: 1 },
            zIndex: defaultNodeZIndexMap.get(node.id) ?? node.zIndex,
          };
        });
      });

      setEdges((prev) =>
        prev.map((edge) => {
          const edgeType = edge.data?.edgeType;

          if (edgeType === "crossModule") {
            return { ...edge, hidden: true, selected: false };
          }

          if (relatedEdgeIds.has(edge.id)) {
            return {
              ...edge,
              hidden: false,
              animated: true,
              selected: true,
              zIndex: FOCUSED_EDGE_ZINDEX,
              style: { ...edge.style, opacity: 1, strokeWidth: 2.5 },
            };
          }

          if (edgeType === "inner" || edgeType === "crossMethod") {
            return {
              ...edge,
              hidden: true,
              selected: false,
              animated: false,
              zIndex: DIMMED_EDGE_ZINDEX,
              style: edge.data?.defaultStyle || edge.style,
            };
          }

          return {
            ...edge,
            hidden: false,
            selected: false,
            animated: true,
            zIndex: DEFAULT_EDGE_ZINDEX,
            style: edge.data?.defaultStyle || edge.style,
          };
        })
      );
    },
    [defaultNodeZIndexMap, edges, setEdges, setNodes]
  );

  const updatePanelSelection = useCallback(
    (node: Node) => {
      if (node.type === "method" && node.data) {
        const methodData = node.data as MethodNodeData;
        if (selectedComponentIdRef.current !== methodData.componentId) {
          selectedComponentIdRef.current = methodData.componentId;
          onSelectComponent(methodData.componentId);
        }
      } else if (node.type === "component" && node.id) {
        if (selectedComponentIdRef.current !== node.id) {
          selectedComponentIdRef.current = node.id;
          onSelectComponent(node.id);
        }
      } else if ((node.type === "module" || node.type === "failedModule") && node.data) {
        if (selectedModuleIdRef.current !== node.id) {
          selectedModuleIdRef.current = node.id;
          onSelectModule(node.data as ModuleNodeData);
        }
      }
    },
    [onSelectComponent, onSelectModule]
  );

  const onNodeMouseEnter = useCallback(
    (event: MouseEvent, node: Node) => {
      // 1. 阻止事件冒泡到父级（模块外框）
      event.stopPropagation();

      // 防抖：重复进入同一节点时不重复计算
      if (hoveredNodeIdRef.current === node.id) return;
      hoveredNodeIdRef.current = node.id;

      // 同步更新右侧面板（带 ref 去重，避免高频渲染）
      updatePanelSelection(node);

      if (node.type === "method") {
        // 执行【方法级】双向依赖高亮、Z-index 置顶等逻辑
        enterMethodFocus(node.id);
      } else if (node.type === "module" || node.type === "failedModule") {
        // 执行【模块级】依赖高亮逻辑
        enterModuleFocus(node.id);
      }
    },
    [enterMethodFocus, enterModuleFocus, updatePanelSelection]
  );

  const onNodeMouseLeave = useCallback(
    (event: MouseEvent, node: Node) => {
      // 1. 阻止事件冒泡到父级（模块外框）
      event.stopPropagation();

      // 2. 只有真正移出当前追踪的最深层级节点时才重置画布
      if (hoveredNodeIdRef.current !== node.id) return;
      hoveredNodeIdRef.current = null;
      resetToDefault();
    },
    [resetToDefault]
  );

  return (
    <div style={{ flex: 1, position: "relative" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeMouseEnter={onNodeMouseEnter}
        onNodeMouseLeave={onNodeMouseLeave}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        attributionPosition="bottom-left"
        // 注意：React Flow v12 没有 elevatedEdgesInFront，等效能力通过
        // 1) elevateEdgesOnSelect 让 selected 边额外提升；
        // 2) react-flow-overrides.css 将 edges 层置于 nodes 层之上；
        // 3) 聚焦边手动设置 zIndex: 1000 + selected: true 共同实现置顶。
        elevateEdgesOnSelect={true}
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
