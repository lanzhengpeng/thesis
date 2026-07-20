"""
PaaS 核心 SDK
=============

定义稳定内核与 AI 生成插件共同使用的核心契约（装饰器与元数据辅助函数）。

AI 智能体只允许使用这些装饰器，严禁直接接触 FastAPI 或 Web 服务器。
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type


class ComponentType(str, Enum):
    """
    组件类型枚举。

    用于区分 CSM 三层架构中的不同角色：
    - MAPPER：数据访问层，直接操作数据库或内存存储。
    - SERVICE：业务逻辑层，编排 Mapper 与其他 Service。
    - CONTROLLER：HTTP 接口层，将 Service 暴露为 Web 接口。
    """

    MAPPER = "mapper"       # 数据访问层
    SERVICE = "service"     # 业务逻辑层
    CONTROLLER = "controller"  # HTTP 接口层


@dataclass
class MethodMeta:
    """
    通过 @GET/@POST 等装饰器附加到控制器方法上的元数据。

    字段说明：
        http_method: HTTP 方法字符串，例如 "GET"、"POST"。
        path: 该方法对应的路由路径模板，例如 "/{user_id}"。
        name: 原始方法名，用于生成 OpenAPI 文档摘要。
    """

    http_method: str   # HTTP 方法，如 GET/POST
    path: str          # 路由路径
    name: str          # 方法名


@dataclass
class ClassMeta:
    """
    通过装饰器附加到插件类上的元数据。

    字段说明：
        component_type: 组件类型（Mapper/Service/Controller）。
        module_name: 该类所属的插件目录名，例如 "user_module"。
        path: Controller 的基础路径前缀，例如 "/api/users"。
        dependencies: __init__ 参数注入与字段注入声明的依赖列表。
        inject_fields: 通过 @Inject 声明的需要字段注入的属性名。
        methods: Controller 类中所有 HTTP 端点方法的元数据。
    """

    component_type: ComponentType       # 组件类型
    module_name: str = ""               # 所属插件模块名
    path: str = ""                      # Controller 的基础路径
    dependencies: List[tuple] = field(default_factory=list)  # 依赖列表
    # 通过 @Inject 标记的类属性名（字段注入）
    inject_fields: List[str] = field(default_factory=list)
    methods: List[MethodMeta] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 公共装饰器
# ---------------------------------------------------------------------------


def Mapper(cls: Type) -> Type:
    """
    标记一个数据访问类（Mapper）。

    被标记的类会被微内核扫描并注册到 DI 容器，
    其他 Service 可通过类型注解自动获得其实例。

    参数：
        cls: 待标记的 Python 类。

    返回：
        传入的类本身（装饰器标准行为，便于链式使用）。
    """
    cls.__paas_meta__ = ClassMeta(component_type=ComponentType.MAPPER)
    cls.__paas_meta__.module_name = _guess_module_name(cls)
    _collect_dependencies(cls)
    return cls


def Service(cls: Type) -> Type:
    """
    标记一个业务逻辑类（Service）。

    Service 负责编排 Mapper 与其他 Service，实现业务规则。
    被标记的类同样会被 DI 容器自动实例化并注入依赖。

    参数：
        cls: 待标记的 Python 类。

    返回：
        传入的类本身。
    """
    cls.__paas_meta__ = ClassMeta(component_type=ComponentType.SERVICE)
    cls.__paas_meta__.module_name = _guess_module_name(cls)
    _collect_dependencies(cls)
    return cls


def Controller(path: str):
    """
    标记一个 HTTP 接口类（Controller），并定义其基础路径。

    Controller 中的方法可进一步使用 @GET、@POST 等装饰器声明 HTTP 端点。
    路径参数通过方法参数捕获，请求体通过第一个非路径参数捕获。

    参数：
        path: 该 Controller 下所有路由的公共前缀，例如 "/api/users"。

    返回：
        一个装饰器函数，接收类对象并返回标记后的类。

    示例：
        @Controller("/api/users")
        class UserController:
            @GET("/")
            def list_users(self): ...
    """

    def decorator(cls: Type) -> Type:
        cls.__paas_meta__ = ClassMeta(
            component_type=ComponentType.CONTROLLER,
            path=path,
        )
        cls.__paas_meta__.module_name = _guess_module_name(cls)
        _collect_dependencies(cls)
        _collect_methods(cls)
        return cls

    return decorator


def Inject(target: Any) -> Any:
    """
    标记需要进行依赖注入的对象。

    用法 1 - 参数注入（推荐）：
        def __init__(self, user_service: UserService):
            ...
    参数的类型注解已经足够，不需要在参数上加装饰器。

    用法 2 - 字段注入：
        class MyService:
            user_mapper: UserMapper = Inject(None)

    参数：
        target: 占位值，通常为 None；或作为类属性注解的默认值。

    返回：
        内部标记对象，供 DI 容器在实例化后识别并填充字段依赖。
    """
    if isinstance(target, str):
        # 作为类变量注解默认值使用
        return _InjectMarker(field_name=target)
    return _InjectMarker(field_name=None)


# ---------------------------------------------------------------------------
# HTTP 方法装饰器
# ---------------------------------------------------------------------------


def GET(path: str):
    """
    标记一个 GET 接口。

    参数：
        path: 路由路径模板，例如 "/" 或 "/{user_id}"。

    返回：
        装饰器函数，用于修饰 Controller 中的方法。
    """
    return _http_method("GET", path)


def POST(path: str):
    """
    标记一个 POST 接口。

    参数：
        path: 路由路径模板。

    返回：
        装饰器函数。
    """
    return _http_method("POST", path)


def PUT(path: str):
    """
    标记一个 PUT 接口。

    参数：
        path: 路由路径模板。

    返回：
        装饰器函数。
    """
    return _http_method("PUT", path)


def DELETE(path: str):
    """
    标记一个 DELETE 接口。

    参数：
        path: 路由路径模板。

    返回：
        装饰器函数。
    """
    return _http_method("DELETE", path)


def PATCH(path: str):
    """
    标记一个 PATCH 接口。

    参数：
        path: 路由路径模板。

    返回：
        装饰器函数。
    """
    return _http_method("PATCH", path)


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------


class _InjectMarker:
    """
    字段注入标记器。

    当 DI 容器实例化一个类后，会检查类属性是否为 _InjectMarker，
    并根据类型注解从已组装的实例中查找对应依赖并赋值。
    """
    __slots__ = ("field_name",)

    def __init__(self, field_name: Optional[str] = None):
        """
        初始化注入标记。

        参数：
            field_name: 被注入字段的名称；None 表示从类注解中推断。
        """
        self.field_name = field_name


def _http_method(method: str, path: str):
    """
    内部：为函数附加 HTTP 方法元数据。

    该函数生成实际的装饰器，被 @GET、@POST 等公共装饰器调用。

    参数：
        method: HTTP 方法字符串，例如 "GET"。
        path: 路由路径模板。

    返回：
        装饰器函数，负责把 MethodMeta 写入被装饰函数的 __paas_methods__。
    """

    def decorator(func: Callable) -> Callable:
        if not hasattr(func, "__paas_methods__"):
            func.__paas_methods__ = []
        func.__paas_methods__.append(MethodMeta(http_method=method, path=path, name=func.__name__))
        return func

    return decorator


def _collect_dependencies(cls: Type) -> None:
    """
    检查类的 __init__ 与类属性，收集所有依赖声明。

    支持两种注入方式：
    1. 参数注入：__init__ 中除 self 外带类型注解的参数。
    2. 字段注入：类属性使用 @Inject 标注且带类型注解。

    收集结果写入 cls.__paas_meta__.dependencies 与 inject_fields。

    参数：
        cls: 已被 @Mapper/@Service/@Controller 标记的类。
    """
    meta: ClassMeta = cls.__paas_meta__
    init = getattr(cls, "__init__", None)
    if init is None or init is object.__init__:
        return

    sig = inspect.signature(init)
    deps = []
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        annotation = param.annotation
        if annotation is inspect.Parameter.empty:
            continue
        if isinstance(annotation, type) or _is_forward_ref(annotation):
            deps.append((name, annotation))

    # 通过类属性实现的字段注入
    for attr_name, value in cls.__dict__.items():
        if isinstance(value, _InjectMarker):
            meta.inject_fields.append(attr_name)
            # 类型注解在类上
            annotation = cls.__annotations__.get(attr_name)
            if annotation is not None:
                deps.append((attr_name, annotation))

    meta.dependencies = deps


def _collect_methods(cls: Type) -> None:
    """
    从控制器类中收集所有 HTTP 方法元数据。

    遍历类的公开成员（非下划线开头），查找带有 __paas_methods__ 标记的方法，
    将其追加到 ClassMeta.methods 列表中。

    参数：
        cls: 已被 @Controller 标记的类。
    """
    meta: ClassMeta = cls.__paas_meta__
    for name in dir(cls):
        if name.startswith("_"):
            continue
        member = getattr(cls, name)
        if not callable(member):
            continue
        methods = getattr(member, "__paas_methods__", [])
        for m in methods:
            meta.methods.append(m)


def _guess_module_name(cls: Type) -> str:
    """
    根据类的 __module__ 推断其所属插件目录名。

    插件模块通常位于 plugins.<module_name>.<file_name> 命名空间下，
    因此取第二段作为模块名；否则返回完整模块名。

    参数：
        cls: 已标记的类。

    返回：
        插件目录名，例如 "user_module"。
    """
    mod = cls.__module__
    # 模块位于 plugins.<模块名>.<文件名> 下
    parts = mod.split(".")
    if len(parts) >= 2 and parts[0] == "plugins":
        return parts[1]
    return mod


def _is_forward_ref(annotation: Any) -> bool:
    """
    判断类型注解是否为前向引用。

    前向引用在插件内部类互相引用时常见，例如：
        def __init__(self, mapper: "UserMapper"): ...

    参数：
        annotation: __init__ 参数的类型注解。

    返回：
        True 如果是字符串形式的前向引用；否则 False。
    """
    return isinstance(annotation, (str,))


# ---------------------------------------------------------------------------
# 元数据访问函数
# ---------------------------------------------------------------------------


def get_meta(cls_or_instance: Any) -> Optional[ClassMeta]:
    """
    获取类或实例的 PaaS 元数据。

    如果传入的是实例，会先取得其实际类型，再读取 __paas_meta__。

    参数：
        cls_or_instance: 类对象或其已实例化的对象。

    返回：
        ClassMeta 对象；若未被标记则返回 None。
    """
    if not isinstance(cls_or_instance, type):
        cls_or_instance = type(cls_or_instance)
    return getattr(cls_or_instance, "__paas_meta__", None)


def is_component(cls_or_instance: Any) -> bool:
    """
    判断一个类或实例是否被标记为 PaaS 组件。

    参数：
        cls_or_instance: 类对象或其已实例化的对象。

    返回：
        True 如果存在 __paas_meta__；否则 False。
    """
    return get_meta(cls_or_instance) is not None
