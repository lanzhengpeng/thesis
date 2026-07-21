"""
智能体会话 API
==============

暴露需求分析会话相关端点，支持多轮问答补全需求，并在确认后触发代码生成流水线。
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from paas_core.kernel.microkernel import MicroKernel

from .agents.requirements_agent import generate_first_questions, process_answers
from .pipeline import stream_pipeline
from .schemas import (
    AnswerRequest,
    ArchitectureDoc,
    RequirementsDoc,
    SessionResponse,
    StartSessionRequest,
)
from .session_store import get_session, update_session, create_session


class _StartSessionPayload(BaseModel):
    task: str = Field(..., min_length=1, description="用户原始任务描述")


class _AnswerPayload(BaseModel):
    answers: Dict[str, str] = Field(..., description="问题 ID 到答案的映射")


def _to_session_response(session: Dict[str, Any]) -> SessionResponse:
    """将数据库中的会话记录转换为 API 响应。"""
    return {
        "session_id": session["session_id"],
        "status": session["status"],
        "questions": session.get("current_questions") or [],
        "requirements_doc": session.get("requirements_doc"),
        "architecture_doc": session.get("architecture_doc"),
        "result": session.get("result"),
    }


def create_session_router(kernel: MicroKernel) -> APIRouter:
    """
    创建需求会话路由。

    参数：
        kernel: 已启动的微内核实例。

    返回：
        配置好的 FastAPI APIRouter。
    """
    router = APIRouter(tags=["agent-sessions"])

    @router.post("/sessions")
    def start_session(payload: _StartSessionPayload):
        """
        创建新的需求分析会话，并由需求分析智能体返回首轮问题。
        """
        task = payload.task.strip()
        if not task:
            raise HTTPException(status_code=400, detail="task 不能为空")

        result = generate_first_questions(task)
        questions = result.get("questions") or []
        requirements_doc = result.get("requirements_doc")
        confirmed = bool(result.get("confirmed"))

        if confirmed:
            requirements_doc["confirmed"] = True

        session_id = create_session(task, questions)
        update_session(
            session_id,
            questions=questions,
            requirements_doc=requirements_doc,
            status="requirements_confirmed" if confirmed else "requirements_gathering",
            logs=[f"创建会话，任务: {task}"],
        )

        return _to_session_response(get_session(session_id))

    @router.post("/sessions/{session_id}/answers")
    def submit_answers(session_id: str, payload: _AnswerPayload):
        """
        提交用户对当前问题的答案。

        若需求仍未完整，返回下一轮问题；
        若需求已确认，更新状态为 requirements_confirmed。
        """
        session = get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="会话不存在")

        current_status = session.get("status", "")
        if current_status not in ("requirements_gathering", "requirements_confirmed"):
            raise HTTPException(status_code=400, detail="当前会话不再接受需求答案")

        task = session["task"]
        current_doc: RequirementsDoc = session.get("requirements_doc") or {}
        current_questions = session.get("current_questions") or []
        answers = session.get("answers") or []

        # 仅保存已回答的问题
        for q in current_questions:
            qid = q.get("id")
            if qid and qid in payload.answers:
                answers.append({"id": qid, "question": q.get("text", ""), "answer": payload.answers[qid]})

        result = process_answers(task, current_doc, answers)
        new_doc = result.get("requirements_doc") or current_doc
        new_questions = result.get("questions") or []
        confirmed = bool(result.get("confirmed"))

        if confirmed:
            new_doc["confirmed"] = True
            status = "requirements_confirmed"
        else:
            status = "requirements_gathering"

        update_session(
            session_id,
            status=status,
            questions=new_questions,
            answers=answers,
            requirements_doc=new_doc,
        )

        return _to_session_response(get_session(session_id))

    @router.get("/sessions/{session_id}")
    def get_session_state(session_id: str):
        """获取指定会话的完整状态。"""
        session = get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="会话不存在")
        return _to_session_response(session)

    @router.post("/sessions/{session_id}/generate")
    def generate_from_session(session_id: str):
        """
        在需求确认后触发代码生成流水线。

        流水线依次执行：架构设计 → 代码生成 → 审查部署。
        返回 SSE 流（media_type="text/event-stream"）。
        """
        session = get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="会话不存在")

        requirements_doc = session.get("requirements_doc")
        if not requirements_doc or not requirements_doc.get("confirmed"):
            raise HTTPException(status_code=400, detail="需求尚未确认，无法生成")

        update_session(session_id, status="generating")
        return StreamingResponse(
            stream_pipeline(
                kernel,
                session_id,
                session["task"],
                requirements_doc,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return router
