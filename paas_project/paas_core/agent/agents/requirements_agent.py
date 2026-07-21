"""
需求分析智能体
==============

负责与用户交互，补全需求并输出结构化的 RequirementsDoc。
"""

from __future__ import annotations

import keyword
import re
from typing import Any, Dict, List, Optional

from ..llm_utils import invoke_json
from ..prompts import (
    REQUIREMENTS_SYSTEM_PROMPT,
    requirements_first_turn_prompt,
    requirements_followup_prompt,
)
from ..schemas import PipelineState, RequirementsDoc


def _normalize_module_name(name: str) -> str:
    """统一模块名后缀为 _module。"""
    if not name.endswith("_module"):
        name = f"{name}_module"
    return name


def _is_valid_module_name(name: str) -> bool:
    """判断是否为合法 Python 标识符且非保留字。"""
    if not name or not name.isidentifier():
        return False
    return not keyword.iskeyword(name)


def _fallback_module_name(task: str) -> str:
    """确定性模块名提取。"""
    if "用户" in task:
        return "user_module"
    if "订单" in task:
        return "order_module"
    if "商品" in task or "产品" in task:
        return "product_module"
    return _normalize_module_name("agent_demo")


def _extract_module_name(task: str) -> str:
    """尝试从任务中提取模块名。"""
    task_lower = task.lower()
    # 简单关键词匹配
    keywords_map = {
        "用户": "user_module",
        "订单": "order_module",
        "商品": "product_module",
        "产品": "product_module",
        "评论": "comment_module",
        "库存": "inventory_module",
    }
    for key, module in keywords_map.items():
        if key in task:
            return module
    # 取任务中第一个连续中文/英文词作为模块名
    match = re.search(r"[一-龥a-zA-Z]+", task)
    if match:
        raw = match.group(0).lower().replace(" ", "_")
        raw = re.sub(r"[^a-z0-9_]", "", raw)
        if raw:
            return _normalize_module_name(raw)
    return _normalize_module_name("agent_demo")


def _default_questions(task: str) -> List[Dict[str, str]]:
    """生成默认首轮问题。"""
    module_name = _extract_module_name(task)
    return [
        {
            "id": "q1",
            "text": "这个模块的核心业务实体是什么？（例如：用户、订单、商品）",
            "reason": "确定模块需要管理的核心数据对象",
        },
        {
            "id": "q2",
            "text": "该实体有哪些关键字段？（例如：用户名、邮箱、创建时间）",
            "reason": "用于设计 Mapper 的数据结构和 Service 的方法参数",
        },
        {
            "id": "q3",
            "text": "需要暴露哪些 REST 接口？（例如：列表查询、详情查询、创建）",
            "reason": "用于设计 Controller 的路由",
        },
        {
            "id": "q4",
            "text": "是否需要依赖其他模块？（例如：订单模块依赖用户模块）",
            "reason": "用于确定跨模块依赖和调用关系",
        },
        {
            "id": "q5",
            "text": "有哪些核心业务规则需要校验？",
            "reason": "用于在 Service 层实现业务逻辑",
        },
    ]


def _default_requirements_doc(task: str) -> RequirementsDoc:
    """生成默认需求文档。"""
    module_name = _extract_module_name(task)
    entity_name = module_name.replace("_module", "")
    return {
        "title": f"{entity_name.title()} 模块",
        "module_name": module_name,
        "business_description": task,
        "entities": [
            {
                "name": entity_name,
                "fields": ["id", "name"],
                "relationships": [],
            }
        ],
        "api_endpoints": [
            {"method": "GET", "path": "/", "description": "查询列表"},
            {"method": "GET", "path": "/{id}", "description": "查询详情"},
            {"method": "POST", "path": "/", "description": "创建"},
        ],
        "business_rules": [],
        "cross_module_dependencies": [],
        "confirmed": False,
    }


def generate_first_questions(task: str) -> Dict[str, Any]:
    """
    根据初始任务生成首轮问题和初步需求文档。

    优先调用 LLM；LLM 不可用时使用规则模板。
    """
    task = task.strip()
    fallback = {
        "confirmed": False,
        "questions": _default_questions(task),
        "requirements_doc": _default_requirements_doc(task),
    }

    data = invoke_json(
        REQUIREMENTS_SYSTEM_PROMPT,
        requirements_first_turn_prompt(task),
    )
    if not data:
        return fallback

    doc = data.get("requirements_doc") or {}
    module_name = doc.get("module_name") or _extract_module_name(task)
    module_name = _normalize_module_name(module_name)
    if not _is_valid_module_name(module_name):
        module_name = _extract_module_name(task)
    doc["module_name"] = module_name

    questions = data.get("questions") or _default_questions(task)
    confirmed = bool(data.get("confirmed"))

    return {
        "confirmed": confirmed,
        "questions": questions,
        "requirements_doc": doc,
    }


def process_answers(
    task: str,
    current_doc: RequirementsDoc,
    answers: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    根据用户答案更新需求文档，并决定是否需要继续提问。

    参数：
        task: 原始任务。
        current_doc: 当前需求文档。
        answers: 用户本次提交的所有答案列表。

    返回：
        {"confirmed": bool, "questions": [...], "requirements_doc": {...}}
    """
    fallback = {
        "confirmed": True,
        "questions": [],
        "requirements_doc": current_doc,
    }

    data = invoke_json(
        REQUIREMENTS_SYSTEM_PROMPT,
        requirements_followup_prompt(task, current_doc, answers),
    )
    if not data:
        return fallback

    merged_doc = dict(current_doc)
    new_doc = data.get("requirements_doc") or {}
    for key, value in new_doc.items():
        if value not in (None, "", []):
            merged_doc[key] = value

    # 如果已经收集了实体、接口、模块名等关键信息，则自动确认
    if not data.get("confirmed"):
        if (
            merged_doc.get("entities")
            and merged_doc.get("api_endpoints")
            and merged_doc.get("module_name")
        ):
            merged_doc["confirmed"] = True
            return {"confirmed": True, "questions": [], "requirements_doc": merged_doc}

    questions = data.get("questions") or []
    confirmed = bool(data.get("confirmed")) or len(questions) == 0
    merged_doc["confirmed"] = confirmed

    return {
        "confirmed": confirmed,
        "questions": questions,
        "requirements_doc": merged_doc,
    }


def run_requirements_node(state: PipelineState, kernel: Any) -> Dict[str, Any]:
    """
    LangGraph 流水线中的需求确认节点。

    从状态中读取已确认的需求文档；若未确认则标记为等待需求。
    """
    logs = list(state.get("logs", []))
    requirements_doc = state.get("requirements_doc")

    if not requirements_doc:
        logs.append("需求文档缺失，无法继续")
        return {
            "status": "requirements_missing",
            "logs": logs,
        }

    if not requirements_doc.get("confirmed"):
        logs.append("需求尚未确认，等待用户补充")
        return {
            "status": "awaiting_requirements",
            "logs": logs,
        }

    module_name = requirements_doc.get("module_name", "")
    module_name = _normalize_module_name(module_name)
    requirements_doc["module_name"] = module_name
    logs.append(f"需求已确认，模块名: {module_name}")
    return {
        "requirements_doc": requirements_doc,
        "status": "requirements_ready",
        "logs": logs,
    }
