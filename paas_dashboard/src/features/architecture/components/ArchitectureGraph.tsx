import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type MouseEvent,
} from "react";
import {
  Background,
  Controls,
  MiniMap,
  Panel,
  ReactFlow,
  useEdgesState,
  useNodesState,
  useViewport,
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
  onSelectMethod?: (method: { componentId: string; methodName: string } | null) => void;
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

type InteractMode = "mouse" | "trackpad";

/**
 * 右下角交互模式切换面板，显示当前缩放比例并支持鼠标/触摸板模式切换。
 */
function InteractionModePanel({
  mode,
  onChange,
}: {
  mode: InteractMode;
  onChange: (mode: InteractMode) => void;
}) {
  const { zoom } = useViewport();
  const [open, setOpen] = useState(false);

  const modes: { key: InteractMode; label: string; desc: string; icon: string }[] = [
    { key: "mouse", label: "鼠标模式", desc: "左键拖拽，滚轮缩放", icon: "🖱️" },
    { key: "trackpad", label: "触摸板模式", desc: "双指平移，捏合缩放", icon: "👆" },
  ];

  const current = modes.find((m) => m.key === mode) ?? modes[0];

  return (
    <Panel position="bottom-right" style={{ margin: 0 }}>
      <div style={{ position: "relative" }}>
        <button
          onClick={() => setOpen((v) => !v)}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "8px 12px",
            borderRadius: 8,
            border: "1px solid #e2e8f0",
            background: "#ffffff",
            boxShadow: "0 2px 8px rgba(0, 0, 0, 0.08)",
            cursor: "pointer",
            fontSize: 13,
            color: "#0f172a",
          }}
        >
          <span>{current.icon}</span>
          <span>{current.label}</span>
          <span style={{ color: "#64748b", marginLeft: 4 }}>
            {Math.round(zoom * 100)}%
          </span>
          <span style={{ color: "#94a3b8", fontSize: 10 }}>▾</span>
        </button>

        {open && (
          <>
            <div
              style={{
                position: "fixed",
                inset: 0,
                zIndex: 1,
              }}
              onClick={() => setOpen(false)}
            />
            <div
              style={{
                position: "absolute",
                bottom: "calc(100% + 8px)",
                right: 0,
                zIndex: 2,
                minWidth: 180,
                padding: 6,
                borderRadius: 10,
                border: "1px solid #e2e8f0",
                background: "#ffffff",
                boxShadow: "0 4px 16px rgba(0, 0, 0, 0.12)",
              }}
            >
              {modes.map((m) => (
                <button
                  key={m.key}
                  onClick={() => {
                    onChange(m.key);
                    setOpen(false);
                  }}
                  style={{
                    width: "100%",
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "8px 10px",
                    borderRadius: 6,
                    border: "none",
                    background: mode === m.key ? "#eff6ff" : "transparent",
                    color: mode === m.key ? "#1d4ed8" : "#0f172a",
                    cursor: "pointer",
                    textAlign: "left",
                  }}
                >
                  <span style={{ fontSize: 16 }}>{m.icon}</span>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>{m.label}</div>
                    <div style={{ fontSize: 11, color: "#64748b" }}>{m.desc}</div>
                  </div>
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </Panel>
  );
}

export function ArchitectureGraph({
  data,
  onSelectModule,
  onSelectComponent,
  onSelectMethod,
}: ArchitectureGraphProps) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => buildGraph(data.call_graph, data.modules, data.api_map, data.components),
    [data]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes as Node[]);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges as Edge[]);
  const [interactMode, setInteractMode] = useState<InteractMode>("mouse");

  // 当前真实处于悬浮状态的最深层级节点 ID（方法级优先级由事件顺序 + stopPropagation 保证）
  const hoveredNodeIdRef = useRef<string | null>(null);
  const lockedNodeIdRef = useRef<string | null>(null);
  const selectedModuleIdRef = useRef<string | null>(null);
  const selectedComponentIdRef = useRef<string | null>(null);
  const selectedMethodRef = useRef<{ componentId: string; methodName: string } | null>(null);

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
    selectedMethodRef.current = null;
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  // 状态 1：默认基准状态（Mouse Leave 恢复状态）
  const resetToDefault = useCallback(() => {
    setNodes((prev) =>
      prev.map((node) => ({
        ...node,
        style: { ...node.style, opacity: 1 },
        zIndex: defaultNodeZIndexMap.get(node.id) ?? node.zIndex,
        data:
          node.type === "method"
            ? { ...(node.data as MethodNodeData), locked: false }
            : node.data,
      }))
    );

    setEdges((prev) =>
      prev.map((edge) => {
        const edgeType = edge.data?.edgeType;
        const isGatewayEdge = !edgeType;

        if (edgeType === "crossMethod" || edgeType === "crossModule") {
          return {
            ...edge,
            hidden: true,
            animated: false,
            selected: false,
            zIndex: DEFAULT_EDGE_ZINDEX,
            style: edge.data?.defaultStyle || edge.style,
          };
        }

        if (edgeType === "inner") {
          return {
            ...edge,
            hidden: false,
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
    (methodId: string, options?: { locked?: boolean }) => {
      const locked = options?.locked ?? false;
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
                data: { ...(node.data as MethodNodeData), locked: node.id === methodId && locked },
                style: { ...node.style, opacity: 1 },
                zIndex: defaultNodeZIndexMap.get(node.id) ?? node.zIndex,
              };
            }
            return {
              ...node,
              data: { ...(node.data as MethodNodeData), locked: false },
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
        const next = { componentId: methodData.componentId, methodName: methodData.name };
        if (
          selectedMethodRef.current?.componentId !== next.componentId ||
          selectedMethodRef.current?.methodName !== next.methodName
        ) {
          selectedMethodRef.current = next;
          selectedComponentIdRef.current = null;
          selectedModuleIdRef.current = null;
          onSelectMethod?.(next);
        }
      } else if (node.type === "component" && node.id) {
        if (selectedComponentIdRef.current !== node.id) {
          selectedComponentIdRef.current = node.id;
          selectedMethodRef.current = null;
          selectedModuleIdRef.current = null;
          onSelectComponent(node.id);
        }
      } else if ((node.type === "module" || node.type === "failedModule") && node.data) {
        if (selectedModuleIdRef.current !== node.id) {
          selectedModuleIdRef.current = node.id;
          selectedComponentIdRef.current = null;
          selectedMethodRef.current = null;
          onSelectModule(node.data as ModuleNodeData);
        }
      }
    },
    [onSelectComponent, onSelectMethod, onSelectModule]
  );

  const onNodeMouseEnter = useCallback(
    (event: MouseEvent, node: Node) => {
      // 1. 阻止事件冒泡到父级（模块外框）
      event.stopPropagation();

      // 若已有方法被锁定，忽略其他悬浮事件，保持当前锁定态
      if (lockedNodeIdRef.current) return;

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

      // 若已有方法被锁定，保持锁定态，不随鼠标移出重置
      if (lockedNodeIdRef.current) return;

      // 2. 只有真正移出当前追踪的最深层级节点时才重置画布
      if (hoveredNodeIdRef.current !== node.id) return;
      hoveredNodeIdRef.current = null;
      resetToDefault();
    },
    [resetToDefault]
  );

  const onNodeClick = useCallback(
    (event: MouseEvent, node: Node) => {
      event.stopPropagation();

      if (node.type === "method") {
        if (lockedNodeIdRef.current === node.id) {
          // 再次点击已锁定方法：解锁并恢复默认视图
          lockedNodeIdRef.current = null;
          hoveredNodeIdRef.current = null;
          resetToDefault();
          selectedMethodRef.current = null;
          onSelectMethod?.(null);
          return;
        }

        // 锁定新方法：保持方法级聚焦并加粗边框
        lockedNodeIdRef.current = node.id;
        hoveredNodeIdRef.current = node.id;
        enterMethodFocus(node.id, { locked: true });
        updatePanelSelection(node);
        return;
      }

      // 点击非方法节点：若当前有锁定方法，先解锁
      if (lockedNodeIdRef.current) {
        lockedNodeIdRef.current = null;
        hoveredNodeIdRef.current = null;
        resetToDefault();
        selectedMethodRef.current = null;
        onSelectMethod?.(null);
      }

      // 同步更新右侧面板为当前点击的模块/组件
      updatePanelSelection(node);
    },
    [enterMethodFocus, resetToDefault, updatePanelSelection, onSelectMethod]
  );

  const onPaneClick = useCallback(() => {
    if (!lockedNodeIdRef.current) return;
    lockedNodeIdRef.current = null;
    hoveredNodeIdRef.current = null;
    resetToDefault();
    selectedMethodRef.current = null;
    onSelectMethod?.(null);
  }, [resetToDefault, onSelectMethod]);

  const isMouseMode = interactMode === "mouse";

  return (
    <div style={{ flex: 1, position: "relative" }}>
      <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeMouseEnter={onNodeMouseEnter}
          onNodeMouseLeave={onNodeMouseLeave}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          // 初始加载与节点全量更新时自动 fitView；覆盖默认 minZoom 限制，确保大架构图也能完整显示
          fitView
          fitViewOptions={{ padding: 0.2, minZoom: 0.1, maxZoom: 1 }}
          minZoom={0.1}
          maxZoom={2}
          attributionPosition="bottom-left"
          // 注意：React Flow v12 没有 elevatedEdgesInFront，等效能力通过
          // 1) elevateEdgesOnSelect 让 selected 边额外提升；
          // 2) react-flow-overrides.css 将 edges 层置于 nodes 层之上；
          // 3) 聚焦边手动设置 zIndex: 1000 + selected: true 共同实现置顶。
          elevateEdgesOnSelect={true}
          // 交互模式动态映射
          panOnDrag={isMouseMode}
          zoomOnScroll={isMouseMode}
          panOnScroll={!isMouseMode}
          selectionOnDrag={false}
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
          <InteractionModePanel mode={interactMode} onChange={setInteractMode} />
        </ReactFlow>
      </div>
  );
}
