"""
Agent SSE 文本格式化工具
========================

把结构化的流水线结果转换成面向用户的 Markdown，并把文本安全地编码为 SSE 帧。
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict


def format_pipeline_markdown(result: Dict[str, Any], title: str = "生成结果") -> str:
    """把 pipeline_result 中的字段转换为一段面向用户的 Markdown 摘要。"""
    lines: list[str] = [f"## {title}", ""]

    module_name = result.get("module_name") or ""
    status = result.get("status") or "unknown"

    lines.append(f"- **模块名**：{module_name}")
    lines.append(f"- **生成状态**：{status}")

    files = result.get("files") or []
    if files:
        lines.append(f"- **生成文件**：{', '.join(str(f) for f in files)}")

    written = result.get("written") or []
    if written:
        lines.append(f"- **已写入**：{', '.join(str(w) for w in written)}")

    logs = result.get("logs") or []
    if logs:
        lines.append("")
        lines.append("**执行日志**：")
        for log in logs:
            lines.append(f"- {log}")

    reload_report = result.get("reload_report") or {}
    if reload_report:
        lines.append("")
        lines.append("**重载报告**：")
        if isinstance(reload_report, dict):
            for key, value in reload_report.items():
                lines.append(f"- {key}：{value}")
        else:
            lines.append(f"- {reload_report}")

    return "\n".join(lines)


def sse_text_frame(text: str) -> str:
    """
    把任意文本编码成符合 SSE 规范的文本帧。

    文本中的换行会被拆分为多行 ``data:`` 字段，浏览器/EventSource 会按标准把它们用 ``\n``
    重新拼接。帧尾用空行标识事件结束。
    """
    lines = text.split("\n")
    return "".join(f"data: {line}\n" for line in lines) + "\n"


async def stream_text_chunks(
    text: str,
    chunk_size: int = 2,
    delay: float = 0.002,
) -> AsyncIterator[str]:
    """
    把文本按固定字符数切成小块，异步产出 SSE 文本帧，实现打字机效果。

    参数：
        text: 要流式输出的完整文本。
        chunk_size: 每帧包含的字符数；中文无天然词边界，默认 2 个字符一帧。
        delay: 每帧之间的延迟（秒）。设为 0 则尽可能快地推送。
    """
    if chunk_size < 1:
        chunk_size = 1
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        yield sse_text_frame(chunk)
        if delay > 0 and i + chunk_size < len(text):
            await asyncio.sleep(delay)
