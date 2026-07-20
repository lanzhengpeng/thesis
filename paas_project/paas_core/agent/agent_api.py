"""
Agent 管理接口
=============

在系统口（8000）暴露 LangGraph agent 相关端点。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from paas_core.kernel.microkernel import MicroKernel

from .agent_module import run_agent_task


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

    @router.post("/generate")
    def generate(req: AgentTaskRequest):
        """
        接收自然语言任务，由 LangGraph agent 生成并部署插件模块。

        请求体：
            {"task": "创建用户模块"}

        返回：
            生成结果、文件列表、静态检查结果、内核重载报告及执行日志。
        """
        if not req.task or not req.task.strip():
            raise HTTPException(status_code=400, detail="task 不能为空")

        result = run_agent_task(kernel, req.task.strip())
        return result

    return router
