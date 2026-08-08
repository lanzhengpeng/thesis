"""
系统口服务器
============

面向平台自身前端/管理员，暴露内核管理接口与系统健康检查。

端口：8000
"""

from __future__ import annotations

import base64
import os
import re
import shutil
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from paas_core.finder import (
    DirectoryEntry,
    FileBinaryContentOut,
    FileBinaryWriteIn,
    FileContentOut,
    FileService,
    FileWriteIn,
    MoveIn,
    PathIn,
    PathOut,
)
from paas_core.finder.file_service import (
    FinderError,
    NotAFileError,
    NotADirectoryError,
    PathAlreadyExistsError,
    PathNotAllowedError,
    PathNotFoundError,
)
from paas_core.kernel.microkernel import MicroKernel


def _finder_error(exc: FinderError, status_code: int = 400) -> HTTPException:
    """将 Finder 业务异常转换为 FastAPI HTTPException。"""
    return HTTPException(status_code=status_code, detail=str(exc))


# 系统管理口监听端口，供本系统前端与管理员使用
SYSTEM_PORT = 8000

# 允许前端跨域访问，支持通过环境变量追加来源（多个用逗号分隔）
DEFAULT_CORS_ORIGINS = ["http://localhost:5173"]


def _get_cors_origins() -> list[str]:
    """从环境变量读取额外 CORS 来源，默认保留开发服务器。"""
    extra = os.getenv("PAA_DASHBOARD_ORIGINS", "")
    origins = list(DEFAULT_CORS_ORIGINS)
    if extra:
        for origin in extra.split(","):
            origin = origin.strip()
            if origin and origin not in origins:
                origins.append(origin)
    return origins


class ModuleFileWriteIn(BaseModel):
    """模块源码写入请求体。"""

    content: str


def _plugin_dir(kernel: MicroKernel, plugin_name: str) -> Path:
    """
    获取插件目录并校验其存在且位于 plugins/ 根目录下。

    返回插件目录的 Path；不存在或路径非法时抛出 HTTPException。
    """
    if not re.match(r"^[A-Za-z0-9_]+$", plugin_name):
        raise HTTPException(status_code=400, detail=f"非法的插件名: {plugin_name}")

    plugin_dir = kernel.plugins_dir / plugin_name
    resolved = plugin_dir.resolve()
    base = kernel.plugins_dir.resolve()
    if resolved != base and not str(resolved).startswith(str(base) + "/"):
        raise HTTPException(status_code=400, detail=f"非法的插件名: {plugin_name}")
    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"找不到插件: {plugin_name}")
    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail=f"{plugin_name} 不是目录")
    return resolved


def create_system_app(kernel: MicroKernel) -> FastAPI:
    """
    创建系统管理 FastAPI 应用。

    该应用运行在 8000 端口，提供：
    - 作弊纸接口：供前端画布实时展示系统架构。
    - 模块管理接口：列出已加载/失败模块、热重载指定插件。
    - 健康检查：用于负载均衡与监控。

    同时配置 CORS，允许本系统前端开发服务器（localhost:5173）跨域访问。

    参数：
        kernel: 已启动的微内核实例。

    返回：
        配置好的 FastAPI 应用。
    """
    app = FastAPI(title="PaaS System Integration Server", version="0.1.0")

    # 允许平台前端开发服务器跨域访问
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from paas_core.server.system.package_api import build_package_router

    app.include_router(build_package_router(kernel))

    @app.get("/admin/kernel/cheat-sheet")
    def cheat_sheet():
        """
        获取系统作弊纸（全局调用图 + API 映射）。

        返回：
            包含模块列表、组件统计、调用图、API 映射的字典。
        """
        return kernel.generate_cheat_sheet()

    @app.get("/admin/kernel/modules")
    def list_modules():
        """
        列出所有已加载和加载失败的模块。

        返回：
            {"loaded": [...], "failed": [...]}
        """
        return {
            "loaded": kernel.get_loaded_modules(),
            "failed": kernel.get_failed_modules(),
        }

    @app.post("/admin/kernel/reload/{plugin_name}")
    def reload_plugin(plugin_name: str):
        """
        重新加载指定插件。

        说明：
        - 该接口会刷新系统口（8000）内核容器中的状态，用于前端实时展示。
        - FastAPI 不方便运行时移除已注册路由，因此服务口（8001）不会立即生效；
          如需同步业务路由，请重启服务口进程或整个系统。

        参数：
            plugin_name: 插件目录名。

        返回：
            包含操作结果与组装报告摘要的字典。
        """
        report = kernel.reload_plugin(plugin_name)
        # FastAPI 不方便运行时移除已注册路由；
        # 本骨架中仅刷新系统口容器，服务口需重启进程才能同步。
        return {
            "message": f"插件 {plugin_name} 已在系统口重新加载",
            "note": "服务口（8001）需重启才能刷新业务路由",
            "report": report.summarize(),
        }

    # ------------------------------------------------------------------
    # Finder：项目文件增删改查（仅允许操作 plugins/ 目录）
    # ------------------------------------------------------------------
    finder = FileService(kernel.plugins_dir)

    # ------------------------------------------------------------------
    # 模块源码管理：列出、读取、保存、删除模块文件
    # ------------------------------------------------------------------

    def _validate_module_file_name(file_name: str) -> None:
        if not re.match(r"^[A-Za-z0-9_][A-Za-z0-9_.-]*$", file_name):
            raise HTTPException(status_code=400, detail=f"非法的文件名: {file_name}")
        if ".." in file_name or "/" in file_name or "\\" in file_name:
            raise HTTPException(status_code=400, detail=f"非法的文件名: {file_name}")

    @app.get("/admin/kernel/modules/{plugin_name}/files")
    def list_module_files(plugin_name: str):
        """
        列出指定模块目录下的所有 Python 文件名。

        返回：
            {"files": ["AlphaController.py", "AlphaService.py", ...]}
        """
        directory = _plugin_dir(kernel, plugin_name)
        files = sorted(
            [p.name for p in directory.iterdir() if p.is_file() and p.suffix == ".py"]
        )
        return {"files": files}

    @app.get("/admin/kernel/modules/{plugin_name}/files/{file_name}")
    def read_module_file(plugin_name: str, file_name: str):
        """
        读取指定模块中某个源码文件的内容。

        返回：
            {"content": "..."}
        """
        _plugin_dir(kernel, plugin_name)
        _validate_module_file_name(file_name)
        try:
            content, _ = finder.read_file(f"{plugin_name}/{file_name}")
        except PathNotFoundError as exc:
            raise _finder_error(exc, 404)
        return {"content": content}

    @app.put("/admin/kernel/modules/{plugin_name}/files/{file_name}")
    def write_module_file(plugin_name: str, file_name: str, payload: ModuleFileWriteIn):
        """
        保存模块源码文件，进行语法检查，通过后再热重载该模块。

        返回：
            {
                "check": {"ok": true, "errors": []},
                "reload_report": {"success_count": 1, "failed_count": 0, ...}
            }
        """
        _plugin_dir(kernel, plugin_name)
        _validate_module_file_name(file_name)

        # 先写入文件
        try:
            finder.write_file(
                f"{plugin_name}/{file_name}",
                payload.content,
                overwrite=True,
            )
        except PathNotAllowedError as exc:
            raise _finder_error(exc, 403)

        # 语法静态检查
        check = {"ok": True, "errors": []}
        try:
            compile(payload.content, f"{plugin_name}/{file_name}", "exec")
        except SyntaxError as exc:
            check = {"ok": False, "errors": [str(exc)]}
        except Exception as exc:  # pragma: no cover
            check = {"ok": False, "errors": [str(exc)]}

        # 只有语法检查通过才尝试重载模块
        reload_report: dict = {}
        if check["ok"]:
            try:
                report = kernel.reload_plugin(plugin_name)
                reload_report = report.summarize()
            except Exception as exc:
                reload_report = {"error": str(exc)}

        return {"check": check, "reload_report": reload_report}

    @app.delete("/admin/kernel/modules/{plugin_name}")
    def delete_module(plugin_name: str):
        """
        删除整个模块目录，并卸载该插件。

        说明：
        - 先从内核容器中移除该插件的类与实例。
        - 再删除磁盘上的插件目录。
        - 服务口（8001）仍需重启才能同步路由变更。
        """
        directory = _plugin_dir(kernel, plugin_name)

        # 先卸载再删除目录，避免卸载时读不到目录报错
        try:
            kernel.unload_plugin(plugin_name)
        except Exception:
            # 目录可能已损坏，允许继续删除
            pass

        shutil.rmtree(directory)

        return {
            "message": f"模块 {plugin_name} 已删除",
            "note": "服务口（8001）需重启才能同步路由变更",
        }

    @app.get("/admin/finder/list", response_model=list[DirectoryEntry])
    def finder_list(path: str = ""):
        """
        列出指定目录下的文件和子目录。

        参数：
            path: 相对于 plugins/ 的路径，空字符串表示 plugins/ 根目录。
        """
        try:
            return finder.list_directory(path)
        except PathNotAllowedError as exc:
            raise _finder_error(exc, 403)
        except PathNotFoundError as exc:
            raise _finder_error(exc, 404)
        except NotADirectoryError as exc:
            raise _finder_error(exc, 400)

    @app.get("/admin/finder/read", response_model=FileContentOut)
    def finder_read(path: str, encoding: str = "utf-8"):
        """
        读取指定文件的文本内容。

        参数：
            path: 相对于 plugins/ 的文件路径。
            encoding: 文件编码，默认 utf-8。
        """
        try:
            content, size = finder.read_file(path, encoding=encoding)
            return FileContentOut(path=path, content=content, encoding=encoding, size=size)
        except PathNotAllowedError as exc:
            raise _finder_error(exc, 403)
        except PathNotFoundError as exc:
            raise _finder_error(exc, 404)
        except NotAFileError as exc:
            raise _finder_error(exc, 400)

    @app.post("/admin/finder/write", response_model=PathOut)
    def finder_write(payload: FileWriteIn):
        """
        写入或创建文件。

        说明：
        - 父目录不存在时会自动创建。
        - overwrite 为 false 时，若文件已存在则返回 409。
        """
        try:
            finder.write_file(
                payload.path,
                payload.content,
                encoding=payload.encoding,
                overwrite=payload.overwrite,
            )
            return PathOut(path=payload.path, message="文件写入成功")
        except PathNotAllowedError as exc:
            raise _finder_error(exc, 403)
        except PathAlreadyExistsError as exc:
            raise _finder_error(exc, 409)

    @app.get("/admin/finder/read-binary", response_model=FileBinaryContentOut)
    def finder_read_binary(path: str):
        """
        读取指定二进制文件内容，以 Base64 返回。

        参数：
            path: 相对于 plugins/ 的文件路径。
        """
        try:
            data, size = finder.read_file_bytes(path)
            return FileBinaryContentOut(
                path=path,
                content_base64=base64.b64encode(data).decode("ascii"),
                size=size,
            )
        except PathNotAllowedError as exc:
            raise _finder_error(exc, 403)
        except PathNotFoundError as exc:
            raise _finder_error(exc, 404)
        except NotAFileError as exc:
            raise _finder_error(exc, 400)

    @app.post("/admin/finder/write-binary", response_model=PathOut)
    def finder_write_binary(payload: FileBinaryWriteIn):
        """
        写入或创建二进制文件。

        说明：
        - 父目录不存在时会自动创建。
        - overwrite 为 false 时，若文件已存在则返回 409。
        """
        try:
            data = base64.b64decode(payload.content_base64)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"无效的 Base64 数据: {exc}")
        try:
            finder.write_file_bytes(
                payload.path,
                data,
                overwrite=payload.overwrite,
            )
            return PathOut(path=payload.path, message="二进制文件写入成功")
        except PathNotAllowedError as exc:
            raise _finder_error(exc, 403)
        except PathAlreadyExistsError as exc:
            raise _finder_error(exc, 409)

    @app.post("/admin/finder/mkdir", response_model=PathOut)
    def finder_mkdir(payload: PathIn):
        """创建目录（递归创建父目录）。"""
        try:
            finder.create_directory(payload.path)
            return PathOut(path=payload.path, message="目录创建成功")
        except PathNotAllowedError as exc:
            raise _finder_error(exc, 403)
        except PathAlreadyExistsError as exc:
            raise _finder_error(exc, 409)

    @app.delete("/admin/finder/delete", response_model=PathOut)
    def finder_delete(payload: PathIn):
        """删除文件或目录（目录会递归删除）。"""
        try:
            finder.delete(payload.path)
            return PathOut(path=payload.path, message="删除成功")
        except PathNotAllowedError as exc:
            raise _finder_error(exc, 403)
        except PathNotFoundError as exc:
            raise _finder_error(exc, 404)

    @app.post("/admin/finder/move", response_model=PathOut)
    def finder_move(payload: MoveIn):
        """移动或重命名文件/目录。"""
        try:
            finder.move(payload.src, payload.dst)
            return PathOut(path=payload.dst, message="移动成功")
        except PathNotAllowedError as exc:
            raise _finder_error(exc, 403)
        except PathNotFoundError as exc:
            raise _finder_error(exc, 404)
        except PathAlreadyExistsError as exc:
            raise _finder_error(exc, 409)

    @app.get("/health")
    def health():
        """
        系统口健康检查。

        返回：
            {"status": "ok", "port": 8000}
        """
        return {"status": "ok", "port": SYSTEM_PORT}

    return app
