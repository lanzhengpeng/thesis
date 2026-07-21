"""
多智能体流水线状态与 API 契约
=============================

本模块定义 4 个智能体之间传递的状态结构，以及对外暴露的 API 请求/响应模型。
所有状态字段均使用 TypedDict，便于 LangGraph 直接使用；API 模型使用 Pydantic
做请求校验。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class RequirementsDoc(TypedDict, total=False):
    """需求分析智能体输出的结构化需求文档。"""

    title: str
    module_name: str
    business_description: str
    entities: List[Dict[str, Any]]
    api_endpoints: List[Dict[str, Any]]
    business_rules: List[str]
    cross_module_dependencies: List[str]
    confirmed: bool


class ArchitectureDoc(TypedDict, total=False):
    """架构设计智能体输出的模块架构文档。"""

    module_name: str
    api_prefix: str
    classes: List[Dict[str, Any]]
    files: List[Dict[str, Any]]
    dependencies: List[str]
    calls_graph: List[Dict[str, Any]]


class GeneratedFiles(TypedDict, total=False):
    """代码生成智能体输出的文件集合。"""

    files: Dict[str, str]
    notes: List[str]


class PipelineState(TypedDict, total=False):
    """LangGraph 多智能体流水线全局状态。"""

    session_id: str
    task: str
    status: str
    requirements_doc: Optional[RequirementsDoc]
    architecture_doc: Optional[ArchitectureDoc]
    files: Dict[str, str]
    written: List[str]
    checks: Dict[str, Any]
    reload_report: Dict[str, Any]
    logs: List[str]
    result: Dict[str, Any]


class StartSessionRequest(TypedDict):
    """创建需求会话请求。"""

    task: str


class AnswerRequest(TypedDict):
    """提交答案请求。"""

    answers: Dict[str, str]


class Question(TypedDict):
    """需求分析阶段的一个问题。"""

    id: str
    text: str
    reason: str


class SessionResponse(TypedDict, total=False):
    """会话状态响应。"""

    session_id: str
    status: str
    questions: List[Question]
    requirements_doc: Optional[RequirementsDoc]
    architecture_doc: Optional[ArchitectureDoc]
    result: Optional[Dict[str, Any]]
