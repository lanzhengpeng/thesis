# PaaS 架构可视化前端

> 配套「AI 驱动的模块化微内核 PaaS 平台」的可视化仪表盘。
> 基于 React 19 + TypeScript 5 + Vite，使用 React Flow v12 渲染系统模块层级与调用关系。

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术栈](#2-技术栈)
3. [目录结构](#3-目录结构)
4. [快速开始](#4-快速开始)
5. [核心组件说明](#5-核心组件说明)
6. [与后端对接](#6-与后端对接)
7. [构建与部署](#7-构建与部署)
8. [开发注意事项](#8-开发注意事项)
9. [常见问题](#9-常见问题)

---

## 1. 项目概述

本前端用于直观展示 PaaS 平台的实时架构：

- 顶部居中展示“网关 / 鉴权”节点，所有业务模块在其下方横向并排铺开。
- 每个模块卡片内部按 **Controller → Service → Mapper** 三层垂直堆叠；同一层内组件水平并排。
- **所有 CSM 组件卡片默认完全展开为大尺寸全景卡片，不支持折叠**：
  - Controller 行展示 HTTP 方法标签 + 路由路径 + 方法签名。
  - Service 行展示方法签名。
  - Mapper 行展示方法签名及嵌入式 SQL 代码块。
- 调用连线精确到**方法级**：根据 `components[].methods[].calls`，从源方法行右侧的 handle 连到目标方法行左侧的 handle；跨模块调用使用橙色虚线流动边。
- 以节点画布形式展示所有插件模块（成功模块、失败模块）。
- 绘制模块间的跨模块依赖关系（如 `order_module → user_module`）。
- 顶部展示系统整体统计：Controller / Service / Mapper 数量、模块加载情况。
- 点击画布节点，右侧面板展示该模块的组件、依赖和 API 列表；选中具体 CSM 组件可查看其构造参数、方法入参、下游 `calls` 目标及 Mapper SQL。
- 每 5 秒自动轮询后端作弊纸，实现近似实时的架构刷新。

### 1.1 截图示意

启动后访问 `http://localhost:5173`，可看到：

- 顶部状态栏：`Controller 2 / Service 2 / Mapper 2 / 模块 3/3`
- 中央画布：网关节点 + 模块节点 + 依赖连线
- 右侧详情面板：选中模块的组件统计、调用关系、API 列表

---

## 2. 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | ^19.2.7 | UI 框架 |
| TypeScript | ^5.8.3 | 类型安全 |
| Vite | ^6.3.5 | 构建与开发服务器 |
| @xyflow/react | ^12.11.2 | 节点画布（React Flow v12） |
| 原生 fetch | - | HTTP 请求 |

---

## 3. 目录结构

```text
paas_dashboard/
├── index.html                 # HTML 入口
├── package.json               # 依赖与脚本
├── tsconfig.json              # TypeScript 根配置
├── tsconfig.app.json          # 应用 TS 配置
├── tsconfig.node.json         # Vite 配置 TS 配置
├── vite.config.ts             # Vite 配置
├── README.md                  # 本文档
└── src/
    ├── main.tsx               # React 应用挂载入口
    ├── App.tsx                # 主页面布局组合
    ├── index.css              # 全局样式
    ├── types/
    │   └── cheatSheet.ts      # 后端作弊纸数据结构类型
    ├── services/
    │   └── api.ts             # HTTP 请求封装
    ├── hooks/
    │   └── useCheatSheet.ts   # 数据拉取与轮询 Hook
    ├── lib/
    │   └── graphBuilder.ts    # 解析作弊纸 → React Flow 节点/边
    ├── components/
    │   ├── ArchitectureGraph.tsx   # 画布主组件
    │   ├── GatewayNode.tsx         # 网关节点样式
    │   ├── ModuleNode.tsx          # 模块节点样式
    │   ├── ModuleDetailPanel.tsx   # 右侧详情面板
    │   └── StatusHeader.tsx        # 顶部状态栏
    └── styles/
        └── react-flow-overrides.css  # React Flow 样式微调
```

---

## 4. 快速开始

### 4.1 环境要求

- Node.js >= 18
- npm 或 yarn
- 后端服务已启动（见后端 README）

### 4.2 安装依赖

```bash
cd paas_dashboard
npm install
```

### 4.3 启动开发服务器

```bash
npm run dev -- --host
```

默认访问：`http://localhost:5173`

### 4.4 启动后端

前端依赖后端 `8000` 系统口的 `/admin/kernel/cheat-sheet` 接口：

```bash
cd ../paas_project
python main.py
```

后端会同时启动：
- 系统口 `http://localhost:8000`（供前端与管理）
- 服务口 `http://localhost:8001`（供外部业务调用）

---

## 5. 核心组件说明

### 5.1 `services/api.ts`

封装对后端系统口的请求：

```typescript
export async function fetchCheatSheet(): Promise<CheatSheetResponse>
```

默认请求地址：`http://localhost:8000/admin/kernel/cheat-sheet`

### 5.2 `hooks/useCheatSheet.ts`

负责挂载时拉取数据，并每 5 秒轮询一次：

```typescript
const { data, loading, error, refetch } = useCheatSheet();
```

### 5.3 `lib/graphBuilder.ts`

核心转换逻辑：

1. 解析 `call_graph` 中的依赖字符串，如 `Service(OrderMapper, UserService)`。
2. 为每个模块生成一个 React Flow 节点，模块尺寸按内部组件数量与卡片内容自动扩展。
3. 模块内部组件按 **Controller（顶）→ Service（中）→ Mapper（底）** 三层垂直堆叠，同层组件水平并排。
4. 每个组件卡片根据方法数量、方法签名、HTTP 路径和 SQL 长度动态计算宽高，默认完全展开为大尺寸全景卡片。
5. 方法级调用边：
   - 根据 `components[].methods[].calls`，从源方法行右侧 handle 连到目标方法行左侧 handle。
   - 模块内部调用使用灰色实线。
   - 跨模块 Service 调用使用橙色虚线流动边。
6. 所有业务模块在画布中横向并排，网关节点居中置顶。

### 5.4 `components/ArchitectureGraph.tsx`

渲染 React Flow 画布，注册自定义节点类型：

- `gateway`：顶部网关节点
- `module`：正常加载的模块
- `failedModule`：加载失败的模块（红色边框）

支持缩放、平移、MiniMap、Controls。

### 5.5 `components/ModuleNode.tsx`

模块节点展示：

- 模块名称
- 组件数量徽章：`C: x / S: x / M: x`
- 失败模块额外展示错误信息

### 5.6 `components/ModuleDetailPanel.tsx`

点击节点后展示：

- 模块运行状态
- 组件统计
- 组件与依赖列表（点击组件名可进入组件详情）
- 选中 CSM 组件时展示：构造参数、方法入参、下游 `calls`、Mapper SQL、Controller HTTP 方法
- API 列表（方法 + 路径）

### 5.7 `components/StatusHeader.tsx`

顶部状态栏展示：

- 标题
- Controller / Service / Mapper 总数
- 成功/失败模块数
- 立即刷新按钮

---

## 6. 与后端对接

### 6.1 默认后端地址

前端默认连接：

```text
http://localhost:8000/admin/kernel/cheat-sheet
```

如需修改，编辑 `src/services/api.ts` 中的 `BASE_URL`。

### 6.2 跨域说明

后端 `paas_core/server/system_server.py` 已配置 `CORSMiddleware`，允许 `http://localhost:5173` 访问。若前端部署到其他域名，请同步修改后端 `allow_origins`。

### 6.3 Agent 接口（可选扩展）

后端系统口还提供 LangGraph Agent 接口：

```text
POST http://localhost:8000/admin/agent/generate
```

请求体示例：

```json
{"task": "创建用户模块"}
```

该接口会根据自然语言任务自动生成 CSM 插件代码、执行安全检查并重载内核。前端可在此基础上扩展“自然语言生成模块”的交互页面。

### 6.4 作弊纸数据结构

后端返回的关键字段：

```json
{
  "status": "ok",
  "modules": {
    "loaded": ["user_module", "order_module"],
    "failed": [{"module": "faulty_module", "error": "..."}]
  },
  "counts": {
    "controllers": 2,
    "services": 2,
    "mappers": 2
  },
  "call_graph": {
    "user_module": {
      "mapper": ["Mapper(None)"],
      "service": ["Service(UserMapper)"],
      "controller": ["Controller(UserService)"]
    }
  },
  "api_map": [
    {"module": "user_module", "method": "GET", "path": "/api/users/", "handler": "UserController.list_users"}
  ],
  "components": [
    {
      "name": "UserController",
      "type": "controller",
      "module": "user_module",
      "base_path": "/api/users",
      "assembled": true,
      "constructor_params": [{"name": "user_service", "type": "UserService"}],
      "inject_fields": [],
      "methods": [
        {
          "name": "list_users",
          "http_method": "GET",
          "path": "/api/users/",
          "params": [],
          "calls": ["UserService.list_users"],
          "sql": null
        }
      ]
    }
  ]
}
```

---

## 7. 构建与部署

### 7.1 类型检查

```bash
npm run typecheck
```

### 7.2 生产构建

```bash
npm run build
```

构建产物位于 `dist/` 目录。

### 7.3 预览生产构建

```bash
npm run preview
```

### 7.4 部署建议

- 将 `dist/` 目录部署到任意静态文件服务器（Nginx、Vercel、GitHub Pages 等）。
- 生产环境需将 `src/services/api.ts` 中的 `BASE_URL` 改为真实后端地址。
- 建议后端系统口也配置 HTTPS 与鉴权。

---

## 8. 开发注意事项

### 8.1 React Flow v12 类型兼容性

React Flow v12 对节点数据类型有严格要求。`ModuleNodeData` 接口需包含 `[key: string]: unknown` 索引签名：

```typescript
export interface ModuleNodeData {
  label: string;
  // ... 其他字段
  [key: string]: unknown;
}
```

### 8.2 自定义节点组件

由于 `NodeProps` 泛型在 v12 中的约束问题，组件签名采用：

```typescript
export function ModuleNode(props: NodeProps) {
  const data = props.data as ModuleNodeData;
  // ...
}
```

### 8.3 状态同步

`useNodesState` / `useEdgesState` 返回的 setter 用于状态同步。当后端数据变化时，通过 `useEffect` 更新节点和边：

```typescript
useEffect(() => {
  setNodes(initialNodes as Node[]);
  setEdges(initialEdges as Edge[]);
}, [initialNodes, initialEdges, setNodes, setEdges]);
```

---

## 9. 常见问题

### Q1: 前端页面空白或报错

检查后端是否已启动：`curl http://localhost:8000/admin/kernel/cheat-sheet`

### Q2: 浏览器控制台报 CORS 错误

确认后端 `paas_core/server/system_server.py` 中的 `allow_origins` 包含前端地址。

### Q3: 画布没有自动刷新

检查 `hooks/useCheatSheet.ts` 中的轮询逻辑，以及后端接口是否返回新数据。

### Q4: 节点布局错乱

`lib/graphBuilder.ts` 使用固定规则布局：

- 模块节点横向并排，网关居中置顶。
- 模块内部组件按 CSM 三层垂直堆叠。
- 同层组件过多时模块宽度会自动扩展。

若组件过于密集，可调整 `COMPONENT_H_GAP`、`COMPONENT_V_GAP` 或 `MODULE_H_GAP`。

### Q5: 如何添加新的节点样式？

1. 在 `components/` 下新建节点组件。
2. 在 `ArchitectureGraph.tsx` 的 `nodeTypes` 中注册。
3. 在 `graphBuilder.ts` 中生成对应 `type` 的节点。

---

## 作者

本项目用于毕业设计研究，探索 AI 驱动的模块化 PaaS 平台可视化方法。
