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
- 模块节点为**宽大、方正、内边距充足的容器**，为内部 CSM 组件留出足够呼吸空间。
- 每个模块卡片内部按 **Controller → Service → Mapper** 三层严格垂直堆叠；同一层内组件水平并排，层与层之间等距分布。
- 每个 CSM 组件（Controller/Service/Mapper）是一个可拖拽的父容器，内部的方法节点采用**单行水平展开**：所有方法卡片在同一水平行从左到右依次排列，不再换行，彻底避免边穿过无关卡片。
- **每个方法渲染为独立的 React Flow 子节点**，拥有自己的四向 handle（上/下/左/右），并支持在所属 CSM 容器内部自由拖拽（`extent: 'parent'` 限制不可拖出父容器）。
- 方法卡片**仅展示功能名**（`feature`），不再展示参数、HTTP 路径或 SQL；这些细节在右侧面板的组件详情中查看。
- **方法级精确连线（跨模块默认隐藏 + 模块内默认可见）**：
  - 模块内部调用（Controller → Service → Mapper）使用**灰色虚线**，默认**可见**，帮助理解组件间调用关系。
  - 跨模块调用分为两级：
    - **模块级连线（crossModule）**：大框连大框，默认**完全隐藏**。
    - **方法级连线（crossMethod）**：精确到具体方法，默认**完全隐藏**。
  - **悬浮到模块外框**时，当前模块及其依赖模块高亮，模块级连线以亮橙色实线 + 流动动画 + 置顶 zIndex 展示；无关模块及其内部节点透明度降为 `0.2`。
  - **悬浮到具体方法**时，该方法及其直接上下游方法（同模块或跨模块）高亮，模块与组件外框保持中性，相关的方法级连线与模块内连线以亮橙色 + 流动动画 + 置顶 zIndex 展示；无关节点与连线暗化降噪。
  - 鼠标移出节点后自动恢复到全局默认视图：跨模块连线隐藏，内部连线恢复可见。
  - 模块内部调用使用方法节点**顶部 target + 底部 source** 的 handle，跨模块调用使用**左侧 target + 右侧 source**。
  - 所有边使用 `smoothstep` 路由，并通过 `pathOptions: { borderRadius: 16 }` 设置 16px 圆角折线。
- 以节点画布形式展示所有插件模块（成功模块、失败模块）。
- **左侧固定 AI 智能体聊天面板**：基于自然语言输入自动生成并部署模块，支持 SSE 流式响应、Markdown 渲染与代码高亮。
- 顶部展示系统整体统计：Controller / Service / Mapper 数量、模块加载情况。
- **悬浮**画布节点，右侧面板展示该模块的组件、依赖和 API 列表；悬浮具体 CSM 方法可查看其构造参数、方法入参、下游 `calls` 目标及 Mapper SQL。
- 每 5 秒自动轮询后端作弊纸，实现近似实时的架构刷新。

### 1.1 截图示意

启动后访问 `http://localhost:5173`，可看到：

- 左侧边栏：AI 智能体助手聊天面板，可输入自然语言任务并查看流式生成结果
- 顶部状态栏：`Controller 2 / Service 2 / Mapper 2 / 模块 3/3`
- 中央画布：网关节点 + 宽大模块容器 + CSM 组件卡片 + 仅展示功能名的方法块 + 虚线调用边；悬浮模块/方法时自动聚焦高亮
- 右侧详情面板：悬浮模块时展示模块详情，悬浮方法时展示其所属 CSM 组件详情

---

## 2. 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | ^19.2.7 | UI 框架 |
| TypeScript | ~6.0.2 | 类型安全 |
| Vite | ^8.1.1 | 构建与开发服务器 |
| @xyflow/react | ^12.11.2 | 节点画布（React Flow v12） |
| @ant-design/x | ^2.8.0 | 智能体聊天原子组件（Bubble、Sender） |
| @ant-design/x-markdown | ^2.8.0 | AI 消息 Markdown 渲染与代码高亮 |
| ai | ^3.4.33 | Vercel AI SDK React Hook（useChat） |
| highlight.js | ^11.11.1 | 代码块语法高亮 |
| marked-highlight | ^2.2.4 | marked 高亮扩展 |
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
    ├── components/
    │   └── StatusHeader.tsx   # 顶部状态栏
    └── features/
        ├── architecture/      # 架构可视化功能模块
        │   ├── index.ts       # 功能模块对外导出
        │   ├── components/
        │   │   ├── ArchitectureGraph.tsx   # 画布主组件
        │   │   └── ModuleDetailPanel.tsx   # 右侧详情面板
        │   ├── nodes/
        │   │   ├── ComponentNode.tsx       # CSM 组件容器样式
        │   │   ├── GatewayNode.tsx         # 网关节点样式
        │   │   ├── MethodNode.tsx          # 方法子节点样式
        │   │   └── ModuleNode.tsx          # 模块节点样式
        │   ├── lib/
        │   │   └── graphBuilder.ts         # 解析作弊纸 → React Flow 节点/边
        │   └── styles/
        │       └── react-flow-overrides.css  # React Flow 样式微调
        └── agent/             # AI 智能体聊天功能模块
            ├── index.ts       # 对外导出 AgentChatPanel
            ├── components/
            │   └── AgentChatPanel.tsx      # 左侧智能体聊天面板
            └── styles/
                └── agent-chat.css          # 聊天消息 Markdown 样式
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

### 5.3 `features/architecture/lib/graphBuilder.ts`

核心转换逻辑：

1. 解析 `call_graph` 中的依赖字符串，如 `Service(OrderMapper, UserService)`。
2. 为每个模块生成一个 React Flow 节点；模块尺寸按内部组件数量与方法块内容自动扩展，容器宽大、内边距充足。
3. 模块内部组件按 **Controller（顶）→ Service（中）→ Mapper（底）** 三层垂直堆叠，同层组件水平并排。
4. 每个组件卡片内部将方法提升为**独立的 React Flow 子节点**（`type: "method"`），采用**单行水平展开**布局：
   - 方法节点固定宽度，在同一水平行从左到右依次排列，**不再换行**，避免边穿过无关卡片。
   - 所有方法节点顶部对齐；组件容器高度由最高的方法块决定，保证 Mapper 等高卡片不会侵入下一层。
   - 每个方法节点设置 `draggable: true` 与 `extent: "parent"`，允许在 CSM 容器内拖拽，且不会拖出父容器边界。
5. 方法级调用边改为**直接连接方法子节点**，并区分三类策略：
   - 解析 `components[].methods[].calls`，从源方法节点连到目标方法节点。
   - **模块内方法连线（inner）**：
     - 同模块内的组件调用（Controller → Service → Mapper）。
     - 默认 `hidden: false`，初始加载时即展示模块内部调用关系。
     - 方法级悬浮时，仅与当前方法相关的 inner 边高亮显示，无关的 inner 边临时隐藏。
     - 样式为灰色虚线（`#94a3b8`），`strokeWidth: 2`，`opacity: 0.9`，使用 `sourceHandle: bottom` → `targetHandle: top`。
   - **跨模块方法连线（crossMethod）**：
     - 调用方与接收方不在同一 `module`，精确到具体方法。
     - 默认 `hidden: true`，避免初始加载时线条爆炸。
     - 样式为亮橙色实线（`#f97316`），`strokeWidth: 2`，使用 `sourceHandle: right` → `targetHandle: left`。
   - **跨模块级连线（crossModule）**：
     - 由跨模块方法调用聚合而成，表示模块大框之间的依赖关系。
     - 默认 `hidden: true`。
     - 样式为亮橙色实线（`#f97316`），`strokeWidth: 2.5`，使用 `sourceHandle: right` → `targetHandle: left`。
   - 所有边使用 `smoothstep` 类型，`pathOptions: { borderRadius: 16 }`；边默认 `zIndex: 5`，聚焦时提升到 `zIndex: 1000`。
   - 每条边在 `data` 中携带 `edgeType: "inner" | "crossMethod" | "crossModule"` 与 `defaultStyle`，便于 `ArchitectureGraph` 在聚焦/取消聚焦时快速恢复默认样式。
6. 节点层级：模块容器 `zIndex: 0`，CSM 组件 `zIndex: 10`，方法子节点 `zIndex: 11`；同时通过 `src/features/architecture/styles/react-flow-overrides.css` 强制 `.react-flow__edges { z-index: 1 }`、`.react-flow__nodes { z-index: 2 }`，确保连线始终渲染在方法卡片背后，不会遮挡文字。
7. 所有业务模块在画布中横向并排，网关节点居中置顶。

### 5.4 `features/architecture/components/ArchitectureGraph.tsx`

渲染 React Flow 画布，注册自定义节点类型：

- `gateway`：顶部网关节点
- `module`：正常加载的模块
- `failedModule`：加载失败的模块（红色边框）
- `component`：CSM 组件卡片
- `method`：方法子节点

支持缩放、平移、MiniMap、Controls。

**自适应缩放与缩放限制**：

- 在 `<ReactFlow>` 上开启 `fitView`，并配置 `fitViewOptions={{ padding: 0.2, minZoom: 0.1, maxZoom: 1 }}`。
- 根组件同时设置 `minZoom={0.1}`、`maxZoom={2}`，避免节点众多时用户无法缩放到全貌。
- 画布首次加载或节点数据全量更新时，React Flow 会自动 fitView，将所有节点完整展示在可视区域内。

**交互模式切换（右下角面板）**：

- 使用 `<Panel position="bottom-right">` 悬浮放置模式切换按钮。
- 显示当前缩放比例（如 `25%`），通过 `useViewport()` 实时获取 `zoom` 并转换为百分比。
- 支持两种模式：
  - **鼠标模式**（默认）：`panOnDrag={true}`、`zoomOnScroll={true}`、`panOnScroll={false}`，左键拖拽画布、滚轮缩放。
  - **触摸板模式**：`panOnDrag={false}`、`zoomOnScroll={false}`、`panOnScroll={true}`，双指平移、捏合缩放。

**Hover 双层聚焦模式**（由 `onNodeMouseEnter` / `onNodeMouseLeave` 驱动）：

- 悬浮到**模块节点**（`module` / `failedModule`）：
  - 高亮当前模块及所有与其有跨模块依赖的模块（双向：既包含它依赖的下游模块，也包含依赖它的上游模块）。
  - 显示相关的**模块级跨模块连线**（`crossModule`），开启 `animated` 流动动画，`zIndex` 置顶到 `1000`，`selected` 设为 `true` 配合 `elevateEdgesOnSelect` 进一步提升层级。
  - 无关模块及其内部节点透明度降至 `0.2`，`zIndex` 降到 `0`。
- 悬浮到**方法节点**（`method`）：
  - 高亮当前方法节点，以及所有以它为 `source` 或 `target` 的直接上下游方法节点（同模块或跨模块）。
  - 模块与组件外框保持中性（不整体高亮也不整体暗化），仅通过方法卡片自身的透明度变化体现聚焦，视觉更清晰。
  - 右侧面板同步展示该方法的详细信息：所属组件/模块、HTTP 方法/路径（Controller）、参数、下游调用、SQL（Mapper）。
  - 隐藏所有**模块级跨模块连线**（`crossModule`）。
  - 显示相关的**方法级跨模块连线**（`crossMethod`）与**模块内方法连线**（`inner`），开启 `animated`，`zIndex` 置顶到 `1000`，`selected: true`。
  - 无关节点透明度降至 `0.2`，无关的方法连线隐藏或降级到 `zIndex: 0`。
- 鼠标移出节点：
  - 恢复所有节点 `opacity: 1` 与原始 `zIndex`。
  - 跨模块连线重新 `hidden: true` 并关闭动画。
  - 模块内连线恢复默认灰色虚线样式。

**方法节点锁定/固定（Hover + Click）**：

- 悬浮到方法节点后，再次**单击**该方法即可将其“锁定/固定”：
  - 被锁定方法的外边框加粗并附带同色系外发光，提示当前处于固定状态。
  - 方法级聚焦状态（高亮上下游方法、显示相关方法连线、隐藏模块级连线）保持不变。
  - 即使鼠标移出方法节点或移动到右侧控制面板，画布和详情面板都不会自动恢复默认视图。
- 再次单击已锁定的方法，或单击其他模块/组件/画布空白处，即可解除锁定并恢复默认视图：
  - 已锁定方法边框恢复为普通细边框。
  - 相关连线恢复默认隐藏/显示规则。
  - 右侧面板回到当前选中模块的摘要视图。
- 锁定期间，其他方法/模块的悬浮事件被忽略，避免误触切换聚焦状态。

- `onNodeMouseEnter` / `onNodeMouseLeave` 第一行调用 `event.stopPropagation()`，防止子节点事件冒泡到父级模块。
- 使用 `hoveredNodeIdRef` 记录当前最深层级悬浮节点，重复进入同一节点不重复计算；只有真正移出当前追踪节点时才重置画布。
- 方法级悬浮天然优先于模块级悬浮：鼠标进入方法卡片时，方法节点的事件先被处理并更新状态锁，后续模块级逻辑因 `hoveredNodeIdRef` 已指向方法节点而被忽略。

### 5.5 `features/architecture/nodes/ModuleNode.tsx`

模块节点展示：

- 模块名称
- 组件数量徽章：`C: x / S: x / M: x`
- 失败模块额外展示错误信息
- 容器采用大圆角、大阴影与充足内边距，营造“宽大方正”的模块外壳

### 5.6 `features/architecture/nodes/ComponentNode.tsx`

CSM 组件容器：

- 顶部标题栏：组件名 + 类型徽章（Controller/Service/Mapper）
- 容器本身作为 React Flow 父节点，内部不再直接渲染方法块，而是为 `MethodNode` 子节点提供背景与边界
- 容器宽度根据方法数量单行水平展开自动计算；容器高度由最高的方法块决定，保证各组件底部对齐、不会侵入下一层
- 底部预留拖拽余量，方便在容器内拖拽方法节点

### 5.7 `features/architecture/nodes/MethodNode.tsx`

方法子节点：

- 渲染为白色圆角卡片，带细边框与轻微阴影
- 顶部/底部/左侧/右侧各有一个 handle，用于连接调用边
- **卡片仅展示方法的功能名（`feature`），无功能名时回退到方法名（`name`）**
- 不再展示参数标签、HTTP 方法/路径徽章或 Mapper SQL 块
- 字体加粗，溢出时省略号截断，保持单行紧凑显示
- 支持在所属 CSM 容器内部拖拽，不可拖出父容器边界
- **悬浮到方法节点时，右侧面板展示该方法的功能名、参数、下游调用、SQL 等详细信息，不再仅展示所属组件摘要**
- **单击已悬浮的方法节点可将其锁定/固定，边框加粗并显示外发光，方便移动鼠标到右侧面板查看详情而不丢失聚焦**

右侧面板（`ModuleDetailPanel.tsx`）负责展示具体的方法签名、参数、HTTP 路径、下游 `calls` 目标及 SQL。

### 5.8 `features/architecture/components/ModuleDetailPanel.tsx`

悬浮/点击节点后展示：

- 模块运行状态
- 组件统计
- 组件与依赖列表（点击组件名可进入组件详情）
- 选中 CSM 组件时展示：构造参数、方法入参、下游 `calls`、Mapper SQL、Controller HTTP 方法
- **悬浮到方法节点时展示方法详情**：功能名/方法名、所属组件与模块、HTTP 方法/路径、参数列表、下游调用目标、Mapper SQL
- API 列表（方法 + 路径）

### 5.9 `components/StatusHeader.tsx`

顶部状态栏展示：

- 标题
- Controller / Service / Mapper 总数
- 成功/失败模块数
- 立即刷新按钮

### 5.10 `features/agent/components/AgentChatPanel.tsx`

左侧固定宽度的 AI 智能体聊天面板（`400px`），采用 flex 列布局：

- **顶部标题区**：展示面板标题与副标题。
- **中间消息列表**：可滚动，使用 Ant Design X 的 `Bubble.List` 渲染对话。
  - 用户消息居右（`placement: "end"`），AI 消息居左（`placement: "start"`）。
  - AI 消息使用 `@ant-design/x-markdown` 渲染，支持 Markdown、行内代码、代码块语法高亮（`highlight.js` + `marked-highlight`）。
  - 流式输出时自动追加内容并滚动到底部。
- **底部输入区**：使用 Ant Design X 的 `Sender` 组件。
  - `Enter` 发送，`Shift + Enter` 换行。
  - 请求中显示加载状态，支持点击停止生成。
  - 空消息列表时展示欢迎提示。

**SSE 适配**：

后端 Agent 接口返回 `data: <文本片段>\n\n` 格式的 SSE 流，而非 Vercel AI SDK 的标准数据流协议。`AgentChatPanel.tsx` 通过自定义 `fetch` 将 SSE 转换为纯文本流，再交给 `useChat` 在 `streamMode: "text"` 下消费。

**请求体适配**：

`useChat` 默认发送 `{ messages: [...] }`，但后端期望 `{ task: "..." }`。通过 `experimental_prepareRequestBody` 将最后一条用户消息内容映射为 `task` 字段：

```typescript
experimental_prepareRequestBody: ({ messages: chatMessages }) => {
  const lastMessage = chatMessages[chatMessages.length - 1];
  return { task: lastMessage?.content || "" };
},
```

**工具调用进度块**：

当后端返回 `> 🛠️ 正在执行: [tool_name]...\n\n` 等 Markdown 引用块时，`agent-chat.css` 会将其渲染为蓝色高亮任务进度条，便于用户感知 Agent 正在调用工具。

**错误处理**：

- 后端不可用时，聊天面板仍可正常显示与输入（`App.tsx` 已将聊天面板与架构画布解耦）。
- 请求失败会在消息列表下方展示红色错误提示。
- 通过 `keepLastMessageOnError: true` 保留用户输入，便于重试。

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

### 6.3 Agent 接口（智能体聊天面板）

左侧 `AgentChatPanel` 通过以下接口与后端 LangGraph Agent 交互：

```text
POST http://localhost:8000/admin/agent/generate
```

请求体示例：

```json
{"task": "创建用户模块"}
```

响应为 SSE 流，每帧格式为：

```text
data: 这是第一段生成内容

data: 这是第二段生成内容

```

前端将其转换为纯文本流，供 Vercel AI SDK `useChat` 消费，实现逐字显示。

该接口会根据自然语言任务自动生成 CSM 插件代码、执行安全检查并重载内核。生成结果会实时展示在左侧聊天面板中。

### 6.4 作弊纸数据结构

后端返回的关键字段：

> `components[].methods[].feature`（可选）：方法的中文功能名。前端已预留展示位，后端返回该字段后，方法卡片第一行将展示加粗中文功能名。

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
          "feature": "查询用户列表",
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

### 7.1 类型检查与构建

```bash
npm run build
```

`npm run build` 会先执行 `tsc -b` 进行类型检查，再通过 Vite 打包。

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

### 8.4 层级与连线防遮挡

为了避免模块边框/背景遮挡内部连线，同时让方法节点盖住连线，节点与边分别设置了 `zIndex`：

| 元素 | 默认 zIndex | 聚焦态 zIndex |
|------|------------|--------------|
| module / failedModule | 0 | 0（高亮）/ 0（暗化） |
| component | 10 | 10（高亮）/ 0（暗化） |
| method | 11 | 11（高亮）/ 0（暗化） |
| edge（默认/模块内） | 5 | 1000（高亮）/ 0（暗化） |

实现要点：
- 模块节点只作为背景容器，不拦截鼠标事件。
- 方法节点作为 component 的子节点，可直接拖拽，并通过 `extent: "parent"` 限制在 CSM 容器内。
- 边使用 `smoothstep`，`pathOptions: { borderRadius: 16 }` 让折线带有 16px 圆角，视觉上更柔和。
- 在 `src/features/architecture/styles/react-flow-overrides.css` 中将 `.react-flow__edges` 设为 `z-index: 3`、`.react-flow__nodes` 设为 `z-index: 2`，使 SVG 连线层整体位于节点层之上，聚焦态高亮边可覆盖方法卡片；默认态的模块内虚线较淡，不会严重遮挡文字。
- `<ReactFlow />` 开启 `elevateEdgesOnSelect={true}`，聚焦边同时设置 `selected: true`，获得 React Flow 内部的额外层级提升。
- 方法节点 handle 分别位于上下左右四个方向，内部调用走上下，跨模块调用走左右，水平位移错开锚点，减少边交叉。
- 为所有生成节点显式写入 `measured: { width, height }` 与 `handles` 数组，避免在预览或某些无 ResizeObserver 的环境下出现 handle 不可见、边无法计算的问题。

---

## 9. 常见问题

### Q1: 前端页面空白或报错

检查后端是否已启动：`curl http://localhost:8000/admin/kernel/cheat-sheet`

### Q2: 浏览器控制台报 CORS 错误

确认后端 `paas_core/server/system_server.py` 中的 `allow_origins` 包含前端地址。

### Q3: 画布没有自动刷新

检查 `hooks/useCheatSheet.ts` 中的轮询逻辑，以及后端接口是否返回新数据。

### Q4: 节点布局错乱

`features/architecture/lib/graphBuilder.ts` 使用固定规则布局：

- 模块节点横向并排，网关居中置顶。
- 模块内部组件按 CSM 三层垂直堆叠。
- 每个组件容器内部的方法节点采用**单行水平展开**：固定宽度、从左到右依次排列、不换行，所有方法顶部对齐，组件高度由最高方法决定。
- 同层组件过多时模块宽度会自动扩展。

若组件过于密集，可调整 `COMPONENT_H_GAP`、`COMPONENT_V_GAP`、`MODULE_H_GAP`、`MODULE_PADDING`、`METHOD_NODE_WIDTH` 或 `METHOD_NODE_GAP`。

### Q5: 如何添加新的节点样式？

1. 在 `features/architecture/nodes/` 下新建节点组件。
2. 在 `features/architecture/components/ArchitectureGraph.tsx` 的 `nodeTypes` 中注册。
3. 在 `features/architecture/lib/graphBuilder.ts` 中生成对应 `type` 的节点。

### Q6: 智能体聊天面板没有响应或报错

1. 确认后端 `admin/agent/generate` 接口已启动：`curl -X POST http://localhost:8000/admin/agent/generate -H "Content-Type: application/json" -d '{"task":"hello"}'`。
2. 检查浏览器控制台是否有 CORS 错误，确认后端 `allow_origins` 包含前端地址。
3. 该接口返回 SSE 流，格式需为 `data: <文本>\n\n`；若后端输出格式变更，需同步调整 `AgentChatPanel.tsx` 中的 `customFetch` 解析逻辑。
4. 即使架构画布加载失败，聊天面板仍可独立使用（`App.tsx` 中两者已解耦）。

---

## 作者

本项目用于毕业设计研究，探索 AI 驱动的模块化 PaaS 平台可视化方法。
