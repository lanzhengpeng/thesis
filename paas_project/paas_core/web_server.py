"""
Web 服务器兼容层
================

原 `create_web_app` 保留为兼容入口，内部组合 system_server + 业务路由。

生产环境推荐直接使用 `main.py` 启动双进程：
- 8000 系统口：`paas_core.system_server.create_system_app`
- 8001 服务口：`paas_core.service_server.create_service_app`
"""

from __future__ import annotations

from fastapi import FastAPI

from .microkernel import MicroKernel
from .route_bridge import mount_controllers
from .system_server import create_system_app


def create_web_app(kernel: MicroKernel) -> FastAPI:
    """兼容旧入口：同时挂载管理接口与业务路由。"""
    app = create_system_app(kernel)
    mount_controllers(app, kernel)
    return app


def create_app() -> FastAPI:
    """Uvicorn 工厂入口：单端口聚合模式。"""
    kernel = MicroKernel()
    kernel.boot()
    return create_web_app(kernel)
