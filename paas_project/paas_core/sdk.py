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
    """组件类型枚举。"""

    MAPPER = "mapper"       # 数据访问层
    SERVICE = "service"     # 业务逻辑层
    CONTROLLER = "controller"  # HTTP 接口层


@dataclass
class MethodMeta:
    """通过 @GET/@POST 等装饰器附加到控制器方法上的元数据。"""

    http_method: str   # HTTP 方法，如 GET/POST
    path: str          # 路由路径
    name: str          # 方法名


@dataclass
class ClassMeta:
    """通过装饰器附加到插件类上的元数据。"""

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
    """标记一个数据访问类。"""
    cls.__paas_meta__ = ClassMeta(component_type=ComponentType.MAPPER)
    cls.__paas_meta__.module_name = _guess_module_name(cls)
    _collect_dependencies(cls)
    return cls


def Service(cls: Type) -> Type:
    """标记一个业务逻辑类。"""
    cls.__paas_meta__ = ClassMeta(component_type=ComponentType.SERVICE)
    cls.__paas_meta__.module_name = _guess_module_name(cls)
    _collect_dependencies(cls)
    return cls


def Controller(path: str):
    """标记一个 HTTP 接口类，并定义其基础路径。"""

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
    """
    if isinstance(target, str):
        # 作为类变量注解默认值使用
        return _InjectMarker(field_name=target)
    return _InjectMarker(field_name=None)


# ---------------------------------------------------------------------------
# HTTP 方法装饰器
# ---------------------------------------------------------------------------


def GET(path: str):
    """标记一个 GET 接口。"""
    return _http_method("GET", path)


def POST(path: str):
    """标记一个 POST 接口。"""
    return _http_method("POST", path)


def PUT(path: str):
    """标记一个 PUT 接口。"""
    return _http_method("PUT", path)


def DELETE(path: str):
    """标记一个 DELETE 接口。"""
    return _http_method("DELETE", path)


def PATCH(path: str):
    """标记一个 PATCH 接口。"""
    return _http_method("PATCH", path)


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------


class _InjectMarker:
    __slots__ = ("field_name",)

    def __init__(self, field_name: Optional[str] = None):
        self.field_name = field_name


def _http_method(method: str, path: str):
    """内部：为函数附加 HTTP 方法元数据。"""

    def decorator(func: Callable) -> Callable:
        if not hasattr(func, "__paas_methods__"):
            func.__paas_methods__ = []
        func.__paas_methods__.append(MethodMeta(http_method=method, path=path, name=func.__name__))
        return func

    return decorator


def _collect_dependencies(cls: Type) -> None:
    """检查 __init__ 方法，收集带类型注解的依赖。"""
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
    """从控制器类中收集 HTTP 方法元数据。"""
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
    """根据模块路径推断插件文件夹名称。"""
    mod = cls.__module__
    # 模块位于 plugins.<模块名>.<文件名> 下
    parts = mod.split(".")
    if len(parts) >= 2 and parts[0] == "plugins":
        return parts[1]
    return mod


def _is_forward_ref(annotation: Any) -> bool:
    """判断是否为前向引用。"""
    return isinstance(annotation, (str,))


# ---------------------------------------------------------------------------
# 元数据访问函数
# ---------------------------------------------------------------------------


def get_meta(cls_or_instance: Any) -> Optional[ClassMeta]:
    """获取类或实例的元数据。"""
    if not isinstance(cls_or_instance, type):
        cls_or_instance = type(cls_or_instance)
    return getattr(cls_or_instance, "__paas_meta__", None)


def is_component(cls_or_instance: Any) -> bool:
    """判断一个类或实例是否被标记为 PaaS 组件。"""
    return get_meta(cls_or_instance) is not None
