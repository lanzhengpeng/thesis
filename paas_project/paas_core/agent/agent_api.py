"""
Agent 管理接口
=============

在系统口（8000）暴露 LangGraph agent 相关端点。

本模块同时提供：
1. 新的多智能体会话 API（/admin/agent/sessions/*）。
2. 旧的单步生成接口（/admin/agent/generate），内部复用新流水线。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from paas_core.kernel.microkernel import MicroKernel

from .agents.requirements_agent import _default_requirements_doc, _extract_module_name
from .pipeline import stream_pipeline
from .session_api import create_session_router
from .session_store import create_session, update_session


class AgentTaskRequest(BaseModel):
    """Agent 任务请求体。"""

    task: str


class AgentTaskResponse(BaseModel):
    """Agent 任务响应体。"""

    task: str
    module_name: str
    status: str
    files: list
    written: list
    checks: dict
    reload_report: dict
    logs: list


def create_agent_router(kernel: MicroKernel) -> APIRouter:
    """
    创建 agent 路由。

    参数：
        kernel: 已启动的微内核实例。

    返回：
        配置好的 FastAPI APIRouter。
    """
    router = APIRouter(tags=["agent"])

    # 挂载新的会话路由
    router.include_router(create_session_router(kernel))

    @router.post("/generate")
    async def generate(req: AgentTaskRequest):
        """
        接收自然语言任务，由多智能体流水线生成并部署插件模块。

        请求体：
            {"task": "创建用户模块"}

        返回：
            SSE 流（media_type="text/event-stream"）。流中包括：
            - 大模型输出块（打字机效果）
            - 工具开始执行的 Markdown 提示
            - 流水线结束后的 JSON 总结
        """
        if not req.task or not req.task.strip():
            raise HTTPException(status_code=400, detail="task 不能为空")

        task = req.task.strip()
        # 构造一个自动确认的需求文档，复用新流水线
        module_name = _extract_module_name(task)
        requirements_doc = _default_requirements_doc(task)
        requirements_doc["module_name"] = module_name
        requirements_doc["confirmed"] = True

        session_id = create_session(task)
        update_session(
            session_id,
            status="generating",
            requirements_doc=requirements_doc,
            logs=[f"旧接口直接生成，任务: {task}"],
        )

        return StreamingResponse(
            stream_pipeline(kernel, session_id, task, requirements_doc),
            media_type="text/event-stream",
        )

    return router
