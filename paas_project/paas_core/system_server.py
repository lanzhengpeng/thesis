"""
系统口服务器
============

面向平台自身前端/管理员，暴露内核管理接口与系统健康检查。

端口：8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .microkernel import MicroKernel
from .route_bridge import summarize_report


SYSTEM_PORT = 8000


def create_system_app(kernel: MicroKernel) -> FastAPI:
    """创建系统管理 FastAPI 应用。"""
    app = FastAPI(title="PaaS System Integration Server", version="0.1.0")

    # 允许平台前端开发服务器跨域访问
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/admin/kernel/cheat-sheet")
    def cheat_sheet():
        return kernel.generate_cheat_sheet()

    @app.get("/admin/kernel/modules")
    def list_modules():
        return {
            "loaded": kernel.get_loaded_modules(),
            "failed": kernel.get_failed_modules(),
        }

    @app.post("/admin/kernel/reload/{plugin_name}")
    def reload_plugin(plugin_name: str):
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
        return {"status": "ok", "port": SYSTEM_PORT}

    return app
