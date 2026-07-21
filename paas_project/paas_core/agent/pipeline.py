"""
多智能体 LangGraph 流水线
=========================

编排 4 个智能体：
    requirements → architect → generator → reviewer → finalize

需求分析阶段由外部 API 驱动多轮问答，流水线内部仅做最终确认；
确认后依次完成架构设计、代码生成、审查部署。
"""

from __future__ import annotations

import uuid
from typing import Any, AsyncIterator, Dict, Optional

from langgraph.graph import END, StateGraph

from paas_core.kernel.microkernel import MicroKernel

from .agents import (
    run_architect_node,
    run_generator_node,
    run_requirements_node,
    run_reviewer_deployer_node,
)
from .formatting import format_pipeline_markdown, sse_text_frame, stream_text_chunks
from .schemas import PipelineState, wrap_agent_event
from .session_store import update_session


_STEP_TITLES = {
    "requirements": "确认需求",
    "architect": "设计模块架构",
    "generator": "生成 CSM 代码",
    "reviewer": "审查与部署模块",
    "finalize": "整理生成结果",
}


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

    - ``on_chain_start`` / ``on_chain_end``: 向前端发送步骤事件与 Markdown 进度文案。
    - ``on_tool_start``: 向前端发送工具执行提示。
    - ``on_tool_end``: 不推送，工具结果保留在 LangGraph 状态流中供后续节点使用。
    - 流水线结束后：先以字符对分块流式推送最终 Markdown 摘要，再推送 ``pipeline_result`` 结构化事件。

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

    yield sse_text_frame("收到，我开始生成模块...\n")

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
                if name == "architect":
                    arch = output.get("architecture_doc") or {}
                    detail = f"模块名: {arch.get('module_name', '')}, API 前缀: {arch.get('api_prefix', '')}"
                elif name == "generator":
                    files = output.get("files") or {}
                    detail = f"生成文件: {', '.join(files.keys())}"
                elif name == "reviewer":
                    status = output.get("status", "")
                    written = output.get("written") or []
                    detail = f"状态: {status}"
                    if written:
                        detail += f", 写入: {', '.join(written)}"
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
                # 工具结果已通过 LangGraph 状态流转到后续节点，无需再发给前端。
                pass

            elif event_type == "on_chat_model_stream":
                # 模块生成流水线的模型输出（架构 JSON、代码片段等）不适合直接作为聊天文本展示，
                # 避免把 call_graph、脏 JSON 等内部数据暴露给用户。进度感知通过 agent_step 实现。
                pass

            elif event_type == "on_chain_end" and name == "finalize":
                output = event.get("data", {}).get("output", {})
                final_result = output.get("result", {})
    except Exception as exc:  # pragma: no cover
        error_message = str(exc)
        yield f"data: {wrap_agent_event('agent_step', {
            'id': 'step-error',
            'status': 'error',
            'title': '流水线执行出错',
            'detail': error_message,
        })}\n\n"

    if error_message:
        update_session(
            session_id,
            status="stream_failed",
            logs=[f"流式执行失败: {error_message}"],
        )
        yield sse_text_frame(f"❌ **流水线执行出错**：{error_message}\n")
        yield f"data: {wrap_agent_event('pipeline_result', {'status': 'stream_failed', 'error': error_message})}\n\n"
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
        summary = format_pipeline_markdown(final_result, title="模块生成完成")
        async for frame in stream_text_chunks(summary, chunk_size=2, delay=0.002):
            yield frame
        yield f"data: {wrap_agent_event('pipeline_result', final_result)}\n\n"
