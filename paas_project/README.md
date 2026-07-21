# AI 驱动的模块化微内核 PaaS 平台

> 一个专为 AI 自动生成代码而设计的“微内核 + 插件化”PaaS 平台。
> 通过物理隔离的模块化沙箱与自带防爆机制的微内核底座，为 AI 提供高度安全、职责单一的代码生成环境，实现业务逻辑的热拔插与动态演进。

---

## 目录

1. [项目概述](#1-项目概述)
2. [核心架构设计](#2-核心架构设计)
3. [功能模块详解](#3-功能模块详解)
4. [目录结构](#4-目录结构)
5. [快速开始](#5-快速开始)
6. [AI 开发规范](#6-ai-开发规范)
7. [管理接口](#7-管理接口)
8. [故障隔离与调试](#8-故障隔离与调试)
9. [扩展与演进路线](#9-扩展与演进路线)
10. [常见问题](#10-常见问题)

---

## 1. 项目概述

### 1.1 背景与痛点

传统架构在面对大语言模型（LLM）自动生成代码时，普遍存在以下问题：

| 痛点 | 说明 |
|------|------|
| **上下文超载** | AI 一次性处理整个项目代码，容易遗忘关键约束。 |
| **幻觉改错代码** | AI 可能修改不该动的框架代码或核心配置。 |
| **牵一发而动全身** | 一处错误可能导致整个系统崩溃，无法优雅降级。 |
| **架构与代码脱节** | 文档容易过时，运行系统与描述不一致。 |
| **Token 浪费** | 每次迭代都把无关代码喂给 AI，成本高且效果差。 |

### 1.2 解决思路

本项目采用 **“稳定内核 + AI 沙箱”** 的双层架构：

- **内核态（`paas_core/`）**：由人类维护，提供加载、注入、路由、安全等基础设施，**绝对稳定，禁止 AI 修改**。
- **用户态/沙箱区（`plugins/`）**：全权交由 AI 生成业务代码，按业务模块隔离，**故障不影响全局**。

通过这种模式，AI 只需要专注于单一业务模块的实现，无需理解整个系统；底座负责把模块组装成可运行的 Web 服务，并实时生成系统调用图。

### 1.3 核心特性

- ✅ **热插拔业务模块**：新增、删除、修改模块无需重启整个系统。
- ✅ **爆炸半径隔离**：单个模块崩溃不会影响其他模块。
- ✅ **自动依赖注入**：通过装饰器声明依赖，容器自动装配。
- ✅ **动态 API 暴露**：写完 Controller 即刻自动生成 HTTP 接口。
- ✅ **实时调用图（作弊纸）**：自动扫描内存依赖，生成全局 API 字典。
- ✅ **方法级元数据**：支持为 Controller / Service / Mapper 方法标注入参、下游调用与 SQL，供前端生成精确调用连线。
- ✅ **AI 沙箱工具链**：限制 AI 只能操作 `plugins/` 目录，防止越权。
- ✅ **两层扫描装配**：先发现、再组装，避免过早执行有问题的业务代码。
- ✅ **双端口隔离**：系统管理口（8000）与对外开放服务口（8001）物理分离。

---

## 2. 核心架构设计

### 2.1 空间划分

系统在物理与逻辑上严格划分为两大空间，并通过双端口对外暴露：

```text
                              外部请求
                                 │
         ┌───────────────────────┴───────────────────────┐
         │                                                 │
         ↓                                                 ↓
┌─────────────────────┐                         ┌─────────────────────┐
│ 8000 系统管理口      │                         │ 8001 对外开放服务口  │
│ （本系统前端/管理员） │                         │ （外部调用方）       │
│ /admin/kernel/*     │                         │ /api/users          │
│ /health             │                         │ /api/orders         │
└──────────┬──────────┘                         └──────────┬──────────┘
           │                                               │
           └─────────────────┬─────────────────────────────┘
                             ↓
           ┌───────────────────────────────────────────────┐
           │  内核态 (Kernel Space) —— 人类维护，绝对稳定      │
           │  ├─ Microkernel   : 模块扫描、异常隔离、生命周期   │
           │  ├─ DI Container  : 依赖注入、拓扑排序、两遍扫描   │
           │  ├─ System Server : 8000 管理接口                │
           │  ├─ Service Server: 8001 业务路由                │
           │  ├─ SDK           : @Controller / @Service ...   │
           │  ├─ Agent Tools   : AI 文件操作沙箱               │
           │  └─ LangGraph Agent: 自然语言生成插件工作流        │
           └───────────────────┬───────────────────────────────┘
                               ↓  严格隔离
           ┌───────────────────────────────────────────────┐
           │  用户态/沙箱区 (User Space) —— AI 生成，热拔插     │
           │  ├─ plugins/user_module/                       │
           │  ├─ plugins/order_module/                      │
           │  └─ plugins/...                                │
           └───────────────────────────────────────────────┘
```

### 2.2 CSM 三层业务架构

所有业务代码必须遵循 **CSM（Controller-Service-Mapper）** 三层架构：

| 层级 | 装饰器 | 职责 | 可调用下层 |
|------|--------|------|-----------|
| **Controller** | `@Controller(path)` | HTTP 接口、请求响应转换 | Service |
| **Service** | `@Service` | 业务规则、流程编排 | Service、Mapper |
| **Mapper** | `@Mapper` | 数据持久化、数据库访问 | 无（原则上不依赖其他组件） |

**重要约束**：Controller 严禁直接调用 Mapper，必须通过 Service 中转。这保证了业务逻辑的原子性和可复用性。

---

## 3. 功能模块详解

### 3.1 微内核动态装载引擎（`microkernel.py`）

#### 3.1.1 热插拔扫描

系统启动时，自动遍历 `plugins/` 目录下的所有业务模块，识别有效的 Python 模块。

```python
kernel = MicroKernel()
report = kernel.boot()
```

#### 3.1.2 爆炸半径隔离

装载过程中，任何含有语法错误、运行时异常或非法调用的“故障模块”，都会被 `try-except` 捕获并强制丢弃。故障被限制在单一模块内，主系统及其他模块继续正常运行。

示例：`plugins/faulty_module/FaultyService.py` 在 `__init__` 中故意抛出异常，系统会记录失败并继续加载其他模块。

### 3.2 智能依赖注入容器（`di_container.py`）

#### 3.2.1 标准化契约

提供一组标准化装饰器：

```python
from paas_core import (
    Controller, Service, Mapper, Inject,
    GET, POST, PUT, DELETE, PATCH,
    service_method, sql_operation,
)
```

| 装饰器 | 用途 |
|--------|------|
| `@Controller("/api/users")` | 标记 HTTP 接口类，定义基础路径 |
| `@Service` | 标记业务逻辑类 |
| `@Mapper` | 标记数据访问类 |
| `@Inject` | 标记需要注入的字段（参数注入优先推荐） |
| `@GET(path, calls=..., feature=...)` / `@POST(...)` 等 | 标记 Controller 的 HTTP 端点，可声明下游调用与中文功能名 |
| `@service_method(params, calls, feature)` | 标记 Service 业务方法，记录入参、下游调用与中文功能名 |
| `@sql_operation(sql, params, feature)` | 标记 Mapper 数据库操作，绑定 SQL 模板与中文功能名 |

#### 3.2.2 两遍扫描装配法

1. **首轮探索**：全量扫描插件，收集所有被装饰器标记的类，存入内存注册表（不执行业务代码）。
2. **次轮组装**：自底向上实例化。框架自动将 Mapper 注入给 Service，将 Service 注入给 Controller，彻底接管对象生命周期。

依赖通过 `__init__` 的类型注解自动识别：

```python
@Service
class UserService:
    def __init__(self, user_mapper: UserMapper):
        self.user_mapper = user_mapper
```

### 3.3 动态 API 双端口桥接（`system_server.py` / `service_server.py`）

底座将内存中存活的 Controller 实例动态转换为 FastAPI HTTP 路由，但管理流量与业务流量分别跑在不同端口：

| 端口 | 进程 | 用途 | 典型路由 |
|------|------|------|----------|
| **8000** | System Server | 平台自身前端/管理员 | `/admin/kernel/*`、`/health` |
| **8001** | Service Server | 外部调用方 | `/api/users/*`、`/api/orders/*` |

例如：

```python
@Controller("/api/users")
class UserController:
    @GET("/")
    def list_users(self):
        return [...]
```

启动后会同时在 **8001** 服务口生成：`GET /api/users/`；在 **8000** 系统口生成作弊纸：`GET /admin/kernel/cheat-sheet`。

**8001 热更新机制**：服务口不将每个 Controller 方法注册为固定的 FastAPI 路由，
而是使用 `DynamicDispatcher` 在请求时根据当前内核状态动态匹配并调用控制器方法。
当 `plugins/` 下任何 `.py` 文件变更时，`PluginWatcher` 会自动重建内核并原子替换分发器引用的内核，
因此新增、修改、删除插件后都无需重启 8001 进程。

这种物理隔离 + 动态分发的好处：
- 管理接口不会暴露在公网业务域名下，降低攻击面。
- 业务口可以独立做限流、鉴权、负载均衡，不受管理口影响。
- 业务口支持真正的热拔插：插件变更后约 1 秒自动生效。

### 3.4 “代码即真理”与 AI 上下文管理

#### 3.4.1 AST 动态拓扑提取

放弃维护脆弱的静态文档。底座通过扫描内存中的依赖关系，实时生成一份“全局 API 字典（作弊纸）”。

访问地址（系统口 8000）：

```text
GET http://localhost:8000/admin/kernel/cheat-sheet
```

返回内容包括：

- 已加载模块列表
- 组件数量统计
- 调用图（call_graph）
- API 映射表（api_map）
- 结构化组件元数据（components），包含每个 Controller / Service / Mapper 的构造参数、字段注入、方法签名、下游调用（calls）及 Mapper SQL

#### 3.4.2 精准上下文投喂

当 AI 需要跨模块调用或修改逻辑时，只投喂：

1. 当前操作的局部文件
2. 高密度“作弊纸”

避免把整个项目代码塞给 AI，降低 Token 消耗并减少幻觉。

#### 3.4.3 前端架构可视化

`paas_dashboard/` 是一个独立的 React Flow 可视化前端，实时消费 `/admin/kernel/cheat-sheet`：

- 顶部展示“网关 / 鉴权”节点，下方横向并排展示所有业务模块。
- 模块卡片内部严格按 **Controller → Service → Mapper** 三层垂直堆叠，同一层组件水平并排。
- 所有 CSM 组件卡片默认完全展开为大尺寸全景卡片，不可折叠：
  - Controller 行展示 HTTP 方法标签、路由路径和方法签名。
  - Service 行展示方法签名。
  - Mapper 行展示方法签名及嵌入式 SQL 代码块。
- 调用连线精确到方法级：根据 `methods[].calls`，从源方法行右侧连到目标方法行左侧；跨模块 Service 调用使用橙色虚线流动边，内部调用使用灰色实线。

启动方式见 `paas_dashboard/README.md`。

### 3.5 智能体沙箱与人机协同治理

#### 3.5.1 防越权工具链

AI 文件操作工具内置强校验，锁死 `plugins/` 目录，无法通过 `../` 逃逸到内核层。

提供以下工具函数：

- `list_plugins()`：列出所有插件模块
- `create_plugin(name)`：创建新模块目录
- `write_plugin_file(plugin, file, content)`：写入/覆盖插件文件
- `read_plugin_file(plugin, file)`：读取插件文件
- `delete_plugin(plugin)`：删除插件模块
- `static_check(plugin, file)`：静态安全检查

#### 3.5.2 双重确认机制（建议实现）

当 AI 对复杂逻辑进行“读取 → 覆写”时，系统应默认生成 Draft 草稿文件，前端通过 Diff 视图展示修改前后的差异，由人类确认后才正式应用。

> 当前骨架已提供基础工具函数，Diff 确认流程建议在前端或管理接口层实现。

#### 3.5.3 LangGraph Agent 工作流

底座新增基于 LangGraph 的 agent 工作流（`paas_core/agent/agent_module.py`），支持通过自然语言任务自动生成并部署插件模块。

典型调用链：

1. `POST /admin/agent/generate` 接收任务，例如 `"创建用户模块"`。
2. Agent 提取模块名，规划 Mapper / Service / Controller 文件及 API 前缀。
3. 生成符合 CSM 规范的代码（优先使用 LLM，失败时回退到确定性模板）。
4. 通过 `agent_tools` 将代码写入 `plugins/<module_name>/`。
5. 执行 `static_check` 静态安全检查。
6. 调用 `MicroKernel.reload_plugin()` 刷新系统口容器；8001 服务口通过文件监听自动感知变更。

**流式响应**：`/admin/agent/generate` 现在返回 `text/event-stream` SSE 流，前端可实时看到大模型输出（`on_chat_model_stream`）和工具执行提示（`on_tool_start`），无需解析中间 JSON；最终结果以一条 JSON 事件推送。

**LLM 配置**：默认读取环境变量 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`AGENT_MODEL`；未配置时回退到 `test_api.ipynb` 中记录的本地接口。若 LLM 不可用或返回格式错误，agent 会自动使用内置模板，保证随时可运行。

---

## 4. 目录结构

```text
paas_project/
├── paas_core/                 # 系统底座（人类维护，禁止 AI 修改）
│   ├── __init__.py            # 公共 API 导出
│   ├── sdk.py                 # 装饰器契约：@Controller, @Service, @Mapper, @Inject
│   │
│   ├── agent/                 # AI 代理模块：大模型交互与工具调用
│   │   ├── __init__.py
│   │   ├── agent_api.py       # Agent 管理接口路由
│   │   ├── agent_module.py    # LangGraph 自然语言生成插件工作流
│   │   └── agent_tools.py     # AI 工具箱：带沙箱校验的文件操作
│   │
│   ├── kernel/                # 内核基座模块：依赖注入与插件生命周期
│   │   ├── __init__.py
│   │   ├── microkernel.py     # 微内核：模块扫描、异常隔离、热重载
│   │   ├── di_container.py    # 依赖注入容器：两遍扫描、拓扑排序、实例化
│   │   └── plugin_watcher.py  # 热更新监听
│   │
│   └── server/                # 网关与路由模块：HTTP 服务、路由桥接与动态分发
│       ├── __init__.py
│       ├── web_server.py      # 单端口兼容层（聚合模式）
│       ├── system_server.py   # 8000 系统管理口
│       ├── service_server.py  # 8001 对外开放服务口
│       ├── route_bridge.py    # Controller → FastAPI 路由通用桥接
│       └── dynamic_dispatcher.py  # 动态路由分发
│
├── plugins/                   # 业务沙箱（AI 生成）
│   ├── user_module/           # 用户模块
│   │   ├── UserMapper.py      # 数据访问
│   │   ├── UserService.py     # 业务逻辑
│   │   └── UserController.py  # HTTP 接口
│   │
│   ├── order_module/          # 订单模块（演示跨模块依赖）
│   │   ├── OrderMapper.py
│   │   ├── OrderService.py    # 依赖 UserService
│   │   └── OrderController.py
│   │
│   └── faulty_module/         # 故障模块（用于测试隔离）
│       └── FaultyService.py
│
├── database/                  # 数据文件目录（可选）
│
├── main.py                    # 双进程启动入口
├── requirements.txt           # 依赖清单
└── README.md                  # 本文档
```

---

## 5. 快速开始

### 5.1 环境要求

- Python >= 3.10（使用了 `dict | None` 等联合类型语法）
- pip

### 5.2 环境准备

后端使用 **conda `thesis` 环境**运行，请确保已创建并激活该环境：

```bash
conda create -n thesis python=3.11 -y
conda activate thesis
pip install -r requirements.txt
```

> 后续所有后端命令均默认在 `thesis` 环境中执行。如果未手动激活环境，请使用 `conda run -n thesis <command>`。

### 5.3 启动服务

推荐方式：一键启动双进程（系统口 8000 + 服务口 8001）：

```bash
cd paas_project
conda run -n thesis python main.py
```

或使用项目提供的启动脚本（已内置 `thesis` 环境）：

```bash
cd paas_project
./start_backend.sh
```

输出示例：

```text
[系统口] 监听 0.0.0.0:8000
[服务口] 监听 0.0.0.0:8001
```

也可以单独启动某一端口：

```bash
# 仅系统口
./start_backend.sh --mode system

# 仅服务口
./start_backend.sh --mode service
```

如需回到旧的单端口聚合模式（例如开发调试）：

```bash
conda run -n thesis uvicorn paas_core.server.web_server:create_app --reload --port 8000
```

### 5.4 测试接口

#### 业务接口（服务口 8001）

创建用户：

```bash
curl -X POST http://localhost:8001/api/users/ \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com"}'
```

查询用户：

```bash
curl http://localhost:8001/api/users/
```

创建订单（依赖用户模块）：

```bash
curl -X POST http://localhost:8001/api/orders/ \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "total": 99.9}'
```

#### 管理接口（系统口 8000）

查看系统作弊纸：

```bash
curl http://localhost:8000/admin/kernel/cheat-sheet
```

列出模块状态：

```bash
curl http://localhost:8000/admin/kernel/modules
```

通过 LangGraph Agent 生成模块（自然语言 → 插件），接口以 SSE 流式返回：

```bash
curl -N -X POST http://localhost:8000/admin/agent/generate \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"task": "创建用户模块"}'
```

SSE 事件说明：

| 事件来源 | SSE 数据示例 | 含义 |
|----------|--------------|------|
| `on_chat_model_stream` | `data: 正在生成 UserMapper...\n\n` | 大模型实时输出块，前端可直接拼接实现打字机效果 |
| `on_tool_start` | `data: \n> 🛠️ 正在执行: write_plugin_file...\n\n` | 内部工具开始执行，前端可用 Markdown 引用样式渲染 |
| 流水线结束 | `data: {"status": "deployed", ...}\n\n` | 最终生成结果 JSON，包含文件列表、静态检查、重载报告等 |

> 工具执行完毕（`on_tool_end`）的冗长 JSON 结果不会推送给前端，仅注入 LangGraph 状态供后续大模型节点使用。

Agent 会根据任务自动创建 `plugins/<module_name>/` 目录、生成 CSM 代码、执行静态检查并重载内核。成功后可在 8001 服务口调用对应的业务接口。

---

## 6. AI 开发规范

### 6.1 AI 可操作范围

AI **只能**操作 `plugins/` 目录下的文件，**严禁**触碰 `paas_core/`、`main.py`、`requirements.txt` 等内核文件。

### 6.2 模块命名规范

- 模块目录名必须是合法的 Python 标识符，建议使用小写下划线命名，如 `user_module`、`order_module`。
- 每个模块内部按 CSM 三层拆分文件：
  - `XxxMapper.py`
  - `XxxService.py`
  - `XxxController.py`

### 6.3 代码编写规范

#### 6.3.1 Mapper 示例

```python
from paas_core import Mapper, sql_operation


@Mapper
class UserMapper:
    def __init__(self):
        self._users = {}
        self._next_id = 1

    @sql_operation(
        sql="INSERT INTO users (username, email) VALUES (%s, %s)",
        params=["username", "email"],
        feature="创建用户",
    )
    def create(self, username: str, email: str) -> dict:
        user_id = self._next_id
        self._next_id += 1
        user = {"id": user_id, "username": username, "email": email}
        self._users[user_id] = user
        return user

    @sql_operation(
        sql="SELECT * FROM users WHERE id = %s",
        params=["user_id"],
        feature="查询用户",
    )
    def get(self, user_id: int) -> dict | None:
        return self._users.get(user_id)

    @sql_operation(sql="SELECT * FROM users", feature="全量列表")
    def list_all(self) -> list:
        return list(self._users.values())
```

#### 6.3.2 Service 示例

```python
from paas_core import Service, service_method
from .UserMapper import UserMapper


@Service
class UserService:
    def __init__(self, user_mapper: UserMapper):
        self.user_mapper = user_mapper

    @service_method(params=["username", "email"], calls=["UserMapper.create"], feature="用户注册")
    def register(self, username: str, email: str) -> dict:
        return self.user_mapper.create(username, email)

    @service_method(params=["user_id"], calls=["UserMapper.get"], feature="查询用户")
    def get_user(self, user_id: int) -> dict | None:
        return self.user_mapper.get(user_id)

    @service_method(calls=["UserMapper.list_all"], feature="全量列表")
    def list_users(self) -> list:
        return self.user_mapper.list_all()
```

#### 6.3.3 Controller 示例

```python
from paas_core import Controller, GET, POST
from .UserService import UserService


@Controller("/api/users")
class UserController:
    def __init__(self, user_service: UserService):
        self.user_service = user_service

    @GET("/", calls=["UserService.list_users"], feature="查询列表")
    def list_users(self):
        return self.user_service.list_users()

    @GET("/{user_id}", calls=["UserService.get_user"], feature="查询用户")
    def get_user(self, user_id: str):
        user = self.user_service.get_user(int(user_id))
        if user is None:
            return {"error": "not found"}
        return user

    @POST("/", calls=["UserService.register"], feature="创建用户")
    def create_user(self, payload: dict):
        return self.user_service.register(
            payload.get("username", ""),
            payload.get("email", ""),
        )
```

### 6.4 HTTP 方法装饰器

Controller 方法使用标准 HTTP 方法装饰器，所有装饰器都可选地支持 `calls` 与 `feature` 参数：

- `calls`：声明该方法内部调用的下游 Service / Mapper 方法，供前端绘制方法级调用连线。
- `feature`：简短中文功能名（4~8 字动宾短语），用于可视化拓扑展示。

```python
from paas_core import GET, POST, PUT, DELETE, PATCH
```

示例：

```python
@Controller("/api/orders")
class OrderController:
    @Inject
    def __init__(self, order_service: OrderService):
        self.order_service = order_service

    @POST("/", calls=["OrderService.create_order"], feature="创建订单")
    def create_order(self, request_data):
        return self.order_service.create_order(request_data)
```

### 6.5 Service 与 Mapper 方法装饰器

为了把调用图精确到方法级别，Service 和 Mapper 的方法也可以使用专用装饰器声明元数据。

#### `@service_method(params, calls, feature)`

用于 Service 业务方法，记录入参、下游调用与中文功能名：

```python
from paas_core import Service, service_method
from .OrderMapper import OrderMapper

@Service
class OrderService:
    @Inject
    def __init__(self, order_mapper: OrderMapper):
        self.order_mapper = order_mapper

    @service_method(params=["data"], calls=["OrderMapper.insert_order"], feature="创建订单")
    def create_order(self, data):
        return self.order_mapper.insert_order(data['id'], data['amount'])
```

#### `@sql_operation(sql, params, feature)`

用于 Mapper 数据库操作方法，绑定 SQL 模板、参数与中文功能名：

```python
from paas_core import Mapper, sql_operation

@Mapper
class OrderMapper:
    @sql_operation(
        sql="INSERT INTO orders (id, amount) VALUES (%s, %s)",
        params=["order_id", "amount"],
        feature="订单入库"
    )
    def insert_order(self, order_id, amount):
        pass
```

> **功能名 `feature` 规范**：
> - 必须是简短的动宾短语，通常 4~8 个字，例如 `"查询订单"`、`"创建用户"`、`"订单入库"`。
> - 用于在可视化拓扑中直观展示该方法的业务职能。
> - ❌ 不要写成冗长逻辑描述，如 `"创建订单之前先去用户模块校验用户ID是否存在"`。

### 6.6 跨模块调用

Service 可以依赖其他模块的 Service：

```python
from plugins.user_module.UserService import UserService
from .OrderMapper import OrderMapper

@Service
class OrderService:
    def __init__(self, order_mapper: OrderMapper, user_service: UserService):
        self.order_mapper = order_mapper
        self.user_service = user_service
```

### 6.7 禁止事项

- ❌ 导入 `os`、`sys`、`subprocess`、`socket` 等危险模块
- ❌ 使用 `eval`、`exec`、`__import__`
- ❌ 写死端口号或路径
- ❌ 直接操作 `paas_core/` 内核文件
- ❌ Controller 直接调用 Mapper
- ❌ 循环依赖

---

## 7. 管理接口（系统口 8000）

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/admin/kernel/modules` | GET | 列出已加载/失败的模块 |
| `/admin/kernel/cheat-sheet` | GET | 获取全局调用图、API 映射与结构化组件元数据 |
| `/admin/kernel/reload/{plugin_name}` | POST | 重新加载指定插件（刷新系统口容器；8001 服务口通过文件监听自动热更新） |
| `/admin/agent/generate` | POST | LangGraph Agent：自然语言生成并部署插件模块，返回 `text/event-stream` SSE 流 |
| `/admin/agent/sessions/{session_id}/generate` | POST | 在需求确认后触发代码生成流水线，同样返回 SSE 流 |

> **注意**：
> 1. `/admin/kernel/reload` 主动刷新 **8000 系统口** 的内存容器，用于前端画布实时展示。
> 2. **8001 服务口** 内部通过 `watchdog` 监听 `plugins/` 目录，任何 `.py` 文件变更都会自动触发内核重建并热更新路由，无需重启进程。

### 7.1 作弊纸响应示例

`GET /admin/kernel/cheat-sheet` 返回的 JSON 示例：

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
    "order_module": {
      "mapper": ["OrderMapper(None)"],
      "service": ["OrderService(OrderMapper, UserService)"],
      "controller": ["OrderController(OrderService)"]
    }
  },
  "api_map": [
    {"module": "user_module", "method": "GET", "path": "/api/users/", "handler": "UserController.list_users"}
  ],
  "components": [
    {
      "name": "UserMapper",
      "type": "mapper",
      "module": "user_module",
      "base_path": "",
      "assembled": true,
      "constructor_params": [],
      "inject_fields": [],
      "methods": [
        {
          "name": "create",
          "feature": "创建用户",
          "params": ["username", "email"],
          "calls": [],
          "sql": "INSERT INTO users (username, email) VALUES (%s, %s)"
        }
      ]
    },
    {
      "name": "UserService",
      "type": "service",
      "module": "user_module",
      "base_path": "",
      "assembled": true,
      "constructor_params": [{"name": "user_mapper", "type": "UserMapper"}],
      "inject_fields": [],
      "methods": [
        {
          "name": "register",
          "feature": "用户注册",
          "params": ["username", "email"],
          "calls": ["UserMapper.create"],
          "sql": null
        }
      ]
    },
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
          "name": "create_user",
          "feature": "创建用户",
          "http_method": "POST",
          "path": "/api/users/",
          "params": ["payload"],
          "calls": ["UserService.register"],
          "sql": null
        }
      ]
    }
  ]
}
```

`components` 数组为每个 CSM 组件提供了结构化元数据，前端可据此：

- 在右侧面板展开每个方法的入参、下游调用和 SQL。
- 根据 `methods[].calls` 绘制方法到方法的精确调用连线。
- 根据 `assembled` 状态区分已组装与未组装组件。

---

## 8. 故障隔离与调试

### 8.1 模块加载失败

启动时会输出“发现报告”和“组装报告”，明确显示：

- 哪些模块加载成功
- 哪些组件被发现
- 哪些组件实例化失败及错误原因

### 8.2 常见失败原因

| 现象 | 原因 | 解决 |
|------|------|------|
| `Dependency X of Y is unavailable` | 依赖的组件未成功实例化 | 检查被依赖模块是否有异常 |
| `Syntax error` | 代码语法错误 | 修正代码后重新加载 |
| `Forbidden import` | 触发了静态安全检查 | 移除 `os`、`sys` 等禁止导入 |
| `Dependency cycle detected` | 循环依赖 | 重新设计模块边界 |

### 8.3 调试模式

直接运行 `./start_backend.sh` 会在控制台打印完整的启动日志和作弊纸内容，便于排查问题。

---

## 9. 扩展与演进路线

### 9.1 近期（骨架已完成）

- [x] 微内核动态装载
- [x] 依赖注入与两遍扫描
- [x] FastAPI 路由桥接
- [x] 双端口隔离（8000 系统口 + 8001 服务口）
- [x] AI 沙箱工具链
- [x] 全局调用图生成
- [x] 方法级元数据（params / calls / sql）
- [x] 前端可视化画布（React Flow）展示架构图

### 9.2 中期

- [ ] 数据库持久化（SQLAlchemy + Alembic migration）
- [x] 模块热重载时自动刷新 8001 服务口路由（无需重启服务）
- [x] AI 对话入口：自然语言 → 生成模块 → 自动部署（LangGraph Agent 已接入）
- [ ] Diff 确认机制：AI 修改先生成 Draft，人工确认后应用

### 9.3 远期

- [ ] 多租户隔离
- [ ] 容器级隔离（当前为进程 + 模块级隔离）
- [ ] 统一的鉴权与限流网关
- [ ] 模块市场 / 模板库
- [ ] 前端页面自动生成（根据后端 OpenAPI 生成管理后台）

---

## 10. 常见问题

### Q1: AI 能修改内核代码吗？

**不能。** AI 只能通过 `paas_core/agent/agent_tools.py` 暴露的工具操作 `plugins/` 目录。`paas_core/` 和 `main.py` 等文件不暴露给 AI。

### Q2: 一个模块崩溃了会怎样？

该模块被隔离，不影响其他模块和主系统。启动日志的“组装报告”会显示失败原因。

### Q3: 如何新增一个业务模块？

在 `plugins/` 下新建目录，按 CSM 三层编写类并打上装饰器，重启服务即可自动加载。

### Q4: Controller 必须依赖 Service 吗？

规范上是的。Controller 不应直接调用 Mapper，以保证业务逻辑集中在 Service 层。

### Q5: 当前数据存储在哪里？

示例模块使用内存字典存储。后续可替换为数据库 Mapper，业务代码无需改动。

### Q6: 为什么刷新热重载后业务路由没有变？

旧版本中 `/admin/kernel/reload` 只刷新 **8000 系统口** 的内存容器；而 **8001 服务口** 曾在启动时固定所有业务路由，导致新增/修改插件后需要重启 8001 进程。

**当前版本已改为动态分发**：8001 服务口在请求时根据当前内核状态匹配控制器方法，
并由 `PluginWatcher` 监听 `plugins/` 目录。任何 `.py` 文件变更后约 1 秒会自动重建内核并热更新路由，
**无需重启 8001 进程**。

如果想立即手动触发 8001 重建，可以直接保存任意插件文件，或在 8000 系统口调用：

```bash
curl -X POST http://localhost:8000/admin/kernel/reload/{plugin_name}
```

> 该管理接口仍会刷新 8000 系统口的容器，而 8001 服务口会通过文件监听自动同步感知变更。

### Q7: 8000 和 8001 端口有什么区别？

| 端口 | 进程 | 用途 | 访问方 | 热更新方式 |
|------|------|------|--------|------------|
| 8000 | System Server | 管理接口、作弊纸、健康检查 | 平台自身前端 / 管理员 | `/admin/kernel/reload` |
| 8001 | Service Server | 业务 API（/api/*） | 外部调用方 / 客户 | `watchdog` 自动监听热更新 |

两者作为独立进程运行，互不干扰。8001 服务口支持真正的插件热拔插：新增、修改、删除 `plugins/` 下的模块后无需重启即可生效。

---

## 作者

本项目用于毕业设计研究，探索 AI 驱动的模块化 PaaS 平台构建方法。
