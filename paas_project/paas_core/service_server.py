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


# 对外开放服务口监听端口，仅暴露业务 API
SERVICE_PORT = 8001


def create_service_app(kernel: MicroKernel) -> FastAPI:
    """
    创建对外开放的业务服务 FastAPI 应用。

    该应用运行在 8001 端口，职责单一：
    - 挂载所有插件 Controller 生成的业务路由（/api/*）。
    - 不暴露 /admin/kernel/* 管理接口。
    - 不添加前端 CORS，避免管理面暴露在业务口。
    - 提供独立健康检查。

    参数：
        kernel: 已启动的微内核实例。

    返回：
        配置好的 FastAPI 应用。
    """
    app = FastAPI(title="PaaS Exposed Service Server", version="0.1.0")

    # 服务口不添加前端 CORS，不暴露管理接口
    mount_controllers(app, kernel)

    @app.get("/health")
    def health():
        """
        服务口健康检查。

        返回：
            {"status": "ok", "port": 8001}
        """
        return {"status": "ok", "port": SERVICE_PORT}

    return app
