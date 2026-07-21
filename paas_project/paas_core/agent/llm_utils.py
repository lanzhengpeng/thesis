"""
LLM 辅助函数
============

为多智能体流水线提供统一的 LLM 客户端初始化与 JSON 提取能力。
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, AsyncIterator, Dict, Optional

from .prompts import GENERAL_CHAT_SYSTEM_PROMPT, INTENT_SYSTEM_PROMPT, intent_prompt

try:
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI
except ImportError:  # pragma: no cover
    SystemMessage = None  # type: ignore
    HumanMessage = None  # type: ignore
    ChatOpenAI = None  # type: ignore


DEFAULT_API_KEY = "qwe"
DEFAULT_BASE_URL = "http://112.132.229.234:8030/v1"
DEFAULT_MODEL = "DeepSeek-R1-Distill-Qwen-671B"


def get_llm(timeout: Optional[int] = None) -> Optional[Any]:
    """
    初始化可选的 LLM 客户端。

    配置来源（优先级从高到低）：
    1. 环境变量 OPENAI_API_KEY / OPENAI_BASE_URL / AGENT_MODEL。
    2. 代码默认值。

    若初始化失败或未安装相关依赖，返回 None，后续使用确定性回退。
    """
    if ChatOpenAI is None:
        return None

    api_key = os.getenv("OPENAI_API_KEY", DEFAULT_API_KEY)
    base_url = os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL)
    model = os.getenv("AGENT_MODEL", DEFAULT_MODEL)

    try:
        return ChatOpenAI(
            openai_api_key=api_key,
            openai_api_base=base_url,
            model=model,
            temperature=0.2,
            max_tokens=4096,
            timeout=timeout if timeout is not None else 15,
        )
    except Exception as exc:  # pragma: no cover
        print(f"[Agent] LLM 初始化失败: {exc}")
        return None


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """
    从模型输出中提取最外层 JSON 对象。

    支持以下场景：
    - 纯 JSON 字符串。
    - 被 markdown 代码块包裹的 JSON。
    - JSON 前后带有解释文本时，提取第一个完整的 `{}` 对象。
    """
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    for i in range(start, len(text)):
        char = text[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def invoke_json(
    system_prompt: str,
    user_prompt: str,
    timeout: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    调用 LLM 并尝试将返回内容解析为 JSON 字典。

    参数：
        system_prompt: 系统提示词。
        user_prompt: 用户提示词。
        timeout: LLM 调用超时秒数，默认 15 秒。

    返回：
        解析后的字典；LLM 不可用或解析失败时返回 None。
    """
    llm = get_llm(timeout=timeout)
    if llm is None or SystemMessage is None or HumanMessage is None:
        return None
    try:
        resp = llm.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        )
        return extract_json(resp.content)
    except Exception as exc:  # pragma: no cover
        print(f"[Agent] LLM 调用失败: {exc}")
        return None


async def stream_llm_text(
    system_prompt: str,
    user_prompt: str,
) -> AsyncIterator[str]:
    """
    流式调用 LLM，产出文本片段。

    参数：
        system_prompt: 系统提示词。
        user_prompt: 用户提示词。

    返回：
        异步迭代器，每个元素为一个文本片段。
    """
    llm = get_llm()
    if llm is None or SystemMessage is None or HumanMessage is None:
        yield "LLM 服务暂不可用，请稍后重试。"
        return

    try:
        async for chunk in llm.astream(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        ):
            text = getattr(chunk, "content", None)
            if text:
                yield text
    except Exception as exc:  # pragma: no cover
        print(f"[Agent] LLM 流式调用失败: {exc}")
        yield "智能体服务暂时无法响应，请稍后再试。"


# 用于意图识别兜底的关键词
_MODULE_GENERATION_KEYWORDS = {
    "创建", "生成", "新增", "添加", "增加", "开发", "写", "做一个",
    "模块", "插件", "接口", "服务", "mapper", "service", "controller",
    "api", "rest", "crud", "业务", "功能",
}

_MODULE_MODIFICATION_KEYWORDS = {
    "修复", "修改", "更新", "改", "调整", "改动", "patch", "bug",
    "加上", "加上去", "新增.*接口", "删除.*接口", "增加.*接口",
    "让.*调用", "改为", "改成", "连接到", "接到",
}


def classify_intent(message: str) -> str:
    """
    识别用户输入的意图。

    优先调用 LLM；LLM 不可用时使用关键词规则兜底。

    参数：
        message: 用户输入消息。

    返回：
        "general_chat"、"module_generation" 或 "module_modification"。
    """
    data = invoke_json(INTENT_SYSTEM_PROMPT, intent_prompt(message))
    if data:
        intent = data.get("intent", "").lower().strip()
        if intent in ("general_chat", "module_generation", "module_modification"):
            return intent

    # LLM 不可用时使用确定性规则兜底
    text = message.lower()
    if any(kw.lower() in text for kw in _MODULE_MODIFICATION_KEYWORDS):
        return "module_modification"
    if any(kw.lower() in text for kw in _MODULE_GENERATION_KEYWORDS):
        return "module_generation"
    return "general_chat"
