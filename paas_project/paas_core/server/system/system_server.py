"""
系统口服务器
============

面向平台自身前端/管理员，暴露内核管理接口与系统健康检查。

端口：8000
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from paas_core.finder import (
    DirectoryEntry,
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
