"""
动态请求分发器
==============

为 8001 服务口提供无需重启进程的热更新能力。

传统做法是在启动时把每个 Controller 方法注册为 FastAPI 路由；
FastAPI 无法运行时注销路由，因此插件变更后必须重启服务进程。

本模块采用"请求时动态匹配"策略：
- 只注册一个通配路由（或中间件）。
- 每次请求根据当前 MicroKernel 中的 Controller 元数据进行匹配。
- 插件变更后重建内核并原子替换 dispatcher 持有的内核引用。
- 路由表始终在内存中按需构建，不需要修改 FastAPI 路由表。
"""

from __future__ import annotations

import inspect
import json
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import HTTPException, Request

from .microkernel import MicroKernel
from .sdk import ClassMeta, MethodMeta, get_meta


class DynamicDispatcher:
    """
    动态控制器分发器。

    持有当前 MicroKernel 引用，在请求到达时实时匹配控制器方法并调用。
    通过 set_kernel() 原子替换内核，支持插件热更新。
    """

    def __init__(self, kernel: MicroKernel):
        """
        初始化分发器。

        参数：
            kernel: 已启动的微内核实例。
        """
        self.kernel = kernel
        # 缓存编译后的路由模板，避免每次请求重复编译。
        # 键：path_template；值：(compiled_pattern, param_names)
        self._route_cache: Dict[str, Tuple[re.Pattern, List[str]]] = {}

    def set_kernel(self, kernel: MicroKernel) -> None:
        """
        原子替换当前内核。

        通常在插件热重载成功后调用，使后续请求使用新内核。

        参数：
            kernel: 新的已启动微内核实例。
        """
        self.kernel = kernel
        # 路径模板可能已变更，清空缓存
        self._route_cache.clear()

    async def dispatch(self, request: Request) -> Any:
        """
        根据请求方法和路径动态匹配并调用控制器方法。

        参数：
            request: FastAPI Request 对象。

        返回：
            控制器方法的返回值（dict/list 直接返回，其它值包装为 {"result": ...}）。

        异常：
            HTTPException(404): 当前内核中没有匹配的路由。
            HTTPException(405/422/500): 调用过程中的其它错误。
        """
        report = self.kernel.container.report
        if report is None:
            raise HTTPException(status_code=503, detail="内核尚未组装完成")

        path = request.url.path
        method = request.method.upper()

        # 遍历当前内核中的所有 Controller，寻找匹配的方法
        for rec in report.get_controllers():
            meta = get_meta(rec.instance)
            if meta is None:
                continue

            for method_meta in meta.methods:
                if method_meta.http_method.upper() != method:
                    continue

                full_template = (meta.path + method_meta.path).replace("//", "/")
                pattern, param_names = self._compile_path(full_template)
                match = pattern.match(path)
                if not match:
                    continue

                return await self._invoke(
                    controller_instance=rec.instance,
                    method_meta=method_meta,
                    param_names=param_names,
                    param_values=match.groups(),
                    request=request,
                )

        raise HTTPException(status_code=404, detail=f"未找到 {method} {path}")

    def _compile_path(self, template: str) -> Tuple[re.Pattern, List[str]]:
        """
        把路径模板编译成正则表达式并提取参数名。

        例如 `/api/orders/{order_id}` 编译为 `^/api/orders/([^/]+)$`，
        并返回参数名 ["order_id"]。

        参数：
            template: 路由路径模板。

        返回：
            (compiled_pattern, param_names)。
        """
        cache_key = template
        if cache_key in self._route_cache:
            return self._route_cache[cache_key]

        param_names: List[str] = []

        def _replace_param(match: re.Match) -> str:
            param_names.append(match.group(1))
            return r"([^/]+)"

        pattern_str = "^" + re.sub(r"\{(\w+)\}", _replace_param, template) + "$"
        pattern = re.compile(pattern_str)
        result = (pattern, param_names)
        self._route_cache[cache_key] = result
        return result

    async def _invoke(
        self,
        controller_instance: Any,
        method_meta: MethodMeta,
        param_names: List[str],
        param_values: Tuple[str, ...],
        request: Request,
    ) -> Any:
        """
        调用匹配到的控制器方法。

        参数构建逻辑：
        1. 路径参数按名称注入 kwargs。
        2. 对于 POST/PUT/PATCH，尝试读取 JSON body，作为第一个非 self、非路径参数传入。
           这与现有 @Controller 约定一致（body 参数通常名为 payload: dict）。
        3. 调用原始方法，若返回协程则 await。
        4. 返回 dict/list 直接序列化，否则包装为 {"result": ...}。

        参数：
            controller_instance: 控制器实例。
            method_meta: 方法元数据。
            param_names: 路径参数名列表。
            param_values: 路径参数值元组。
            request: FastAPI Request 对象，用于读取 body。

        返回：
            控制器方法返回值或包装结果。
        """
        kwargs: Dict[str, Any] = dict(zip(param_names, param_values))

        original_method = getattr(controller_instance, method_meta.name)
        sig = inspect.signature(original_method)

        # 非 GET/DELETE 请求尝试读取 JSON body
        body: Optional[dict] = None
        if request.method.upper() in {"POST", "PUT", "PATCH"}:
            try:
                body = await request.json()
            except json.JSONDecodeError:
                body = {}
            except Exception:
                # 无 body 或解析失败时默认为空字典
                body = {}

        if body is not None:
            # 找到第一个非 self、非路径参数的参数名，把 body 传给它
            for name, param in sig.parameters.items():
                if name == "self" or name in kwargs:
                    continue
                kwargs[name] = body
                break

        result = original_method(**kwargs)
        if inspect.isawaitable(result):
            result = await result

        if isinstance(result, (dict, list)):
            return result
        return {"result": result}
