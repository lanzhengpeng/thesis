"""
LangGraph Agent 工作流
=====================

接收自然语言任务，通过 LangGraph 状态图生成符合 CSM 规范的插件模块，
完成静态检查后自动重载内核。

所有文件操作均通过 agent_tools.py 进行沙箱校验，禁止越权写入 plugins/ 之外。
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, TypedDict

try:
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI
except ImportError:  # pragma: no cover
    SystemMessage = None  # type: ignore
    HumanMessage = None  # type: ignore
    ChatOpenAI = None  # type: ignore

from langgraph.graph import END, StateGraph

from paas_core.kernel.microkernel import MicroKernel
from paas_core.server.route_bridge import summarize_report

from . import agent_tools


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

DEFAULT_API_KEY = "qwe"
DEFAULT_BASE_URL = "http://112.132.229.234:8030/v1"
DEFAULT_MODEL = "DeepSeek-R1-Distill-Qwen-671B"


# ---------------------------------------------------------------------------
# 状态定义
# ---------------------------------------------------------------------------


class AgentState(TypedDict, total=False):
    """
    LangGraph 工作流状态。

    字段说明：
        task: 用户输入的自然语言任务。
        module_name: 提取出的插件模块名（snake_case）。
        plan: LLM 或回退生成的文件计划。
        files: 文件名 -> 文件内容的代码字典。
        written: 成功写入磁盘的文件名列表。
        checks: 每个文件的 static_check 结果。
        reload_report: 内核重载后的简要报告。
        status: 当前步骤状态。
        logs: 执行日志。
        result: 最终返回给调用方的结果字典。
    """

    task: str
    module_name: str
    plan: Dict[str, Any]
    files: Dict[str, str]
    written: List[str]
    checks: Dict[str, Any]
    reload_report: Dict[str, Any]
    status: str
    logs: List[str]
    result: Dict[str, Any]


# ---------------------------------------------------------------------------
# LLM 客户端
# ---------------------------------------------------------------------------


def _get_llm() -> Optional[Any]:
    """
    初始化可选的 LLM 客户端。

    配置来源（优先级从高到低）：
    1. 环境变量 OPENAI_API_KEY / OPENAI_BASE_URL / AGENT_MODEL。
    2. 默认值，与 test_api.ipynb 中的本地接口一致。

    若 langchain-openai 未安装或初始化失败，返回 None，后续使用确定性回退。
    """
    if ChatOpenAI is None:
        return None

    api_key = os.getenv("OPENAI_API_KEY", DEFAULT_API_KEY)
    base_url = os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL)
    model = os.getenv("AGENT_MODEL", DEFAULT_MODEL)

    try:
        return ChatOpenAI(
            openai_api_key=api_key,
            openai_api_base=base_url,
            model=model,
            temperature=0.2,
            max_tokens=4096,
        )
    except Exception as exc:  # pragma: no cover
        print(f"[Agent] LLM 初始化失败: {exc}")
        return None


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _normalize_module_name(name: str) -> str:
    """统一模块名后缀为 _module，符合项目命名约定。"""
    if not name.endswith("_module"):
        name = f"{name}_module"
    return name


def _is_valid_module_name(name: str) -> bool:
    """判断是否为合法的 Python 标识符且非保留字。"""
    if not name or not name.isidentifier():
        return False
    import keyword

    return not keyword.iskeyword(name)


def _snake_to_camel(name: str) -> str:
    """将 snake_case 转为 CamelCase。"""
    return "".join(part.capitalize() for part in name.split("_") if part)


def _camel_to_snake(name: str) -> str:
    """将 CamelCase 转为 snake_case。"""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _pluralize(word: str) -> str:
    """极简复数化：末尾非 s 则加 s。"""
    if word.endswith("s"):
        return word
    return f"{word}s"


def _module_prefix(module_name: str) -> str:
    """从模块名推断业务前缀，例如 user_module -> User。"""
    raw = module_name
    if raw.endswith("_module"):
        raw = raw[: -len("_module")]
    if not raw:
        raw = "agent"
    return _snake_to_camel(raw)


def _fallback_module_name(task: str) -> str:
    """确定性模块名提取。"""
    if "用户" in task:
        return "user_module"
    if "订单" in task:
        return "order_module"
    return _normalize_module_name("agent_demo")


def _fallback_plan(module_name: str) -> Dict[str, str]:
    """确定性文件计划。"""
    prefix = _module_prefix(module_name)
    return {
        "mapper": f"{prefix}Mapper",
        "service": f"{prefix}Service",
        "controller": f"{prefix}Controller",
        "api_prefix": f"/api/{_pluralize(prefix.lower())}",
    }


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """从模型输出中提取最外层 JSON 对象。"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    for i in range(start, len(text)):
        char = text[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


# ---------------------------------------------------------------------------
# 代码模板
# ---------------------------------------------------------------------------


def _render_mapper(class_name: str) -> str:
    """渲染 Mapper 模板。"""
    return f'''from paas_core import Mapper


@Mapper
class {class_name}:
    def __init__(self):
        self._items = {{}}
        self._next_id = 1

    def create(self, **kwargs) -> dict:
        item_id = self._next_id
        self._next_id += 1
        item = {{"id": item_id, **kwargs}}
        self._items[item_id] = item
        return item

    def get(self, item_id: int) -> dict | None:
        return self._items.get(item_id)

    def list_all(self) -> list:
        return list(self._items.values())
'''


def _render_service(class_name: str, mapper_name: str) -> str:
    """渲染 Service 模板。"""
    mapper_var = _camel_to_snake(mapper_name)
    return f'''from paas_core import Service
from .{mapper_name} import {mapper_name}


@Service
class {class_name}:
    def __init__(self, {mapper_var}: {mapper_name}):
        self.{mapper_var} = {mapper_var}

    def create(self, **kwargs) -> dict:
        return self.{mapper_var}.create(**kwargs)

    def get(self, item_id: int) -> dict | None:
        return self.{mapper_var}.get(item_id)

    def list_all(self) -> list:
        return self.{mapper_var}.list_all()
'''


def _render_controller(class_name: str, service_name: str, api_prefix: str) -> str:
    """渲染 Controller 模板。"""
    service_var = _camel_to_snake(service_name)
    return f'''from paas_core import Controller, GET, POST
from .{service_name} import {service_name}


@Controller("{api_prefix}")
class {class_name}:
    def __init__(self, {service_var}: {service_name}):
        self.{service_var} = {service_var}

    @GET("/")
    def list_items(self):
        return self.{service_var}.list_all()

    @GET("/{{item_id}}")
    def get_item(self, item_id: str):
        item = self.{service_var}.get(int(item_id))
        if item is None:
            return {{"error": "not found"}}
        return item

    @POST("/")
    def create_item(self, payload: dict):
        return self.{service_var}.create(**payload)
'''


def _fallback_generate(module_name: str, plan: Dict[str, Any]) -> Dict[str, str]:
    """确定性代码生成。"""
    mapper = plan.get("mapper", f"{_module_prefix(module_name)}Mapper")
    service = plan.get("service", f"{_module_prefix(module_name)}Service")
    controller = plan.get("controller", f"{_module_prefix(module_name)}Controller")
    api_prefix = plan.get("api_prefix", f"/api/{_pluralize(_module_prefix(module_name).lower())}")

    return {
        f"{mapper}.py": _render_mapper(mapper),
        f"{service}.py": _render_service(service, mapper),
        f"{controller}.py": _render_controller(controller, service, api_prefix),
    }


# ---------------------------------------------------------------------------
# LLM 节点辅助函数
# ---------------------------------------------------------------------------


def _plan_with_llm(task: str, module_name: str) -> Optional[Dict[str, str]]:
    """使用 LLM 生成文件计划。"""
    llm = _get_llm()
    if llm is None or SystemMessage is None or HumanMessage is None:
        return None

    prompt = f"""请为以下任务生成 PaaS 插件模块的代码文件计划。

任务：{task}
模块名：{module_name}

请只返回如下 JSON 对象，不要包含解释或 markdown：
{{
  "mapper": "UserMapper",
  "service": "UserService",
  "controller": "UserController",
  "api_prefix": "/api/users"
}}
"""
    try:
        resp = llm.invoke([SystemMessage(content="你是一个 PaaS 模块设计助手。"), HumanMessage(content=prompt)])
        data = _extract_json(resp.content)
        if not data:
            return None
        plan = {
            "mapper": data.get("mapper", ""),
            "service": data.get("service", ""),
            "controller": data.get("controller", ""),
            "api_prefix": data.get("api_prefix", ""),
        }
        if all(plan.values()):
            return plan
    except Exception as exc:  # pragma: no cover
        print(f"[Agent] LLM 计划生成失败: {exc}")
    return None


def _generate_code_with_llm(task: str, module_name: str, plan: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """使用 LLM 生成具体代码文件。"""
    llm = _get_llm()
    if llm is None or SystemMessage is None or HumanMessage is None:
        return None

    prompt = f"""请根据以下任务和文件计划，生成一个符合 CSM 三层架构的 PaaS 插件模块代码。

任务：{task}
模块名：{module_name}
文件计划：
- Mapper: {plan.get('mapper')}
- Service: {plan.get('service')}
- Controller: {plan.get('controller')}
- API 前缀: {plan.get('api_prefix')}

要求：
1. Mapper 类必须加 `@Mapper`，Service 类必须加 `@Service`，Controller 类必须加 `@Controller`。
2. Mapper 使用内存字典存储，提供 create / get / list_all 方法。
3. Service 必须通过 `def __init__(self, xxx_mapper: XxxMapper)` 注入 Mapper，并将依赖保存到 `self.xxx_mapper`。
4. Controller 必须通过 `def __init__(self, xxx_service: XxxService)` 注入 Service，并将依赖保存到 `self.xxx_service`。
5. Controller 使用 paas_core 的 @GET、@POST 装饰器；方法路径必须是相对路径且以 `/` 开头，例如 `@GET("/")`、`@GET("/{{item_id}}")`、`@POST("/")`。GET 方法只能有路径参数，不能有 `payload` 参数；POST 方法签名为 `def method(self, payload: dict)`。
6. 代码中只导入 paas_core 和本模块内的相对模块，禁止导入 os / sys / subprocess / socket。

请只返回如下 JSON 对象（键为文件名，值为完整代码字符串），不要包含解释：
{{
  "{plan.get('mapper')}.py": "...",
  "{plan.get('service')}.py": "...",
  "{plan.get('controller')}.py": "..."
}}
"""
    try:
        resp = llm.invoke([SystemMessage(content="你是一个 Python 后端代码生成助手。"), HumanMessage(content=prompt)])
        data = _extract_json(resp.content)
        if not data or "files" not in data:
            return data
        return data.get("files")
    except Exception as exc:  # pragma: no cover
        print(f"[Agent] LLM 代码生成失败: {exc}")
    return None


# ---------------------------------------------------------------------------
# LangGraph 节点
# ---------------------------------------------------------------------------


def _node_parse(state: AgentState, kernel: MicroKernel) -> Dict[str, Any]:
    """解析任务，提取模块名。"""
    task = state.get("task", "")
    logs = list(state.get("logs", []))
    module_name = ""

    llm = _get_llm()
    if llm and SystemMessage and HumanMessage:
        try:
            resp = llm.invoke(
                [
                    SystemMessage(content="请从用户任务中提取一个 snake_case 的 Python 模块名，只返回模块名，不要解释。"),
                    HumanMessage(content=f"任务：{task}"),
                ]
            )
            candidate = resp.content.strip().lower().replace(" ", "_").replace("-", "_")
            candidate = re.sub(r"[^a-z0-9_]", "", candidate)
            candidate = _normalize_module_name(candidate)
            if _is_valid_module_name(candidate):
                module_name = candidate
                logs.append(f"LLM 提取模块名: {module_name}")
        except Exception as exc:
            logs.append(f"LLM 提取模块名失败: {exc}")

    if not module_name:
        module_name = _fallback_module_name(task)
        logs.append(f"回退提取模块名: {module_name}")

    return {"module_name": module_name, "logs": logs}


def _node_plan(state: AgentState, kernel: MicroKernel) -> Dict[str, Any]:
    """生成文件计划。"""
    task = state.get("task", "")
    module_name = state.get("module_name", "")
    logs = list(state.get("logs", []))

    plan = _plan_with_llm(task, module_name) or _fallback_plan(module_name)
    logs.append(f"生成计划: {plan}")
    return {"plan": plan, "logs": logs}


def _is_valid_generated_files(files: Dict[str, str], plan: Dict[str, Any]) -> bool:
    """校验 LLM 生成的代码是否满足 CSM 装配约定。"""
    if not files or len(files) < 3:
        return False

    mapper_file = next((f for f in files if f.endswith("Mapper.py")), None)
    service_file = next((f for f in files if f.endswith("Service.py")), None)
    controller_file = next((f for f in files if f.endswith("Controller.py")), None)

    if not all([mapper_file, service_file, controller_file]):
        return False

    mapper_class = plan.get("mapper", "")
    service_class = plan.get("service", "")

    if "@Mapper" not in files[mapper_file]:
        return False
    if "@Service" not in files[service_file]:
        return False
    if "@Controller" not in files[controller_file]:
        return False

    # Controller 必须带基础路径参数，例如 @Controller("/api/comments")
    if not re.search(r"@Controller\s*\(\s*[\"']", files[controller_file]):
        return False

    # Service / Controller 必须提供 __init__ 构造参数注入
    if "def __init__(" not in files[service_file]:
        return False
    if "def __init__(" not in files[controller_file]:
        return False

    # Service 必须注入 Mapper；Controller 必须注入 Service
    if service_class not in files[service_file]:
        return False
    if service_class not in files[controller_file]:
        return False

    # 方法级路由应为相对路径，不能再次包含 /api/ 前缀，也不能为空
    method_decorators = list(re.finditer(r"@(GET|POST|PUT|PATCH|DELETE)\s*\(\s*[\"'](.*?)[\"']\s*\)", files[controller_file]))
    if not method_decorators:
        return False
    for m in method_decorators:
        http_method = m.group(1)
        method_path = m.group(2)
        if not method_path.startswith("/") or method_path.startswith("/api/"):
            return False
        subsequent = files[controller_file][m.end() :]
        def_match = re.search(r"def\s+\w+\s*\((.*?)\):", subsequent, re.DOTALL)
        if not def_match:
            return False
        params = def_match.group(1)
        if http_method == "GET" and "payload" in params:
            return False

    return True


def _node_generate(state: AgentState, kernel: MicroKernel) -> Dict[str, Any]:
    """生成代码文件。"""
    task = state.get("task", "")
    module_name = state.get("module_name", "")
    plan = state.get("plan", {})
    logs = list(state.get("logs", []))

    files = _generate_code_with_llm(task, module_name, plan)
    if not _is_valid_generated_files(files, plan):
        logs.append("LLM 代码未满足 CSM 装配约束或解析失败，使用确定性模板")
        files = _fallback_generate(module_name, plan)
    else:
        logs.append(f"LLM 生成文件: {list(files.keys())}")

    return {"files": files, "logs": logs}


def _node_write(state: AgentState, kernel: MicroKernel) -> Dict[str, Any]:
    """将代码写入 plugins/ 沙箱。"""
    module_name = state.get("module_name", "")
    files = state.get("files", {})
    logs = list(state.get("logs", []))

    try:
        agent_tools.create_plugin(module_name)
        logs.append(f"创建插件目录: {module_name}")
    except agent_tools.AgentSandboxError as exc:
        logs.append(f"创建插件目录失败: {exc}")
        return {"status": "write_failed", "logs": logs}

    written: List[str] = []
    for file_name, content in files.items():
        try:
            agent_tools.write_plugin_file(module_name, file_name, content)
            written.append(file_name)
        except Exception as exc:
            logs.append(f"写入 {file_name} 失败: {exc}")

    status = "written" if len(written) == len(files) else "write_failed"
    logs.append(f"成功写入文件: {written}")
    return {"written": written, "status": status, "logs": logs}


def _node_check(state: AgentState, kernel: MicroKernel) -> Dict[str, Any]:
    """对生成的文件执行静态安全检查。"""
    module_name = state.get("module_name", "")
    files = state.get("files", {})
    logs = list(state.get("logs", []))

    checks: Dict[str, Any] = {}
    all_ok = True
    for file_name in files:
        result = agent_tools.static_check(module_name, file_name)
        checks[file_name] = result
        if not result.get("ok"):
            all_ok = False
            logs.append(f"静态检查失败 {file_name}: {result.get('errors')}")

    if all_ok:
        logs.append("静态检查通过")

    status = "ready" if all_ok else "static_check_failed"
    return {"checks": checks, "status": status, "logs": logs}


def _node_reload(state: AgentState, kernel: MicroKernel) -> Dict[str, Any]:
    """重新加载插件，使系统口容器生效。"""
    module_name = state.get("module_name", "")
    logs = list(state.get("logs", []))

    try:
        report = kernel.reload_plugin(module_name)
        summary = summarize_report(report)
        logs.append(f"内核重载成功: {summary}")
        return {"reload_report": summary, "status": "deployed", "logs": logs}
    except Exception as exc:
        logs.append(f"内核重载失败: {exc}")
        return {"reload_report": {"error": str(exc)}, "status": "reload_failed", "logs": logs}


def _node_finalize(state: AgentState, kernel: MicroKernel) -> Dict[str, Any]:
    """整理最终响应。"""
    result = {
        "task": state.get("task", ""),
        "module_name": state.get("module_name", ""),
        "status": state.get("status", "unknown"),
        "files": list(state.get("files", {}).keys()),
        "written": state.get("written", []),
        "checks": state.get("checks", {}),
        "reload_report": state.get("reload_report", {}),
        "logs": state.get("logs", []),
    }
    return {"result": result}


def _after_check(state: AgentState) -> str:
    """静态检查后的路由判断。"""
    if state.get("status") == "ready":
        return "reload"
    return "finalize"


# ---------------------------------------------------------------------------
# 图构建与入口
# ---------------------------------------------------------------------------


def build_agent_graph(kernel: MicroKernel) -> Any:
    """
    构建并编译 LangGraph 工作流。

    参数：
        kernel: 当前微内核实例，用于重载插件。

    返回：
        编译后的 StateGraph 可调用对象。
    """
    builder = StateGraph(AgentState)

    builder.add_node("parse", lambda state: _node_parse(state, kernel))
    builder.add_node("plan", lambda state: _node_plan(state, kernel))
    builder.add_node("generate", lambda state: _node_generate(state, kernel))
    builder.add_node("write", lambda state: _node_write(state, kernel))
    builder.add_node("check", lambda state: _node_check(state, kernel))
    builder.add_node("reload", lambda state: _node_reload(state, kernel))
    builder.add_node("finalize", lambda state: _node_finalize(state, kernel))

    builder.set_entry_point("parse")
    builder.add_edge("parse", "plan")
    builder.add_edge("plan", "generate")
    builder.add_edge("generate", "write")
    builder.add_edge("write", "check")
    builder.add_conditional_edges("check", _after_check, {"reload": "reload", "finalize": "finalize"})
    builder.add_edge("reload", "finalize")
    builder.add_edge("finalize", END)

    return builder.compile()


def run_agent_task(kernel: MicroKernel, task: str) -> Dict[str, Any]:
    """
    执行一次 agent 任务。

    参数：
        kernel: 微内核实例。
        task: 自然语言任务，例如 "创建用户模块"。

    返回：
        包含生成结果、状态、日志的字典。
    """
    graph = build_agent_graph(kernel)
    initial_state: AgentState = {
        "task": task,
        "module_name": "",
        "plan": {},
        "files": {},
        "written": [],
        "checks": {},
        "reload_report": {},
        "status": "pending",
        "logs": [],
    }
    final_state = graph.invoke(initial_state)
    return final_state.get("result", final_state)
