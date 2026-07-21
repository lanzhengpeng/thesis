"""
多智能体 LangGraph 流水线
=========================

编排 4 个智能体：
    requirements → architect → generator → reviewer → finalize

需求分析阶段由外部 API 驱动多轮问答，流水线内部仅做最终确认；
确认后依次完成架构设计、代码生成、审查部署。
"""

from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, StateGraph

from paas_core.kernel.microkernel import MicroKernel

from .agents import (
    run_architect_node,
    run_generator_node,
    run_requirements_node,
    run_reviewer_deployer_node,
)
from .schemas import PipelineState


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
