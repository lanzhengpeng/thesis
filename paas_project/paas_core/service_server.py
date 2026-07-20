"""
服务口服务器
============

面向外部调用方，仅暴露插件生成的业务 Controller 路由。

端口：8001

重要：本服务器使用动态请求分发，不在启动时注册固定 FastAPI 路由，
因此插件变更后无需重启 8001 进程即可生效。
"""

from __future__ import annotations

from typing import Tuple

from fastapi import FastAPI, Request

from .dynamic_dispatcher import DynamicDispatcher
from .microkernel import MicroKernel


# 对外开放服务口监听端口，仅暴露业务 API
SERVICE_PORT = 8001


def create_service_app(kernel: MicroKernel) -> Tuple[FastAPI, DynamicDispatcher]:
    """
    创建对外开放的业务服务 FastAPI 应用。

    该应用运行在 8001 端口，职责单一：
    - 通过 DynamicDispatcher 动态匹配插件 Controller 路由（/api/*）。
    - 不暴露 /admin/kernel/* 管理接口。
    - 不添加前端 CORS，避免管理面暴露在业务口。
    - 提供独立健康检查。

    参数：
        kernel: 已启动的微内核实例。

    返回：
        (app, dispatcher) 元组，便于 main.py 绑定文件监听器。
    """
    app = FastAPI(title="PaaS Exposed Service Server", version="0.1.0")

    dispatcher = DynamicDispatcher(kernel)

    # 注册通配路由：所有请求都交给动态分发器处理。
    # 由于分发器在请求时根据当前内核状态匹配，插件变更后无需重启进程。
    @app.api_route(
        "/{full_path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    )
    async def dynamic_route(request: Request):
        """
        动态路由入口。

        直接委托给 DynamicDispatcher，由它根据当前内核状态解析并调用控制器方法。
        """
        return await dispatcher.dispatch(request)

    @app.get("/health")
    def health():
        """
        服务口健康检查。

        返回：
            {"status": "ok", "port": 8001}
        """
        return {"status": "ok", "port": SERVICE_PORT}

    return app, dispatcher
