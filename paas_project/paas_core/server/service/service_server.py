"""
服务口服务器
============

面向外部调用方，仅暴露插件生成的业务 Controller 路由。

端口：8001

重要：本服务器使用动态请求分发，不在启动时注册固定 FastAPI 路由，
因此插件变更后无需重启 8001 进程即可生效。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi

from paas_core.kernel.microkernel import MicroKernel
from paas_core.sdk import ComponentType, get_meta

from .dynamic_dispatcher import DynamicDispatcher


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
        include_in_schema=False,
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

    # 覆盖 OpenAPI schema 生成：把当前内核中的 Controller 元数据动态写入文档。
    # 每次访问 /docs 都会重新生成，因此插件热重载后刷新页面即可看到最新接口。
    def custom_openapi():
        return _build_service_openapi(app, dispatcher)

    app.openapi = custom_openapi

    return app, dispatcher


def _build_service_openapi(app: FastAPI, dispatcher: DynamicDispatcher) -> Dict[str, Any]:
    """
    根据当前 MicroKernel 中的 Controller 元数据生成 OpenAPI schema。

    流程：
    1. 先基于 FastAPI 已注册路由生成基础 schema（仅含 /health）。
    2. 遍历 DIContainer.report 中所有 Controller，把其方法转换成 OpenAPI path item。
    3. 路径参数、请求体按现有动态分发约定生成。

    参数：
        app: 服务口 FastAPI 应用。
        dispatcher: 动态分发器，用于获取当前内核与组装报告。

    返回：
        完整的 OpenAPI schema 字典。
    """
    # 每次重新生成，确保插件热重载后 /docs 能反映最新路由。
    base_schema = get_openapi(title=app.title, version=app.version, routes=app.routes)

    report = dispatcher.kernel.container.report
    if report is None:
        return base_schema

    for rec in report.success:
        if rec.component_type != ComponentType.CONTROLLER:
            continue

        meta = get_meta(rec.instance)
        if meta is None:
            continue

        for method_meta in meta.methods:
            http_method = method_meta.http_method
            if not http_method:
                continue

            full_path = (meta.path + (method_meta.path or "")).replace("//", "/")
            if not full_path:
                continue

            operation_id = f"{meta.module_name}_{rec.instance.__class__.__name__}_{method_meta.name}"
            operation: Dict[str, Any] = {
                "summary": method_meta.feature or method_meta.name,
                "operationId": operation_id,
                "responses": {"200": {"description": "Successful Response"}},
            }

            # 路径参数
            path_params = re.findall(r"\{(\w+)\}", full_path)
            if path_params:
                operation["parameters"] = [
                    {
                        "name": name,
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                    for name in path_params
                ]

            # POST/PUT/PATCH 默认带 JSON body
            if http_method.upper() in {"POST", "PUT", "PATCH"}:
                operation["requestBody"] = {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"},
                        }
                    },
                }

            path_item = base_schema.setdefault("paths", {}).setdefault(full_path, {})
            path_item[http_method.lower()] = operation

    return base_schema
