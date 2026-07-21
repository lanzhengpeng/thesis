"""
Agent 管理接口
=============

在系统口（8000）暴露 LangGraph agent 相关端点。

本模块同时提供：
1. 新的多智能体会话 API（/admin/agent/sessions/*）。
2. 旧的单步生成接口（/admin/agent/generate），内部复用新流水线。
"""

from __future__ import annotations

from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from paas_core.kernel.microkernel import MicroKernel

from .agents.requirements_agent import _default_requirements_doc, _extract_module_name, generate_first_questions
from .llm_utils import GENERAL_CHAT_SYSTEM_PROMPT, classify_intent, stream_llm_text
from .pipeline import stream_pipeline
from .repair_pipeline import stream_repair_pipeline
from .schemas import wrap_agent_event
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


class ChatRequest(BaseModel):
    """通用智能体聊天请求体。"""

    message: str


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
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @router.post("/chat")
    async def chat(req: ChatRequest):
        """
        通用智能体统一入口：先做意图识别，再分发到通用问答或多轮需求流程。

        请求体：
            {"message": "你好"}

        返回：
            SSE 流（media_type="text/event-stream"）。
            - 通用问答：直接返回大模型文本流。
            - 模块生成任务：返回一条带标记的自定义事件
              `<<<AGENT_EVENT|{"type": "requirements_gathering", ...}|AGENT_EVENT>>>`，
              前端识别后切换为需求收集模式。
        """
        if not req.message or not req.message.strip():
            raise HTTPException(status_code=400, detail="message 不能为空")

        message = req.message.strip()
        intent = classify_intent(message)

        if intent == "module_generation":
            result = generate_first_questions(message)
            questions = result.get("questions") or []
            requirements_doc = result.get("requirements_doc") or _default_requirements_doc(message)
            confirmed = bool(result.get("confirmed"))
            if confirmed:
                requirements_doc["confirmed"] = True

            session_id = create_session(message, questions)
            update_session(
                session_id,
                questions=questions,
                requirements_doc=requirements_doc,
                status="requirements_confirmed" if confirmed else "requirements_gathering",
                logs=[f"意图识别为模块生成，创建会话，任务: {message}"],
            )

            async def requirements_event_stream() -> AsyncIterator[str]:
                yield "data: 好的，我先来确认一下需求细节。\n\n"
                payload = {
                    "session_id": session_id,
                    "task": message,
                    "questions": questions,
                    "requirements_doc": requirements_doc,
                }
                yield f"data: {wrap_agent_event('requirements_gathering', payload)}\n\n"

            return StreamingResponse(
                requirements_event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        if intent == "module_modification":
            session_id = create_session(message)
            update_session(
                session_id,
                status="repairing",
                logs=[f"意图识别为模块修复，创建会话，任务: {message}"],
            )

            return StreamingResponse(
                stream_repair_pipeline(kernel, session_id, message),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        # 通用问答：流式调用大模型
        async def general_chat_stream() -> AsyncIterator[str]:
            async for chunk in stream_llm_text(GENERAL_CHAT_SYSTEM_PROMPT, message):
                yield f"data: {chunk}\n\n"

        return StreamingResponse(
            general_chat_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return router
