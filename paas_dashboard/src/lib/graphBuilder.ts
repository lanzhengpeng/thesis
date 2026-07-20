import type { Edge, Node } from "@xyflow/react";
import type {
  CheatSheetApiItem,
  CheatSheetCallGraph,
  CheatSheetComponentItem,
  CheatSheetMethodItem,
  CheatSheetModuleStatus,
} from "../types/cheatSheet";

export type ComponentType = "controller" | "service" | "mapper";

export interface ComponentNodeData {
  [key: string]: unknown;
  label: string;
  name: string;
  componentType: ComponentType;
  module: string;
  componentId: string;
  methods: CheatSheetMethodItem[];
  methodHeights: number[];
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
  nodes: Node<ModuleNodeData | ComponentNodeData>[];
  edges: Edge[];
}

const GATEWAY_WIDTH = 180;

const MODULE_HEADER_HEIGHT = 56;
const MODULE_PADDING = 24;
const MODULE_MIN_WIDTH = 420;
const MODULE_H_GAP = 80;
const MODULE_TOP_MARGIN = 140;

const FAILED_MODULE_WIDTH = 340;
const FAILED_MODULE_HEIGHT = 140;

const MIN_COMPONENT_WIDTH = 360;
const MAX_COMPONENT_WIDTH = 620;
const COMPONENT_H_GAP = 28;
const COMPONENT_V_GAP = 40;

export const COMPONENT_HEADER_HEIGHT = 48;
export const COMPONENT_PADDING = 16;
export const METHOD_ROW_HEIGHT = 52;
export const MAPPER_METHOD_ROW_HEIGHT = 96;

const COMPONENT_ORDER: ComponentType[] = ["controller", "service", "mapper"];

/**
 * 估算单个组件卡片的宽度，保证 HTTP 动词、路径、方法签名和 SQL 都能完整展示。
 */
function estimateComponentWidth(
  type: ComponentType,
  methods: CheatSheetMethodItem[]
): number {
  let maxLine = 0;

  for (const method of methods) {
    const signatureChars = method.name.length + (method.params?.join(", ").length || 0) + 2;

    if (type === "controller") {
      const verbWidth = method.http_method ? 38 : 0;
      const pathWidth = (method.path?.length || 0) * 7.5;
      const signatureWidth = signatureChars * 7.5 + 20;
      maxLine = Math.max(maxLine, verbWidth + pathWidth + signatureWidth + 36);
    } else {
      const signatureWidth = signatureChars * 7.5 + 28;
      let sqlWidth = 0;
      if (type === "mapper" && method.sql) {
        sqlWidth = Math.min(method.sql.length * 6, 420);
      }
      maxLine = Math.max(maxLine, Math.max(signatureWidth, sqlWidth) + 36);
    }
  }

  return Math.min(
    MAX_COMPONENT_WIDTH,
    Math.max(MIN_COMPONENT_WIDTH, maxLine, 240)
  );
}

/**
 * 根据内容估算每一行方法的高度。
 * Mapper 的 SQL 会按卡片宽度折行，留出足够的代码块空间。
 */
function estimateMethodHeights(
  type: ComponentType,
  width: number,
  methods: CheatSheetMethodItem[]
): number[] {
  const contentWidth = Math.max(1, width - COMPONENT_PADDING * 2 - 16);

  return methods.map((method) => {
    const signatureChars = method.name.length + (method.params?.join(", ").length || 0) + 2;

    if (type === "mapper") {
      const base = 48;
      if (!method.sql) return base;
      const charsPerLine = Math.max(1, Math.floor(contentWidth / 6));
      const lines = Math.ceil(method.sql.length / charsPerLine);
      return Math.min(180, base + lines * 16 + 8);
    }

    const charsPerLine = Math.max(1, Math.floor(contentWidth / 7.5));

    if (type === "controller") {
      const pathChars = (method.path?.length || 0) + (method.http_method?.length || 0) + 4;
      const totalChars = signatureChars + pathChars + 4;
      const lines = Math.ceil(totalChars / charsPerLine);
      return Math.min(110, Math.max(METHOD_ROW_HEIGHT, METHOD_ROW_HEIGHT + (lines - 1) * 18));
    }

    const lines = Math.ceil(signatureChars / charsPerLine);
    return Math.min(90, Math.max(METHOD_ROW_HEIGHT, METHOD_ROW_HEIGHT + (lines - 1) * 18));
  });
}

function componentHeight(
  type: ComponentType,
  width: number,
  methods: CheatSheetMethodItem[]
): number {
  const heights = estimateMethodHeights(type, width, methods);
  const rowsHeight = heights.reduce((sum, h) => sum + h, 0);
  return COMPONENT_HEADER_HEIGHT + COMPONENT_PADDING + rowsHeight + COMPONENT_PADDING;
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
 * - 模块宽度根据最宽的一层自动扩展
 * - 每个组件高度根据其方法数量动态计算
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

  // 为标题和右侧 C/S/M 徽章预留足够宽度，避免标题被挤压换行
  const estimatedTitleWidth = moduleName.length * 10 + 190;
  const width = Math.max(
    MODULE_MIN_WIDTH,
    maxRowWidth + MODULE_PADDING * 2,
    estimatedTitleWidth
  );

  // 计算每一层的高度
  const rowHeights = rowInfos.map((infos) =>
    infos.length > 0
      ? Math.max(
          ...infos.map((info) => componentHeight(info.type, info.width, info.methods))
        )
      : METHOD_ROW_HEIGHT
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
  const okModules = moduleStatus.loaded;
  const failedModules = moduleStatus.failed;

  const nodes: Node<ModuleNodeData | ComponentNodeData>[] = [];
  const edges: Edge[] = [];
  const edgeIds = new Set<string>();

  // 组件元数据索引：componentId -> CheatSheetComponentItem
  const componentMeta: Record<string, CheatSheetComponentItem> = {};
  // 方法索引：ClassName.methodName -> componentId / methodName / module
  const methodIndex: Record<
    string,
    { componentId: string; methodName: string; module: string }
  > = {};

  for (const comp of components) {
    const componentId = `${comp.module}::${comp.type}::${comp.name}`;
    componentMeta[componentId] = comp;
    for (const method of comp.methods) {
      methodIndex[`${comp.name}.${method.name}`] = {
        componentId,
        methodName: method.name,
        module: comp.module,
      };
    }
  }

  // 1. 创建网关节点
  nodes.push({
    id: "gateway",
    type: "gateway",
    position: { x: 0, y: 0 },
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
      style: { width, height },
      data: {
        label: moduleName,
        status: "ok",
        components: moduleComponents,
        apiList: moduleApis,
        counts: countComponents(moduleComponents),
      },
    });

    // 网关指向模块
    const gatewayEdgeId = `gateway->${moduleName}`;
    if (!edgeIds.has(gatewayEdgeId)) {
      edgeIds.add(gatewayEdgeId);
      edges.push({
        id: gatewayEdgeId,
        source: "gateway",
        target: moduleName,
        type: "smoothstep",
        animated: true,
      });
    }

    // 组件子节点
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
        style: { width, height },
        data: {
          label: info.name,
          name: info.name,
          componentType: info.type,
          module: moduleName,
          componentId: info.id,
          methods: meta?.methods || [],
          methodHeights: estimateMethodHeights(info.type, width, meta?.methods || []),
        },
      });
    }

    // 方法级调用边：根据 methods[].calls 建立从方法行到方法行的精准连线
    for (const info of componentInfos) {
      for (const method of info.methods) {
        for (const call of method.calls) {
          const target = methodIndex[call];
          if (!target) continue;

          const edgeId = `${info.id}::${method.name}->${target.componentId}::${target.methodName}`;
          if (edgeIds.has(edgeId)) continue;
          edgeIds.add(edgeId);

          const isCrossModule = target.module !== moduleName;

          edges.push({
            id: edgeId,
            source: info.id,
            target: target.componentId,
            type: "smoothstep",
            animated: isCrossModule,
            sourceHandle: `method-${method.name}-right`,
            targetHandle: `method-${target.methodName}-left`,
            style: isCrossModule
              ? { stroke: "#f59e0b", strokeWidth: 2, strokeDasharray: "5,5" }
              : { stroke: "#94a3b8", strokeWidth: 1.5 },
          });
        }
      }
    }
  }

  // 4. 创建失败模块节点
  for (const failed of failedModules) {
    const failedId = `failed-${failed.module}`;
    const failedWidth = Math.max(
      FAILED_MODULE_WIDTH,
      failed.module.length * 10 + 190
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
      style: { width: failedWidth, height: FAILED_MODULE_HEIGHT },
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
