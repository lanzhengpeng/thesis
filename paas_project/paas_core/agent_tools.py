"""
智能体工具箱
============

这些是 AI 智能体在 AI 沙箱（plugins/）内被允许执行的唯一操作。
每个函数都会校验请求路径是否位于 plugins 目录内。

内核不会把文件系统访问直接暴露给大语言模型。
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from .sdk import is_component


# 插件沙箱根目录，AI 只能在该目录下操作文件
PLUGINS_DIR = Path(__file__).resolve().parent.parent / "plugins"


class AgentSandboxError(Exception):
    """
    智能体沙箱违规异常。

    当 AI 尝试访问 plugins/ 目录之外的文件、写入非 .py 文件或触发禁止操作时抛出。
    """
    pass


def _validate_path(path: str, must_exist: bool = False) -> Path:
    """
    确保路径位于 plugins 目录内部，防止目录遍历攻击。

    实现：
    - 将 path 解析为相对于 PLUGINS_DIR 的绝对路径。
    - 检查解析后的路径是否以 PLUGINS_DIR 的绝对路径开头。
    - 可选检查目标是否存在。

    参数：
        path: 相对于 plugins 目录的路径。
        must_exist: 是否要求目标必须存在。

    返回：
        验证后的 Path 对象。

    异常：
        AgentSandboxError: 路径越界或目标不存在时抛出。
    """
    target = (PLUGINS_DIR / path).resolve()
    if not str(target).startswith(str(PLUGINS_DIR.resolve())):
        raise AgentSandboxError(f"路径 '{path}' 逃离了 plugins 沙箱")
    if must_exist and not target.exists():
        raise AgentSandboxError(f"路径 '{path}' 不存在")
    return target


# ---------------------------------------------------------------------------
# 读操作
# ---------------------------------------------------------------------------


def list_plugins() -> List[str]:
    """
    列出所有插件模块目录。

    返回：
        plugins/ 下所有非下划线开头的目录名排序列表。
    """
    if not PLUGINS_DIR.exists():
        return []
    return sorted(
        p.name for p in PLUGINS_DIR.iterdir() if p.is_dir() and not p.name.startswith("_")
    )


def list_plugin_files(plugin_name: str) -> List[str]:
    """
    列出某个插件模块内的 Python 文件。

    参数：
        plugin_name: 插件目录名。

    返回：
        该插件目录下所有 .py 文件名排序列表。
    """
    plugin_path = _validate_path(plugin_name, must_exist=True)
    return sorted(p.name for p in plugin_path.iterdir() if p.suffix == ".py")


def read_plugin_file(plugin_name: str, file_name: str) -> str:
    """
    读取插件文件内容。

    参数：
        plugin_name: 插件目录名。
        file_name: 文件名。

    返回：
        文件 UTF-8 文本内容。
    """
    file_path = _validate_path(f"{plugin_name}/{file_name}", must_exist=True)
    if not file_path.is_file():
        raise AgentSandboxError(f"'{file_name}' 不是文件")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# 写操作
# ---------------------------------------------------------------------------


def write_plugin_file(plugin_name: str, file_name: str, content: str) -> Dict[str, str]:
    """
    创建或覆盖一个插件文件。

    基础安全检查：
    - 文件必须以 .py 结尾。
    - 路径不能逃离 plugins 沙箱。

    参数：
        plugin_name: 插件目录名。
        file_name: 文件名，必须以 .py 结尾。
        content: 文件内容。

    返回：
        {"status": "ok", "plugin": ..., "file": ...}
    """
    if not file_name.endswith(".py"):
        raise AgentSandboxError("只允许写入 .py 文件")

    plugin_path = _validate_path(plugin_name)
    plugin_path.mkdir(parents=True, exist_ok=True)

    file_path = plugin_path / file_name
    resolved = file_path.resolve()
    if not str(resolved).startswith(str(PLUGINS_DIR.resolve())):
        raise AgentSandboxError(f"文件 '{file_name}' 逃离了 plugins 沙箱")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return {"status": "ok", "plugin": plugin_name, "file": file_name}


def create_plugin(plugin_name: str) -> Dict[str, str]:
    """
    创建一个空的插件模块目录。

    参数：
        plugin_name: 插件目录名，必须是合法 Python 标识符。

    返回：
        {"status": "ok", "plugin": plugin_name}
    """
    if not plugin_name or not plugin_name.isidentifier():
        raise AgentSandboxError("插件名必须是合法的 Python 标识符")
    plugin_path = _validate_path(plugin_name)
    plugin_path.mkdir(parents=True, exist_ok=True)
    return {"status": "ok", "plugin": plugin_name}


def delete_plugin(plugin_name: str) -> Dict[str, str]:
    """
    删除整个插件模块目录。

    参数：
        plugin_name: 插件目录名。

    返回：
        {"status": "ok", "plugin": plugin_name, "message": "已删除"}
    """
    plugin_path = _validate_path(plugin_name, must_exist=True)
    shutil.rmtree(plugin_path)
    return {"status": "ok", "plugin": plugin_name, "message": "已删除"}


# ---------------------------------------------------------------------------
# 静态校验辅助函数（加载前使用）
# ---------------------------------------------------------------------------


def static_check(plugin_name: str, file_name: str) -> Dict[str, any]:
    """
    对 AI 生成的文件进行轻量级静态检查。

    检查项：
    - 是否为合法 Python 语法。
    - 是否导入了禁止的模块（os、sys、subprocess、socket）。
    - 是否调用了 eval / exec / __import__。

    参数：
        plugin_name: 插件目录名。
        file_name: 待检查文件名。

    返回：
        {"ok": bool, "errors": [...]}
    """
    import ast

    file_path = _validate_path(f"{plugin_name}/{file_name}", must_exist=True)
    errors = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"ok": False, "errors": [f"语法错误：{e}"]}

    forbidden_imports = {"os", "sys", "subprocess", "socket"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in forbidden_imports:
                    errors.append(f"禁止的导入：{alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                if root in forbidden_imports:
                    errors.append(f"禁止的导入：{node.module}")
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in ("eval", "exec", "__import__"):
                errors.append(f"禁止的调用：{func.id}")

    return {"ok": len(errors) == 0, "errors": errors}
