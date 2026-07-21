"""
模块修复流水线
==============

用于让 agent 真正“修改”已有插件模块，而不是盲目生成新模块覆盖。

流程：
    parse → read → modify → validate → write → check → reload → finalize
"""

from __future__ import annotations

import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

from langgraph.graph import END, StateGraph

from paas_core.kernel.microkernel import MicroKernel

from .agents.requirements_agent import _extract_module_name, _normalize_module_name
from .formatting import format_pipeline_markdown, sse_text_frame, stream_text_chunks
from .llm_utils import invoke_json
from .locks import plugin_write_lock
from .prompts import MODULE_REPAIR_SYSTEM_PROMPT, module_repair_prompt
from .schemas import PipelineState, wrap_agent_event
from .session_store import update_session
from paas_core.server.route_bridge import summarize_report

from . import agent_tools
from .agents.reviewer_deployer_agent import _validate_files


class RepairState(PipelineState, total=False):
    """修复流水线特有状态字段。"""

    module_name: str
    original_files: Dict[str, str]


_STEP_TITLES = {
    "parse": "解析修复任务",
    "read": "读取现有模块文件",
    "modify": "生成修改后的代码",
    "validate": "校验文件格式",
    "write": "写入修改文件",
    "check": "执行静态检查",
    "reload": "重载内核模块",
    "finalize": "整理修复结果",
}


def _node_parse(state: RepairState, kernel: MicroKernel) -> Dict[str, Any]:
    """解析任务，确认目标模块存在。"""
    logs = list(state.get("logs", []))
    task = state.get("task", "")

    module_name = _extract_module_name(task)
    module_name = _normalize_module_name(module_name)

    if not module_name:
        logs.append("无法从任务中提取模块名")
        return {"status": "parse_failed", "logs": logs}

    existing_plugins = agent_tools.list_plugins()
    if module_name not in existing_plugins:
        logs.append(f"模块 {module_name} 不存在，无法修复")
        return {"status": "module_not_found", "module_name": module_name, "logs": logs}

    logs.append(f"识别为模块修复任务，目标模块: {module_name}")
    return {
        "module_name": module_name,
        "status": "parse_ok",
        "logs": logs,
    }


def _node_read(state: RepairState, kernel: MicroKernel) -> Dict[str, Any]:
    """读取模块现有文件内容。"""
    logs = list(state.get("logs", []))
    module_name = state.get("module_name", "")

    try:
        files = agent_tools.list_plugin_files(module_name)
        original_files: Dict[str, str] = {}
        for file_name in files:
            original_files[file_name] = agent_tools.read_plugin_file(module_name, file_name)
        logs.append(f"读取到 {len(original_files)} 个现有文件: {list(original_files.keys())}")
        return {
            "original_files": original_files,
            "status": "read_ok",
            "logs": logs,
        }
    except agent_tools.AgentSandboxError as exc:
        logs.append(f"读取文件失败: {exc}")
        return {"status": "read_failed", "logs": logs}


def _node_modify(state: RepairState, kernel: MicroKernel) -> Dict[str, Any]:
    """调用 LLM 按任务要求修改现有文件。"""
    logs = list(state.get("logs", []))
    task = state.get("task", "")
    module_name = state.get("module_name", "")
    original_files = state.get("original_files", {})

    if not original_files:
        logs.append("没有现有文件可供修改")
        return {"status": "modify_failed", "logs": logs}

    data = invoke_json(
        MODULE_REPAIR_SYSTEM_PROMPT,
        module_repair_prompt(task, module_name, original_files),
        timeout=60,
    )

    files: Dict[str, str] = {}
    if data:
        candidate = data.get("files") or data
        if candidate and isinstance(candidate, dict):
            files = {k: v for k, v in candidate.items() if isinstance(v, str)}

    if not files:
        logs.append("LLM 未返回有效文件内容")
        return {"status": "modify_failed", "logs": logs}

    logs.append(f"LLM 生成修改后的文件: {list(files.keys())}")
    return {
        "files": files,
        "status": "modify_ok",
        "logs": logs,
    }


def _node_validate(state: RepairState, kernel: MicroKernel) -> Dict[str, Any]:
    """校验修改后的文件是否仍满足 CSM 装配约定。"""
    logs = list(state.get("logs", []))
    files = state.get("files", {})

    issues = _validate_files(files)
    if issues:
        logs.append(f"格式校验失败: {issues}")
        return {
            "status": "validation_failed",
            "checks": {"format": {"ok": False, "errors": issues}},
            "logs": logs,
        }

    logs.append("格式校验通过")
    return {"status": "validation_ok", "logs": logs}


def _node_write(state: RepairState, kernel: MicroKernel) -> Dict[str, Any]:
    """将修改后的文件写回沙箱。"""
    logs = list(state.get("logs", []))
    files = state.get("files", {})
    module_name = state.get("module_name", "")

    written: List[str] = []
    try:
        for file_name, content in files.items():
            agent_tools.write_plugin_file(module_name, file_name, content)
            written.append(file_name)
        logs.append(f"成功写入文件: {written}")
        return {"written": written, "status": "write_ok", "logs": logs}
    except agent_tools.AgentSandboxError as exc:
        logs.append(f"写入失败: {exc}")
        return {"status": "write_failed", "written": written, "logs": logs}


def _node_check(state: RepairState, kernel: MicroKernel) -> Dict[str, Any]:
    """对写入后的文件执行静态检查。"""
    logs = list(state.get("logs", []))
    files = state.get("files", {})
    module_name = state.get("module_name", "")

    checks: Dict[str, Any] = {}
    all_ok = True
    for file_name in files:
        result = agent_tools.static_check(module_name, file_name)
        checks[file_name] = result
        if not result.get("ok"):
            all_ok = False
            logs.append(f"静态检查失败 {file_name}: {result.get('errors')}")

    if not all_ok:
        return {
            "status": "static_check_failed",
            "checks": checks,
            "logs": logs,
        }

    logs.append("静态检查通过")
    return {"checks": checks, "status": "check_ok", "logs": logs}


def _node_reload(state: RepairState, kernel: MicroKernel) -> Dict[str, Any]:
    """重新加载模块。

    为避免单插件 reload 破坏跨模块依赖（其他模块可能仍引用旧类对象），
    这里使用完整内核重启，确保所有依赖重新解析。
    """
    logs = list(state.get("logs", []))

    try:
        report = kernel.reboot()
        summary = summarize_report(report)
        logs.append(f"内核重启成功: {summary}")
        return {
            "status": "deployed",
            "reload_report": summary,
            "logs": logs,
        }
    except Exception as exc:  # pragma: no cover
        logs.append(f"内核重启失败: {exc}")
        return {
            "status": "reload_failed",
            "reload_report": {"error": str(exc)},
            "logs": logs,
        }


def _node_finalize(state: RepairState, kernel: MicroKernel) -> Dict[str, Any]:
    """整理最终响应。"""
    result = {
        "session_id": state.get("session_id", ""),
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


def _after_parse(state: RepairState) -> str:
    status = state.get("status", "")
    if status == "parse_ok":
        return "read"
    return "finalize"


def _after_read(state: RepairState) -> str:
    status = state.get("status", "")
    if status == "read_ok":
        return "modify"
    return "finalize"


def _after_modify(state: RepairState) -> str:
    status = state.get("status", "")
    if status == "modify_ok":
        return "validate"
    return "finalize"


def _after_validate(state: RepairState) -> str:
    status = state.get("status", "")
    if status == "validation_ok":
        return "write"
    return "finalize"


def _after_write(state: RepairState) -> str:
    status = state.get("status", "")
    if status == "write_ok":
        return "check"
    return "finalize"


def _after_check(state: RepairState) -> str:
    status = state.get("status", "")
    if status == "check_ok":
        return "reload"
    return "finalize"


def _after_reload(state: RepairState) -> str:
    return "finalize"


def build_repair_graph(kernel: MicroKernel) -> Any:
    """构建并编译修复流水线图。"""
    builder = StateGraph(RepairState)

    builder.add_node("parse", lambda state: _node_parse(state, kernel))
    builder.add_node("read", lambda state: _node_read(state, kernel))
    builder.add_node("modify", lambda state: _node_modify(state, kernel))
    builder.add_node("validate", lambda state: _node_validate(state, kernel))
    builder.add_node("write", lambda state: _node_write(state, kernel))
    builder.add_node("check", lambda state: _node_check(state, kernel))
    builder.add_node("reload", lambda state: _node_reload(state, kernel))
    builder.add_node("finalize", lambda state: _node_finalize(state, kernel))

    builder.set_entry_point("parse")
    builder.add_conditional_edges("parse", _after_parse, {"read": "read", "finalize": "finalize"})
    builder.add_conditional_edges("read", _after_read, {"modify": "modify", "finalize": "finalize"})
    builder.add_conditional_edges("modify", _after_modify, {"validate": "validate", "finalize": "finalize"})
    builder.add_conditional_edges("validate", _after_validate, {"write": "write", "finalize": "finalize"})
    builder.add_conditional_edges("write", _after_write, {"check": "check", "finalize": "finalize"})
    builder.add_conditional_edges("check", _after_check, {"reload": "reload", "finalize": "finalize"})
    builder.add_conditional_edges("reload", _after_reload, {"finalize": "finalize"})
    builder.add_edge("finalize", END)

    return builder.compile()


async def stream_repair_pipeline(
    kernel: MicroKernel,
    session_id: str,
    task: str,
) -> AsyncIterator[str]:
    """
    异步流式执行模块修复流水线，产出 SSE 格式字符串。

    与生成流水线保持相同事件格式，前端无需改动即可消费。
    """
    graph = build_repair_graph(kernel)
    initial_state: RepairState = {
        "session_id": session_id,
        "task": task,
        "status": "pending",
        "requirements_doc": None,
        "architecture_doc": None,
        "files": {},
        "written": [],
        "checks": {},
        "reload_report": {},
        "logs": [f"启动修复流水线，任务: {task}"],
        "result": {},
        "module_name": "",
        "original_files": {},
    }

    final_result: Dict[str, Any] = {}
    error_message: Optional[str] = None

    yield sse_text_frame("收到，我开始修复模块...\n")

    try:
        async for event in graph.astream_events(initial_state, version="v2"):
            event_type = event.get("event")
            name = event.get("name", "")

            if event_type == "on_chain_start" and name in _STEP_TITLES:
                yield f"data: {wrap_agent_event('agent_step', {
                    'id': f'step-{name}',
                    'status': 'running',
                    'title': _STEP_TITLES[name],
                    'detail': '',
                })}\n\n"

            elif event_type == "on_chain_end" and name in _STEP_TITLES:
                detail = ""
                output = event.get("data", {}).get("output", {})
                if name == "modify":
                    files = output.get("files") or {}
                    detail = f"生成文件: {', '.join(files.keys())}"
                elif name == "write":
                    written = output.get("written") or []
                    detail = f"写入: {', '.join(written)}"
                elif name == "reload":
                    report = output.get("reload_report") or {}
                    detail = f"重载结果: {report}"
                yield f"data: {wrap_agent_event('agent_step', {
                    'id': f'step-{name}',
                    'status': 'done',
                    'title': f"{_STEP_TITLES[name]}完成",
                    'detail': detail,
                })}\n\n"
                yield sse_text_frame(f"✅ **{_STEP_TITLES[name]}完成** — {detail}\n")

            elif event_type == "on_tool_start":
                tool_name = event.get("name", "unknown_tool")
                yield f"data: {wrap_agent_event('agent_step', {
                    'id': f'tool-{tool_name}-{uuid.uuid4().hex[:6]}',
                    'status': 'running',
                    'title': f"执行工具: {tool_name}",
                    'detail': '',
                })}\n\n"

            elif event_type == "on_tool_end":
                pass

            elif event_type == "on_chat_model_stream":
                pass

            elif event_type == "on_chain_end" and name == "finalize":
                output = event.get("data", {}).get("output", {})
                final_result = output.get("result", {})
    except Exception as exc:  # pragma: no cover
        error_message = str(exc)
        yield f"data: {wrap_agent_event('agent_step', {
            'id': 'step-error',
            'status': 'error',
            'title': '修复流水线执行出错',
            'detail': error_message,
        })}\n\n"

    if error_message:
        update_session(
            session_id,
            status="stream_failed",
            logs=[f"流式执行失败: {error_message}"],
        )
        yield sse_text_frame(f"❌ **修复流水线执行出错**：{error_message}\n")
        yield f"data: {wrap_agent_event('pipeline_result', {'status': 'stream_failed', 'error': error_message})}\n\n"
        return

    if final_result:
        update_session(
            session_id,
            status=final_result.get("status", "unknown"),
            generated_files=final_result.get("files"),
            written=final_result.get("written"),
            checks=final_result.get("checks"),
            reload_report=final_result.get("reload_report"),
            logs=final_result.get("logs"),
            result=final_result,
        )
        summary = format_pipeline_markdown(final_result, title="模块修复完成")
        async for frame in stream_text_chunks(summary, chunk_size=2, delay=0.002):
            yield frame
        yield f"data: {wrap_agent_event('pipeline_result', final_result)}\n\n"
