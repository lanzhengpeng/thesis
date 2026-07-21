import { Position } from "@xyflow/react";
import type { BuiltInEdge, Edge, Node } from "@xyflow/react";
import type {
  CheatSheetApiItem,
  CheatSheetCallGraph,
  CheatSheetComponentItem,
  CheatSheetMethodItem,
  CheatSheetModuleStatus,
} from "../../../types/cheatSheet";

export type ComponentType = "controller" | "service" | "mapper";

export interface ComponentNodeData {
  [key: string]: unknown;
  label: string;
  name: string;
  componentType: ComponentType;
  module: string;
  componentId: string;
}

export interface MethodNodeData {
  [key: string]: unknown;
  label: string;
  name: string;
  componentType: ComponentType;
  componentId: string;
  method: CheatSheetMethodItem;
  height: number;
}

export interface ModuleNodeData {
  [key: string]: unknown;
  label: string;
  status: "ok" | "failed";
  error?: string;
  components: Record<string, string[]>;
  apiList: CheatSheetApiItem[];
  counts: { controllers: number; services: number; mappers: number };
}

export interface GraphResult {
  nodes: Node<ModuleNodeData | ComponentNodeData | MethodNodeData>[];
  edges: Edge[];
}

const GATEWAY_WIDTH = 200;

const MODULE_HEADER_HEIGHT = 56;
const MODULE_PADDING = 40;
const MODULE_MIN_WIDTH = 560;
const MODULE_H_GAP = 100;
const MODULE_TOP_MARGIN = 160;

const FAILED_MODULE_WIDTH = 360;
const FAILED_MODULE_HEIGHT = 150;

const MIN_COMPONENT_WIDTH = 520;
const MAX_COMPONENT_WIDTH = 1600;
const COMPONENT_H_GAP = 32;
const COMPONENT_V_GAP = 48;

export const COMPONENT_HEADER_HEIGHT = 48;
export const COMPONENT_PADDING = 16;
export const METHOD_BLOCK_GAP = 16;
export const METHOD_BLOCK_PADDING = 12;

const METHOD_NODE_WIDTH = 220;
const METHOD_NODE_GAP = 16;
const COMPONENT_DRAG_MARGIN = 60;

const COMPONENT_ORDER: ComponentType[] = ["controller", "service", "mapper"];

interface HandleDef {
  id: string;
  type: "source" | "target";
  position: Position;
  x: number;
  y: number;
}

function tbHandles(width: number, height: number): HandleDef[] {
  const cx = width / 2 - 4;
  return [
    { id: "top", type: "target", position: Position.Top, x: cx, y: -4 },
    { id: "bottom", type: "source", position: Position.Bottom, x: cx, y: height - 4 },
  ];
}

function moduleHandles(width: number, height: number): HandleDef[] {
  const cx = width / 2 - 4;
  const cy = height / 2 - 4;
  return [
    { id: "top", type: "target", position: Position.Top, x: cx, y: -4 },
    { id: "bottom", type: "source", position: Position.Bottom, x: cx, y: height - 4 },
    { id: "left", type: "target", position: Position.Left, x: -4, y: cy },
    { id: "right", type: "source", position: Position.Right, x: width - 4, y: cy },
  ];
}

function methodHandles(width: number, height: number): HandleDef[] {
  const cx = width / 2 - 4;
  const cy = height / 2 - 4;
  return [
    { id: "top", type: "target", position: Position.Top, x: cx, y: -4 },
    { id: "bottom", type: "source", position: Position.Bottom, x: cx, y: height - 4 },
    { id: "left", type: "target", position: Position.Left, x: -4, y: cy },
    { id: "right", type: "source", position: Position.Right, x: width - 4, y: cy },
  ];
}

export const INNER_EDGE_COLOR = "#94a3b8"; // 模块内方法连线：低调灰色虚线
export const CROSS_MODULE_EDGE_COLOR = "#f97316"; // 跨模块级连线：醒目亮橙色
export const CROSS_METHOD_EDGE_COLOR = "#f97316"; // 跨模块方法连线：醒目亮橙色

export const DEFAULT_EDGE_ZINDEX = 5;
export const FOCUSED_EDGE_ZINDEX = 1000;
export const DIMMED_EDGE_ZINDEX = 0;
export const DIMMED_NODE_ZINDEX = 0;

/**
 * 估算组件容器宽度。
 * 方法节点单行水平展开，宽度 = 内边距 + 所有方法节点宽度 + 间距。
 */
function estimateComponentWidth(
  _type: ComponentType,
  methods: CheatSheetMethodItem[]
): number {
  if (methods.length === 0) {
    return MIN_COMPONENT_WIDTH;
  }
  const requiredWidth =
    COMPONENT_PADDING * 2 +
    methods.length * METHOD_NODE_WIDTH +
    Math.max(0, methods.length - 1) * METHOD_NODE_GAP;
  return Math.min(MAX_COMPONENT_WIDTH, Math.max(MIN_COMPONENT_WIDTH, requiredWidth));
}

/**
 * 估算每个方法块的高度。
 * 方法块为独立卡片，包含签名、参数标签、HTTP 路径（Controller）和嵌套 SQL（Mapper）。
 */
export function estimateMethodHeights(
  _type: ComponentType,
  _methodNodeWidth: number,
  methods: CheatSheetMethodItem[]
): number[] {
  // 方法卡片仅展示功能名，高度保持统一且紧凑
  return methods.map(() => Math.max(48, METHOD_BLOCK_PADDING * 2 + 22));
}

function componentHeight(
  type: ComponentType,
  _width: number,
  methods: CheatSheetMethodItem[]
): number {
  const heights = estimateMethodHeights(type, METHOD_NODE_WIDTH, methods);
  const maxMethodHeight = heights.length > 0 ? Math.max(...heights) : 0;
  return (
    COMPONENT_HEADER_HEIGHT +
    COMPONENT_PADDING +
    maxMethodHeight +
    COMPONENT_PADDING +
    COMPONENT_DRAG_MARGIN
  );
}

/**
 * 在组件容器内对方法节点做单行水平展开布局。
 * 所有方法节点在同一水平行（Y 轴一致），X 轴按固定宽度依次排列，不换行。
 */
function layoutComponentMethods(
  _componentWidth: number,
  methodHeights: number[]
): {
  positions: { x: number; y: number }[];
  totalHeight: number;
  maxHeight: number;
} {
  const positions: { x: number; y: number }[] = [];
  for (let i = 0; i < methodHeights.length; i++) {
    positions.push({
      x: COMPONENT_PADDING + i * (METHOD_NODE_WIDTH + METHOD_NODE_GAP),
      y: 0,
    });
  }
  const maxHeight = methodHeights.length > 0 ? Math.max(...methodHeights) : 0;
  return { positions, totalHeight: maxHeight, maxHeight };
}

/**
 * 从调用图条目中解析出类名和依赖类名列表。
 * 例如：
 *   "UserMapper(None)" -> { name: "UserMapper", deps: [] }
 *   "UserService(UserMapper)" -> { name: "UserService", deps: ["UserMapper"] }
 *   "OrderService(OrderMapper, UserService)" -> { name: "OrderService", deps: ["OrderMapper", "UserService"] }
 */
export function parseComponentEntry(entry: string): { name: string; deps: string[] } {
  const match = entry.match(/^(\w+)\((.*)\)$/);
  if (!match) {
    return { name: entry, deps: [] };
  }

  const name = match[1];
  const depsContent = match[2].trim();

  if (!depsContent || depsContent === "None") {
    return { name, deps: [] };
  }

  const deps = depsContent.split(",").map((dep) => dep.trim());
  return { name, deps };
}

function componentNodeId(module: string, type: ComponentType, name: string): string {
  return `${module}::${type}::${name}`;
}

function methodNodeId(componentId: string, methodName: string): string {
  return `${componentId}::${methodName}`;
}

function countComponents(components: Record<string, string[]>): {
  controllers: number;
  services: number;
  mappers: number;
} {
  return {
    controllers: components.controller?.length || 0,
    services: components.service?.length || 0,
    mappers: components.mapper?.length || 0,
  };
}

interface ComponentInfo {
  id: string;
  name: string;
  type: ComponentType;
  deps: string[];
  methods: CheatSheetMethodItem[];
  width: number;
}

/**
 * 计算模块分组尺寸，并返回内部组件的相对坐标。
 *
 * 布局策略：
 * - 按 CSM 三层垂直堆叠：Controller（顶）、Service（中）、Mapper（底）
 * - 同一层内的组件水平并排，整体在模块内水平居中
 * - 模块宽度根据最宽的一层自动扩展，留出充足内边距
 * - 每个组件高度根据其方法块数量动态计算
 */
function layoutModuleComponents(
  moduleName: string,
  components: Record<string, string[]>,
  componentMeta: Record<string, CheatSheetComponentItem>
): {
  width: number;
  height: number;
  componentInfos: ComponentInfo[];
  positions: Record<string, { x: number; y: number }>;
} {
  const controllers: ComponentInfo[] = [];
  const services: ComponentInfo[] = [];
  const mappers: ComponentInfo[] = [];

  for (const entry of components.controller || []) {
    const { name, deps } = parseComponentEntry(entry);
    const id = componentNodeId(moduleName, "controller", name);
    const meta = componentMeta[id];
    const methods = meta?.methods || [];
    controllers.push({
      id,
      name,
      type: "controller",
      deps,
      methods,
      width: estimateComponentWidth("controller", methods),
    });
  }
  for (const entry of components.service || []) {
    const { name, deps } = parseComponentEntry(entry);
    const id = componentNodeId(moduleName, "service", name);
    const meta = componentMeta[id];
    const methods = meta?.methods || [];
    services.push({
      id,
      name,
      type: "service",
      deps,
      methods,
      width: estimateComponentWidth("service", methods),
    });
  }
  for (const entry of components.mapper || []) {
    const { name, deps } = parseComponentEntry(entry);
    const id = componentNodeId(moduleName, "mapper", name);
    const meta = componentMeta[id];
    const methods = meta?.methods || [];
    mappers.push({
      id,
      name,
      type: "mapper",
      deps,
      methods,
      width: estimateComponentWidth("mapper", methods),
    });
  }

  const componentInfos = [...controllers, ...services, ...mappers];
  const rowInfos = [controllers, services, mappers];

  const rowWidths = rowInfos.map((infos) =>
    infos.reduce(
      (sum, info, i) => sum + info.width + (i > 0 ? COMPONENT_H_GAP : 0),
      0
    )
  );
  const maxRowWidth = Math.max(0, ...rowWidths);

  const estimatedTitleWidth = moduleName.length * 11 + 200;
  const width = Math.max(
    MODULE_MIN_WIDTH,
    maxRowWidth + MODULE_PADDING * 2,
    estimatedTitleWidth
  );

  const rowHeights = rowInfos.map((infos) =>
    infos.length > 0
      ? Math.max(
          ...infos.map((info) => componentHeight(info.type, info.width, info.methods))
        )
      : 64
  );

  const contentHeight =
    rowHeights.reduce((sum, h) => sum + h, 0) +
    Math.max(0, rowHeights.length - 1) * COMPONENT_V_GAP;
  const height = MODULE_HEADER_HEIGHT + contentHeight + MODULE_PADDING * 2;

  const positions: Record<string, { x: number; y: number }> = {};

  function placeRow(infos: ComponentInfo[], rowIndex: number) {
    const rowWidth = rowWidths[rowIndex];
    const startX = (width - rowWidth) / 2;
    let startY = MODULE_HEADER_HEIGHT + MODULE_PADDING;
    for (let i = 0; i < rowIndex; i++) {
      startY += rowHeights[i] + COMPONENT_V_GAP;
    }

    let x = startX;
    for (let i = 0; i < infos.length; i++) {
      const info = infos[i];
      positions[info.id] = { x, y: startY };
      x += info.width + COMPONENT_H_GAP;
    }
  }

  placeRow(controllers, 0);
  placeRow(services, 1);
  placeRow(mappers, 2);

  return { width, height, componentInfos, positions };
}

export function buildGraph(
  callGraph: CheatSheetCallGraph,
  moduleStatus: CheatSheetModuleStatus,
  apiMap: CheatSheetApiItem[],
  components: CheatSheetComponentItem[]
): GraphResult {
  const okModules = [...new Set(moduleStatus.loaded)];
  const failedModules = moduleStatus.failed;

  const nodes: Node<ModuleNodeData | ComponentNodeData | MethodNodeData>[] = [];
  const edges: BuiltInEdge[] = [];
  const edgeIds = new Set<string>();

  const componentMeta: Record<string, CheatSheetComponentItem> = {};
  const methodIndex: Record<
    string,
    { componentId: string; methodNodeId: string; methodName: string; module: string; type: ComponentType }
  > = {};

  for (const comp of components) {
    const componentId = `${comp.module}::${comp.type}::${comp.name}`;
    if (componentMeta[componentId]) continue;
    componentMeta[componentId] = comp;
    for (const method of comp.methods) {
      methodIndex[`${comp.name}.${method.name}`] = {
        componentId,
        methodNodeId: methodNodeId(componentId, method.name),
        methodName: method.name,
        module: comp.module,
        type: comp.type,
      };
    }
  }

  // 1. 创建网关节点
  nodes.push({
    id: "gateway",
    type: "gateway",
    position: { x: 0, y: 0 },
    zIndex: 10,
    style: { width: GATEWAY_WIDTH, height: 80 },
    measured: { width: GATEWAY_WIDTH, height: 80 },
    handles: tbHandles(GATEWAY_WIDTH, 80),
    data: {
      label: "网关 / 鉴权",
      status: "ok",
      components: {},
      apiList: [],
      counts: { controllers: 0, services: 0, mappers: 0 },
    },
  });

  // 2. 建立类名 -> 模块/类型索引，用于解析依赖
  const classIndex: Record<string, { module: string; type: ComponentType }> = {};
  for (const [moduleName, moduleComponents] of Object.entries(callGraph)) {
    for (const type of COMPONENT_ORDER) {
      for (const entry of moduleComponents[type] || []) {
        const { name } = parseComponentEntry(entry);
        classIndex[name] = { module: moduleName, type };
      }
    }
  }

  // 3. 创建模块分组节点及其内部组件子节点
  const moduleLayouts: Record<
    string,
    { width: number; height: number; positions: Record<string, { x: number; y: number }> }
  > = {};

  for (const moduleName of okModules) {
    const moduleComponents = callGraph[moduleName] || {};
    const moduleApis = apiMap.filter((api) => api.module === moduleName);

    const { width, height, componentInfos, positions } = layoutModuleComponents(
      moduleName,
      moduleComponents,
      componentMeta
    );
    moduleLayouts[moduleName] = { width, height, positions };

    nodes.push({
      id: moduleName,
      type: "module",
      position: { x: 0, y: 0 },
      zIndex: 0,
      style: { width, height },
      measured: { width, height },
      handles: moduleHandles(width, height),
      data: {
        label: moduleName,
        status: "ok",
        components: moduleComponents,
        apiList: moduleApis,
        counts: countComponents(moduleComponents),
      },
    });

    const gatewayEdgeId = `gateway->${moduleName}`;
    if (!edgeIds.has(gatewayEdgeId)) {
      edgeIds.add(gatewayEdgeId);
      edges.push({
        id: gatewayEdgeId,
        source: "gateway",
        target: moduleName,
        type: "smoothstep",
        animated: true,
        zIndex: 5,
        sourceHandle: "bottom",
        targetHandle: "top",
        style: { stroke: "#94a3b8", strokeWidth: 2 },
        pathOptions: { borderRadius: 16 },
      });
    }

    for (const info of componentInfos) {
      const pos = positions[info.id];
      const meta = componentMeta[info.id];
      const width = info.width;
      const height = componentHeight(info.type, width, info.methods);

      nodes.push({
        id: info.id,
        type: "component",
        parentId: moduleName,
        position: pos,
        zIndex: 10,
        style: { width, height },
        measured: { width, height },
        data: {
          label: info.name,
          name: info.name,
          componentType: info.type,
          module: moduleName,
          componentId: info.id,
        },
      });

      // 方法子节点：横向流式排列在组件容器内，可拖拽但限制在父容器边界
      const methodHeights = estimateMethodHeights(info.type, METHOD_NODE_WIDTH, meta?.methods || []);
      const methodLayout = layoutComponentMethods(width, methodHeights);

      for (let i = 0; i < (meta?.methods || []).length; i++) {
        const method = meta.methods[i];
        const methodPos = methodLayout.positions[i];
        const mId = methodNodeId(info.id, method.name);
        nodes.push({
          id: mId,
          type: "method",
          parentId: info.id,
          position: { x: methodPos.x, y: methodPos.y + COMPONENT_HEADER_HEIGHT },
          zIndex: 11,
          draggable: true,
          extent: "parent",
          style: { width: METHOD_NODE_WIDTH, height: methodHeights[i] },
          measured: { width: METHOD_NODE_WIDTH, height: methodHeights[i] },
          handles: methodHandles(METHOD_NODE_WIDTH, methodHeights[i]),
          data: {
            label: method.name,
            name: method.name,
            componentType: info.type,
            componentId: info.id,
            method,
            height: methodHeights[i],
          },
        });
      }
    }

    // 方法级调用边：直接连接方法子节点
    const crossModulePairs = new Set<string>();

    for (const info of componentInfos) {
      for (const method of info.methods) {
        for (const call of method.calls) {
          const target = methodIndex[call];
          if (!target) continue;

          const sourceId = methodNodeId(info.id, method.name);
          const targetId = target.methodNodeId;
          const edgeId = `${sourceId}->${targetId}`;
          if (edgeIds.has(edgeId)) continue;
          edgeIds.add(edgeId);

          const isCrossModule = target.module !== moduleName;

          if (isCrossModule) {
            const defaultStyle = {
              stroke: CROSS_METHOD_EDGE_COLOR,
              strokeWidth: 2,
            };
            edges.push({
              id: edgeId,
              source: sourceId,
              target: targetId,
              type: "smoothstep",
              hidden: true,
              animated: false,
              zIndex: DEFAULT_EDGE_ZINDEX,
              sourceHandle: "right",
              targetHandle: "left",
              style: defaultStyle,
              pathOptions: { borderRadius: 16 },
              data: {
                edgeType: "crossMethod",
                defaultStyle,
              },
            });
            crossModulePairs.add(`${moduleName}->${target.module}`);
          } else {
            const defaultStyle = {
              stroke: INNER_EDGE_COLOR,
              strokeWidth: 2,
              strokeDasharray: "5,5",
              opacity: 0.9,
            };
            edges.push({
              id: edgeId,
              source: sourceId,
              target: targetId,
              type: "smoothstep",
              hidden: true,
              animated: false,
              zIndex: DEFAULT_EDGE_ZINDEX,
              sourceHandle: "bottom",
              targetHandle: "top",
              style: defaultStyle,
              pathOptions: { borderRadius: 16 },
              data: {
                edgeType: "inner",
                defaultStyle,
              },
            });
          }
        }
      }
    }

    // 模块级跨模块连线：由方法级跨模块调用聚合而成，大框连大框
    for (const pairKey of crossModulePairs) {
      const [sourceModule, targetModule] = pairKey.split("->");
      const edgeId = `module-${sourceModule}->${targetModule}`;
      if (edgeIds.has(edgeId)) continue;
      edgeIds.add(edgeId);

      const defaultStyle = {
        stroke: CROSS_MODULE_EDGE_COLOR,
        strokeWidth: 2.5,
      };
      edges.push({
        id: edgeId,
        source: sourceModule,
        target: targetModule,
        type: "smoothstep",
        hidden: true,
        animated: false,
        zIndex: DEFAULT_EDGE_ZINDEX,
        sourceHandle: "right",
        targetHandle: "left",
        style: defaultStyle,
        pathOptions: { borderRadius: 16 },
        data: {
          edgeType: "crossModule",
          defaultStyle,
        },
      });
    }
  }

  // 4. 创建失败模块节点
  for (const failed of failedModules) {
    const failedId = `failed-${failed.module}`;
    const failedWidth = Math.max(
      FAILED_MODULE_WIDTH,
      failed.module.length * 11 + 200
    );
    moduleLayouts[failedId] = {
      width: failedWidth,
      height: FAILED_MODULE_HEIGHT,
      positions: {},
    };

    nodes.push({
      id: failedId,
      type: "failedModule",
      position: { x: 0, y: 0 },
      zIndex: 0,
      style: { width: failedWidth, height: FAILED_MODULE_HEIGHT },
      measured: { width: failedWidth, height: FAILED_MODULE_HEIGHT },
      handles: tbHandles(failedWidth, FAILED_MODULE_HEIGHT),
      data: {
        label: failed.module,
        status: "failed",
        error: failed.error,
        components: {},
        apiList: [],
        counts: { controllers: 0, services: 0, mappers: 0 },
      },
    });

    const gatewayEdgeId = `gateway->${failedId}`;
    if (!edgeIds.has(gatewayEdgeId)) {
      edgeIds.add(gatewayEdgeId);
      edges.push({
        id: gatewayEdgeId,
        source: "gateway",
        target: failedId,
        type: "smoothstep",
        animated: true,
        zIndex: 5,
        sourceHandle: "bottom",
        targetHandle: "top",
        style: { stroke: "#ef4444", strokeWidth: 2, strokeDasharray: "5,5" },
        pathOptions: { borderRadius: 16 },
      });
    }
  }

  // 5. 模块级布局：所有模块横向并排铺开，网关居中置顶
  const allModuleNodes = nodes.filter(
    (n) => n.type === "module" || n.type === "failedModule"
  );

  let currentX = 0;
  let totalModulesWidth = 0;
  for (const modNode of allModuleNodes) {
    const layout = moduleLayouts[modNode.id];
    modNode.position = { x: currentX, y: MODULE_TOP_MARGIN };
    currentX += layout.width + MODULE_H_GAP;
    totalModulesWidth += layout.width + MODULE_H_GAP;
  }
  totalModulesWidth -= allModuleNodes.length > 0 ? MODULE_H_GAP : 0;

  const gatewayNode = nodes.find((n) => n.id === "gateway");
  if (gatewayNode) {
    gatewayNode.position = {
      x: totalModulesWidth / 2 - GATEWAY_WIDTH / 2,
      y: 0,
    };
  }

  return { nodes, edges };
}
