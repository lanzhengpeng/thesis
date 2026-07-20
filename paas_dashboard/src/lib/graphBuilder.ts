import dagre from "dagre";
import type { Edge, Node } from "@xyflow/react";
import type {
  CheatSheetApiItem,
  CheatSheetCallGraph,
  CheatSheetModuleStatus,
} from "../types/cheatSheet";

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
  nodes: Node<ModuleNodeData>[];
  edges: Edge[];
}

const NODE_WIDTH = 260;
const NODE_HEIGHT = 140;
const GATEWAY_WIDTH = 180;
const GATEWAY_HEIGHT = 80;

/**
 * 从调用图条目中解析出类名和依赖类名列表。
 * 例如：
 *   "Mapper(None)" -> { name: "Mapper", deps: [] }
 *   "Service(UserMapper)" -> { name: "UserService", deps: ["UserMapper"] }
 *   "Service(OrderMapper, UserService)" -> { name: "OrderService", deps: ["OrderMapper", "UserService"] }
 */
function parseComponentEntry(entry: string): { name: string; deps: string[] } {
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

/**
 * 构建“类名 -> 模块名”反向索引。
 */
function buildClassToModuleIndex(callGraph: CheatSheetCallGraph): Record<string, string> {
  const index: Record<string, string> = {};

  for (const [moduleName, components] of Object.entries(callGraph)) {
    for (const entries of Object.values(components)) {
      for (const entry of entries) {
        const { name } = parseComponentEntry(entry);
        index[name] = moduleName;
      }
    }
  }

  return index;
}

/**
 * 计算模块内部的组件数量。
 */
function countComponents(components: Record<string, string[]>): {
  controllers: number;
  services: number;
  mappers: number;
} {
  return {
    mappers: components.mapper?.length || 0,
    services: components.service?.length || 0,
    controllers: components.controller?.length || 0,
  };
}

export function buildGraph(
  callGraph: CheatSheetCallGraph,
  moduleStatus: CheatSheetModuleStatus,
  apiMap: CheatSheetApiItem[]
): GraphResult {
  const classToModule = buildClassToModuleIndex(callGraph);
  const okModules = moduleStatus.loaded;
  const failedModules = moduleStatus.failed;

  const nodes: Node<ModuleNodeData>[] = [];
  const edges: Edge[] = [];

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

  // 2. 创建成功模块节点
  for (const moduleName of okModules) {
    const components = callGraph[moduleName] || {};
    const moduleApis = apiMap.filter((api) => api.module === moduleName);

    nodes.push({
      id: moduleName,
      type: "module",
      position: { x: 0, y: 0 },
      data: {
        label: moduleName,
        status: "ok",
        components,
        apiList: moduleApis,
        counts: countComponents(components),
      },
    });

    // 网关指向每个模块
    edges.push({
      id: `gateway->${moduleName}`,
      source: "gateway",
      target: moduleName,
      type: "smoothstep",
      animated: true,
    });

    // 跨模块依赖边
    for (const entries of Object.values(components)) {
      for (const entry of entries) {
        const { deps } = parseComponentEntry(entry);
        for (const depClassName of deps) {
          const depModule = classToModule[depClassName];
          if (depModule && depModule !== moduleName) {
            const edgeId = `${moduleName}->${depModule}`;
            // 避免重复边
            if (!edges.some((e) => e.id === edgeId)) {
              edges.push({
                id: edgeId,
                source: moduleName,
                target: depModule,
                type: "smoothstep",
                animated: false,
              });
            }
          }
        }
      }
    }
  }

  // 3. 创建失败模块节点
  for (const failed of failedModules) {
    nodes.push({
      id: `failed-${failed.module}`,
      type: "failedModule",
      position: { x: 0, y: 0 },
      data: {
        label: failed.module,
        status: "failed",
        error: failed.error,
        components: {},
        apiList: [],
        counts: { controllers: 0, services: 0, mappers: 0 },
      },
    });

    edges.push({
      id: `gateway->failed-${failed.module}`,
      source: "gateway",
      target: `failed-${failed.module}`,
      type: "smoothstep",
      animated: true,
    });
  }

  // 4. 使用 dagre 自动布局（从上到下）
  const graph = new dagre.graphlib.Graph();
  graph.setGraph({ rankdir: "TB", nodesep: 80, ranksep: 120 });
  graph.setDefaultEdgeLabel(() => ({}));

  for (const node of nodes) {
    const width = node.type === "gateway" ? GATEWAY_WIDTH : NODE_WIDTH;
    const height = node.type === "gateway" ? GATEWAY_HEIGHT : NODE_HEIGHT;
    graph.setNode(node.id, { width, height });
  }

  for (const edge of edges) {
    graph.setEdge(edge.source, edge.target);
  }

  dagre.layout(graph);

  for (const node of nodes) {
    const layoutNode = graph.node(node.id);
    node.position = {
      x: layoutNode.x - (node.type === "gateway" ? GATEWAY_WIDTH / 2 : NODE_WIDTH / 2),
      y: layoutNode.y - (node.type === "gateway" ? GATEWAY_HEIGHT / 2 : NODE_HEIGHT / 2),
    };
  }

  return { nodes, edges };
}
