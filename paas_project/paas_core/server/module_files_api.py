"""
模块文件管理接口
================

在系统口（8000）暴露插件模块源码的查看、编辑、删除端点。

所有路径均受 agent_tools 沙箱保护，只能操作 plugins/ 目录下的 .py 文件。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field

from paas_core.kernel.microkernel import MicroKernel

from ..agent.agent_tools import (
    AgentSandboxError,
    delete_plugin,
    list_plugin_files,
    read_plugin_file,
    static_check,
    write_plugin_file,
)
from ..agent.locks import plugin_write_lock
from .route_bridge import summarize_report


class FileListResponse(BaseModel):
    """模块文件列表响应。"""

    plugin: str
    files: List[str]


class FileContentResponse(BaseModel):
    """单文件内容响应。"""

    plugin: str
    file: str
    content: str


class WriteFileRequest(BaseModel):
    """覆盖写入文件请求体。"""

    content: str = Field(..., description="新的 Python 源码内容")


class WriteFileResponse(BaseModel):
    """写入并重载后的响应。"""

    plugin: str
    file: str
    check: Dict[str, Any]
    reload_report: Dict[str, Any]


class DeleteModuleResponse(BaseModel):
    """删除模块响应。"""

    plugin: str
    message: str


_PLUGIN_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_FILE_NAME_RE = re.compile(r"^[a-zA-Z0-9_]+\.py$")


def _validate_plugin_name(plugin_name: str) -> None:
    """校验插件目录名是否合法且不是私有目录。"""
    if not plugin_name or plugin_name.startswith("_"):
        raise HTTPException(status_code=400, detail="插件名不能以 _ 开头")
    if not _PLUGIN_NAME_RE.match(plugin_name):
        raise HTTPException(status_code=400, detail="插件名必须是合法 Python 标识符")


def _validate_file_name(file_name: str) -> None:
    """校验文件名必须是安全的 .py 文件。"""
    if not file_name or not _FILE_NAME_RE.match(file_name):
        raise HTTPException(status_code=400, detail="文件名必须是 *.py 且只含字母数字下划线")


def _handle_sandbox_error(exc: AgentSandboxError) -> None:
    """统一处理沙箱违规异常。"""
    raise HTTPException(status_code=400, detail=str(exc)) from exc


def create_module_files_router(kernel: MicroKernel) -> APIRouter:
    """创建模块文件管理路由。"""
    router = APIRouter(tags=["module-files"])

    @router.get("/modules/{plugin_name}/files", response_model=FileListResponse)
    def list_files(plugin_name: str = Path(..., description="插件目录名")):
        """列出指定模块下的所有 .py 文件。"""
        _validate_plugin_name(plugin_name)
        try:
            files = list_plugin_files(plugin_name)
        except AgentSandboxError as exc:
            _handle_sandbox_error(exc)
        return {"plugin": plugin_name, "files": files}

    @router.get("/modules/{plugin_name}/files/{file_name}", response_model=FileContentResponse)
    def read_file(
        plugin_name: str = Path(..., description="插件目录名"),
        file_name: str = Path(..., description="文件名"),
    ):
        """读取指定模块的单个 Python 文件内容。"""
        _validate_plugin_name(plugin_name)
        _validate_file_name(file_name)
        try:
            content = read_plugin_file(plugin_name, file_name)
        except AgentSandboxError as exc:
            _handle_sandbox_error(exc)
        return {"plugin": plugin_name, "file": file_name, "content": content}

    @router.put("/modules/{plugin_name}/files/{file_name}", response_model=WriteFileResponse)
    def write_file(
        payload: WriteFileRequest,
        plugin_name: str = Path(..., description="插件目录名"),
        file_name: str = Path(..., description="文件名"),
    ):
        """
        覆盖写入指定模块的 Python 文件，随后进行静态检查并重启整个内核。

        说明：
        - 静态检查不通过时不会触发内核重启，但文件内容会保留，便于用户继续编辑。
        - 使用完整重启而非单模块重载，避免跨模块依赖（如 order_module 引用 user_module 的类）失效。
        """
        _validate_plugin_name(plugin_name)
        _validate_file_name(file_name)

        try:
            with plugin_write_lock():
                write_plugin_file(plugin_name, file_name, payload.content)
                check = static_check(plugin_name, file_name)
                if not check.get("ok"):
                    return {
                        "plugin": plugin_name,
                        "file": file_name,
                        "check": check,
                        "reload_report": {"error": "静态检查未通过，未执行重载"},
                    }
                report = kernel.reboot()
                return {
                    "plugin": plugin_name,
                    "file": file_name,
                    "check": check,
                    "reload_report": summarize_report(report),
                }
        except AgentSandboxError as exc:
            _handle_sandbox_error(exc)

    @router.delete("/modules/{plugin_name}", response_model=DeleteModuleResponse)
    def delete_module(plugin_name: str = Path(..., description="插件目录名")):
        """删除整个插件模块目录，并重启内核使变更生效。"""
        _validate_plugin_name(plugin_name)
        try:
            delete_plugin(plugin_name)
            kernel.reboot()
        except AgentSandboxError as exc:
            _handle_sandbox_error(exc)
        return {"plugin": plugin_name, "message": "已删除"}

    return router
