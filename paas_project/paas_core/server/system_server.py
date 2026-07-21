"""
系统口服务器
============

面向平台自身前端/管理员，暴露内核管理接口与系统健康检查。

端口：8000
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from paas_core.agent.agent_api import create_agent_router
from paas_core.kernel.microkernel import MicroKernel

from .module_files_api import create_module_files_router
from .route_bridge import summarize_report


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

    # 注册 LangGraph agent 管理接口
    app.include_router(create_agent_router(kernel), prefix="/admin/agent")

    # 注册模块源码管理接口
    app.include_router(create_module_files_router(kernel), prefix="/admin/kernel")

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
            "report": summarize_report(report),
        }

    @app.get("/health")
    def health():
        """
        系统口健康检查。

        返回：
            {"status": "ok", "port": 8000}
        """
        return {"status": "ok", "port": SYSTEM_PORT}

    return app
