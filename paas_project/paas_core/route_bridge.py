"""
路由桥接
=======

将 Controller 实例动态转换为 FastAPI HTTP 路由的通用工具。

该模块属于稳定内核区，system_server 与 service_server 均可复用。
"""

from __future__ import annotations

import inspect
import re
from typing import Any, Callable, Dict, List, Optional

from fastapi import Body, FastAPI, Request

from .di_container import DIContainer
from .microkernel import MicroKernel
from .sdk import MethodMeta, get_meta


# 用于提取路由路径模板中的路径参数，例如 "/{user_id}" -> ["user_id"]
_PATH_PARAM_RE = re.compile(r"\{(\w+)\}")


def mount_controllers(app: FastAPI, kernel: MicroKernel) -> None:
    """
    将内核中所有组装成功的 Controller 实例挂载到 FastAPI 应用。

    该函数是 system_server 与 service_server 共享的入口，
    用于把 AI 插件声明的 Controller 批量转换为真实 HTTP 路由。

    参数：
        app: FastAPI 应用实例。
        kernel: 已启动的微内核实例，其 container.report 中包含控制器记录。
    """
    container = kernel.container
    if container.report is None:
        return

    for rec in container.report.get_controllers():
        _mount_controller(app, rec.instance)


def _mount_controller(app: FastAPI, controller_instance: Any) -> None:
    """
    将一个控制器实例挂载到 FastAPI 应用。

    遍历 Controller 元数据中的所有 HTTP 方法，为每个方法生成 FastAPI 端点并注册路由。

    参数：
        app: FastAPI 应用实例。
        controller_instance: 已实例化的 Controller 对象。
    """
    meta = get_meta(controller_instance)
    if meta is None:
        return

    for method_meta in meta.methods:
        full_path = (meta.path + method_meta.path).replace("//", "/")
        handler = _build_fastapi_endpoint(controller_instance, method_meta)
        app.add_api_route(
            path=full_path,
            endpoint=handler,
            methods=[method_meta.http_method],
            summary=f"{controller_instance.__class__.__name__}.{method_meta.name}",
        )


def _build_fastapi_endpoint(controller_instance: Any, method_meta: MethodMeta) -> Callable:
    """
    动态构建一个与路由模板中路径参数签名匹配的 FastAPI 异步端点。

    实现细节：
    - 通过 inspect 分析方法签名。
    - 提取路径参数并在生成函数中声明为 str 类型。
    - 第一个非 self、非路径参数视为请求体，使用 Body(default_factory=dict)。
    - request: Request 参数排在路径参数之后、请求体之前，以满足 FastAPI 默认值规则。
    - 使用 exec 在局部命名空间中生成函数，并包装原始方法以支持同步/异步返回值。

    参数：
        controller_instance: 已实例化的 Controller 对象。
        method_meta: 该方法的 MethodMeta 元数据。

    返回：
        可直接注册到 FastAPI 的异步端点函数。
    """
    original_method = getattr(controller_instance, method_meta.name)
    sig = inspect.signature(original_method)
    path_param_names = _PATH_PARAM_RE.findall(method_meta.path)

    # 识别 body 参数：第一个非 self、非路径参数的参数
    body_param_name: Optional[str] = None
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        if name in path_param_names:
            continue
        body_param_name = name
        break

    # 构建函数源码
    # FastAPI 规则：无默认值的参数必须排在有默认值参数之前。
    args_decl = []
    call_kwargs = []

    for pname in path_param_names:
        args_decl.append(f"{pname}: str")
        call_kwargs.append(f"{pname}={pname}")

    args_decl.append("request: Request")

    if body_param_name:
        args_decl.append("payload: dict = Body(default_factory=dict)")
        call_kwargs.append(f"{body_param_name}=payload")

    args_str = ", ".join(args_decl)
    kwargs_str = ", ".join(call_kwargs)

    func_source = f"""
async def endpoint({args_str}):
    result = await __call_original_method__({kwargs_str})
    if isinstance(result, dict) or isinstance(result, list):
        return result
    return {{"result": result}}
"""

    namespace: Dict[str, Any] = {
        "__call_original_method__": _make_async_caller(original_method),
        "Body": Body,
        "Request": Request,
    }
    exec(func_source, namespace)
    endpoint = namespace["endpoint"]
    endpoint.__name__ = f"{controller_instance.__class__.__name__}_{method_meta.name}"
    return endpoint


def _make_async_caller(method: Callable) -> Callable:
    """
    包装可能为同步的控制器方法，使其可被 await。

    FastAPI 端点是 async def，因此内部统一用 await 调用原始方法；
    如果原始方法返回的是普通值而非协程，则直接返回。

    参数：
        method: Controller 中的原始方法。

    返回：
        一个 async 包装函数。
    """

    async def caller(*args, **kwargs):
        result = method(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    return caller


def summarize_report(report) -> Dict[str, Any]:
    """
    生成 AssemblyReport 的简要摘要。

    用于 /admin/kernel/reload 接口返回，避免把完整堆栈暴露给前端。

    参数：
        report: DIContainer 生成的 AssemblyReport。

    返回：
        包含成功数、失败数、失败类名及错误摘要的字典。
    """
    return {
        "success_count": len(report.success),
        "failed_count": len(report.failed),
        "failed": [
            {"class": name, "error": msg.split("\n")[0]}
            for name, msg, _ in report.failed
        ],
    }
