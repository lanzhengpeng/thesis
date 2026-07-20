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

export interface CheatSheetMethodItem {
  http_method?: string;
  path?: string;
  name: string;
  params: string[];
  calls: string[];
  sql?: string;
}

export interface CheatSheetComponentItem {
  name: string;
  type: "controller" | "service" | "mapper";
  module: string;
  base_path: string;
  assembled: boolean;
  constructor_params: { name: string; type: string }[];
  inject_fields: { name: string; type: string }[];
  methods: CheatSheetMethodItem[];
}

export interface CheatSheetResponse {
  status: string;
  modules: CheatSheetModuleStatus;
  counts: CheatSheetCounts;
  call_graph: CheatSheetCallGraph;
  api_map: CheatSheetApiItem[];
  components: CheatSheetComponentItem[];
}
