# AI 驱动的模块化微内核 PaaS 平台

> 毕业设计项目：探索 AI 自动生成代码与可视化相结合的模块化 PaaS 平台。

本仓库包含两个主要子项目：

- [`paas_project/`](paas_project/) — 后端底座与 LangGraph Agent。
- [`paas_dashboard/`](paas_dashboard/) — React + Vite 架构可视化前端。

## 项目结构

```text
.
├── paas_project/          # Python 后端（微内核、插件系统、Agent 接口）
│   ├── main.py            # 双进程启动入口（系统口 8000 + 服务口 8001）
│   ├── paas_core/         # 内核态（人类维护，禁止 AI 修改）
│   ├── plugins/           # 业务沙箱（AI 生成）
│   └── README.md          # 后端详细说明
├── paas_dashboard/        # React 前端（架构画布 + AI 智能体聊天面板）
│   ├── src/
│   └── README.md          # 前端详细说明
└── README.md              # 本文档
```

## 核心能力

- **稳定内核 + AI 沙箱**：`paas_core/` 提供依赖注入、模块热插拔、双端口服务；`plugins/` 交由 AI 生成业务代码，单模块崩溃不影响全局。
- **自然语言生成模块**：左侧 `AgentChatPanel` 通过 `POST /admin/agent/generate` 提交任务，后端 LangGraph Agent 流式生成并自动部署 CSM 插件。
- **实时架构可视化**：前端每 5 秒拉取作弊纸，以 React Flow 展示模块、Controller / Service / Mapper 组件及方法级调用关系。
- **SSE 流式响应与沉浸式聊天体验**：Agent 接口返回 `text/event-stream`，前端通过自定义 `fetch` 将 SSE 转换为纯文本流供 Vercel AI SDK 消费；AI 消息采用无边框文档化样式，并在生成过程中通过可折叠的“执行步骤”面板实时展示架构设计、代码生成、审查部署等节点进度，最终 Markdown 以打字机效果逐字呈现。

## 快速开始

### 1. 启动后端

需要 Python 3.10+ 与 conda `thesis` 环境：

```bash
cd paas_project
conda create -n thesis python=3.11 -y
conda activate thesis
pip install -r requirements.txt
python main.py
```

或使用脚本：

```bash
cd paas_project
./start_backend.sh
```

启动后会监听：

- 系统口 `http://localhost:8000`（前端、管理接口）
- 服务口 `http://localhost:8001`（业务 API）

### 2. 启动前端

需要 Node.js 18+：

```bash
cd paas_dashboard
npm install
npm run dev -- --host
```

默认访问：`http://localhost:5173`

### 3. 测试 Agent

在左侧聊天面板输入：

```text
创建用户模块
```

或直接用 curl：

```bash
curl -N -X POST http://localhost:8000/admin/agent/generate \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"task": "创建用户模块"}'
```

## 常用接口

| 接口 | 地址 | 说明 |
|------|------|------|
| 架构作弊纸 | `GET http://localhost:8000/admin/kernel/cheat-sheet` | 模块、组件、调用图、API 映射 |
| 模块状态 | `GET http://localhost:8000/admin/kernel/modules` | 已加载 / 失败模块 |
| Agent 生成 | `POST http://localhost:8000/admin/agent/generate` | SSE 流式生成并部署模块 |
| 健康检查 | `GET http://localhost:8000/health` | 系统口健康状态 |

## 跨域配置

后端默认允许 `http://localhost:5173` 跨域访问。若前端部署到其他地址，可设置环境变量：

```bash
PAA_DASHBOARD_ORIGINS="http://localhost:3000,http://localhost:4173" python main.py
```

## 详细文档

- [后端 README](paas_project/README.md) — 架构设计、AI 开发规范、管理接口、故障排查。
- [前端 README](paas_dashboard/README.md) — 技术栈、目录结构、组件说明、构建部署。

## 作者

本项目用于毕业设计研究，探索 AI 驱动的模块化 PaaS 平台构建与可视化方法。
