"""
服务口服务器
============

面向外部调用方，仅暴露插件生成的业务 Controller 路由。

端口：8001
"""

from __future__ import annotations

from fastapi import FastAPI

from .microkernel import MicroKernel
from .route_bridge import mount_controllers


SERVICE_PORT = 8001


def create_service_app(kernel: MicroKernel) -> FastAPI:
    """创建对外开放的业务服务 FastAPI 应用。"""
    app = FastAPI(title="PaaS Exposed Service Server", version="0.1.0")

    # 服务口不添加前端 CORS，不暴露管理接口
    mount_controllers(app, kernel)

    @app.get("/health")
    def health():
        return {"status": "ok", "port": SERVICE_PORT}

    return app
