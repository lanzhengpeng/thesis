/**
 * 后端 /admin/kernel/cheat-sheet 返回的数据结构
 */

export interface CheatSheetModuleStatus {
  loaded: string[];
  failed: { module: string; error: string }[];
}

export interface CheatSheetCounts {
  controllers: number;
  services: number;
  mappers: number;
}

/**
 * 调用图结构：
 * {
 *   "user_module": {
 *     "mapper": ["Mapper(None)"],
 *     "service": ["Service(UserMapper)"],
 *     "controller": ["Controller(UserService)"]
 *   }
 * }
 */
export type CheatSheetCallGraph = Record<string, Record<string, string[]>>;

export interface CheatSheetApiItem {
  module: string;
  method: string;
  path: string;
  handler: string;
}

export interface CheatSheetResponse {
  status: string;
  modules: CheatSheetModuleStatus;
  counts: CheatSheetCounts;
  call_graph: CheatSheetCallGraph;
  api_map: CheatSheetApiItem[];
}
