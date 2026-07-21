"""
多智能体 LangGraph 流水线
=========================

编排 4 个智能体：
    requirements → architect → generator → reviewer → finalize

需求分析阶段由外部 API 驱动多轮问答，流水线内部仅做最终确认；
确认后依次完成架构设计、代码生成、审查部署。
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, Optional

from langgraph.graph import END, StateGraph

from paas_core.kernel.microkernel import MicroKernel

from .agents import (
    run_architect_node,
    run_generator_node,
    run_requirements_node,
    run_reviewer_deployer_node,
)
from .schemas import PipelineState
from .session_store import update_session


def _node_requirements(state: PipelineState, kernel: MicroKernel) -> Dict[str, Any]:
    """需求确认节点。"""
    return run_requirements_node(state, kernel)


def _node_architect(state: PipelineState, kernel: MicroKernel) -> Dict[str, Any]:
    """架构设计节点。"""
    return run_architect_node(state, kernel)


def _node_generator(state: PipelineState, kernel: MicroKernel) -> Dict[str, Any]:
    """代码生成节点。"""
    return run_generator_node(state, kernel)


def _node_reviewer(state: PipelineState, kernel: MicroKernel) -> Dict[str, Any]:
    """审查部署节点。"""
    return run_reviewer_deployer_node(state, kernel)


def _node_finalize(state: PipelineState, kernel: MicroKernel) -> Dict[str, Any]:
    """整理最终响应。"""
    module_name = state.get("module_name", "")
    if not module_name:
        req = state.get("requirements_doc") or {}
        arch = state.get("architecture_doc") or {}
        module_name = req.get("module_name") or arch.get("module_name") or ""

    result = {
        "session_id": state.get("session_id", ""),
        "task": state.get("task", ""),
        "module_name": module_name,
        "status": state.get("status", "unknown"),
        "files": list(state.get("files", {}).keys()),
        "written": state.get("written", []),
        "checks": state.get("checks", {}),
        "reload_report": state.get("reload_report", {}),
        "logs": state.get("logs", []),
    }
    return {"result": result}


def _after_requirements(state: PipelineState) -> str:
    """需求确认后的路由判断。"""
    status = state.get("status", "")
    if status == "requirements_ready":
        return "architect"
    return "finalize"


def _after_reviewer(state: PipelineState) -> str:
    """审查部署后的路由判断；无论成败都进入 finalize。"""
    return "finalize"


def build_pipeline_graph(kernel: MicroKernel) -> Any:
    """
    构建并编译多智能体流水线。

    参数：
        kernel: 当前微内核实例。

    返回：
        编译后的 StateGraph 可调用对象。
    """
    builder = StateGraph(PipelineState)

    builder.add_node("requirements", lambda state: _node_requirements(state, kernel))
    builder.add_node("architect", lambda state: _node_architect(state, kernel))
    builder.add_node("generator", lambda state: _node_generator(state, kernel))
    builder.add_node("reviewer", lambda state: _node_reviewer(state, kernel))
    builder.add_node("finalize", lambda state: _node_finalize(state, kernel))

    builder.set_entry_point("requirements")
    builder.add_conditional_edges(
        "requirements",
        _after_requirements,
        {"architect": "architect", "finalize": "finalize"},
    )
    builder.add_edge("architect", "generator")
    builder.add_edge("generator", "reviewer")
    builder.add_conditional_edges(
        "reviewer",
        _after_reviewer,
        {"finalize": "finalize"},
    )
    builder.add_edge("finalize", END)

    return builder.compile()


def run_pipeline(
    kernel: MicroKernel,
    session_id: str,
    task: str,
    requirements_doc: Dict[str, Any],
) -> Dict[str, Any]:
    """
    从已确认的需求文档开始执行完整流水线。

    参数：
        kernel: 微内核实例。
        session_id: 会话 ID。
        task: 原始任务。
        requirements_doc: 已确认的需求文档。

    返回：
        包含生成结果、状态、日志的字典。
    """
    graph = build_pipeline_graph(kernel)
    initial_state: PipelineState = {
        "session_id": session_id,
        "task": task,
        "status": "pending",
        "requirements_doc": requirements_doc,
        "architecture_doc": None,
        "files": {},
        "written": [],
        "checks": {},
        "reload_report": {},
        "logs": [f"启动流水线，任务: {task}"],
        "result": {},
    }
    final_state = graph.invoke(initial_state)
    return final_state.get("result", final_state)


async def stream_pipeline(
    kernel: MicroKernel,
    session_id: str,
    task: str,
    requirements_doc: Dict[str, Any],
) -> AsyncIterator[str]:
    """
    异步流式执行多智能体流水线，产出 SSE 格式字符串。

    遍历 ``graph.astream_events(initial_state, version="v2")`` 产生的事件：

    - ``on_chat_model_stream``: 将模型输出块实时推送给前端，实现打字机效果。
    - ``on_tool_start``: 向前端发送 Markdown 引用形式的工具执行提示。
    - ``on_tool_end``: 不推送，工具结果保留在 LangGraph 状态流中供后续节点使用。
    - 流水线结束后：将最终结果写入会话并推送一份 JSON 总结。

    参数：
        kernel: 微内核实例。
        session_id: 会话 ID。
        task: 原始任务。
        requirements_doc: 已确认的需求文档。

    返回：
        异步迭代器，每个元素都是符合 SSE 规范的 ``data: ...\\n\\n`` 字符串。
    """
    graph = build_pipeline_graph(kernel)
    initial_state: PipelineState = {
        "session_id": session_id,
        "task": task,
        "status": "pending",
        "requirements_doc": requirements_doc,
        "architecture_doc": None,
        "files": {},
        "written": [],
        "checks": {},
        "reload_report": {},
        "logs": [f"启动流水线，任务: {task}"],
        "result": {},
    }

    final_result: Dict[str, Any] = {}
    error_message: Optional[str] = None

    try:
        async for event in graph.astream_events(initial_state, version="v2"):
            event_type = event.get("event")
            if event_type == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                text = getattr(chunk, "content", None)
                if text:
                    yield f"data: {text}\n\n"
            elif event_type == "on_tool_start":
                tool_name = event.get("name", "unknown_tool")
                yield f"data: \n> 🛠️ 正在执行: {tool_name}...\n\n"
            elif event_type == "on_tool_end":
                # 工具结果已通过 LangGraph 状态流转到后续节点，无需再发给前端。
                pass
            elif event_type == "on_chain_end" and event.get("name") == "finalize":
                output = event.get("data", {}).get("output", {})
                final_result = output.get("result", {})
    except Exception as exc:  # pragma: no cover
        error_message = str(exc)
        yield f"data: \n> ❌ 流水线执行出错: {exc}\n\n"

    if error_message:
        update_session(
            session_id,
            status="stream_failed",
            logs=[f"流式执行失败: {error_message}"],
        )
        yield f"data: {json.dumps({'status': 'stream_failed', 'error': error_message}, ensure_ascii=False)}\n\n"
        return

    if final_result:
        update_session(
            session_id,
            status=final_result.get("status", "unknown"),
            architecture_doc=final_result.get("architecture_doc"),
            generated_files=final_result.get("files"),
            written=final_result.get("written"),
            checks=final_result.get("checks"),
            reload_report=final_result.get("reload_report"),
            logs=final_result.get("logs"),
            result=final_result,
        )
        yield f"data: {json.dumps(final_result, ensure_ascii=False)}\n\n"
