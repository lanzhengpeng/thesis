"""
依赖注入容器
============

实现两遍扫描生命周期：

1. 发现阶段：遍历插件模块，注册带装饰器的类。
2. 组装阶段：按拓扑顺序实例化类，并注入已创建的依赖。

故障隔离：如果某个类或其传递依赖实例化失败，整棵子树会被剪掉，
不会影响兄弟模块。
"""

from __future__ import annotations

import traceback
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from paas_core.sdk import ClassMeta, ComponentType, get_meta, is_component


@dataclass
class InstanceRecord:
    """
    实例化成功的记录。

    字段说明：
        instance: 组装后的实例对象。
        module_name: 该实例所属的插件模块名。
        component_type: 实例的组件类型（Mapper/Service/Controller）。
    """

    instance: Any
    module_name: str
    component_type: ComponentType


@dataclass
class AssemblyReport:
    """
    组装报告。

    记录 DI 容器组装阶段的成功实例、失败信息以及调用图，
    供作弊纸生成、模块健康检查和前端可视化使用。
    """

    success: List[InstanceRecord] = field(default_factory=list)
    failed: List[tuple] = field(default_factory=list)
    # module_name -> {component_type -> class_name}
    call_graph: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)

    def is_alive(self, module_name: str) -> bool:
        """
        判断某个模块是否至少有一个组件存活。

        参数：
            module_name: 插件模块名。

        返回：
            True 如果该模块下存在成功实例化的组件。
        """
        return any(r.module_name == module_name for r in self.success)

    def get_controllers(self) -> List[InstanceRecord]:
        """
        获取所有控制器实例。

        返回：
            InstanceRecord 列表，用于后续挂载到 FastAPI。
        """
        return [r for r in self.success if r.component_type == ComponentType.CONTROLLER]

    def get_services(self) -> List[InstanceRecord]:
        """
        获取所有服务实例。

        返回：
            InstanceRecord 列表。
        """
        return [r for r in self.success if r.component_type == ComponentType.SERVICE]

    def get_mappers(self) -> List[InstanceRecord]:
        """
        获取所有数据访问实例。

        返回：
            InstanceRecord 列表。
        """
        return [r for r in self.success if r.component_type == ComponentType.MAPPER]


class DIContainer:
    """
    依赖注入容器。

    保存已发现类的注册表和已组装实例，负责按依赖顺序完成实例化。
    """

    def __init__(self):
        # 键：类对象；值：该类的 ClassMeta 元数据
        self._classes: Dict[Type, ClassMeta] = {}
        # 键：类对象；值：组装后的实例（失败时存 None）
        self._instances: Dict[Type, Any] = {}
        # 键：类名；值：类对象（用于前向引用查找）
        self._by_name: Dict[str, Type] = {}
        # 最近一次组装生成的报告
        self.report: Optional[AssemblyReport] = None

    # ------------------------------------------------------------------
    # 发现阶段
    # ------------------------------------------------------------------

    def register_class(self, cls: Type) -> None:
        """
        注册一个带装饰器的类到容器。

        只有被 @Mapper、@Service 或 @Controller 标记的类才会被注册。

        参数：
            cls: 待注册的类。
        """
        if not is_component(cls):
            return
        meta = get_meta(cls)
        self._classes[cls] = meta
        self._by_name[cls.__name__] = cls

    def discover_module_classes(self, module: Any) -> List[Type]:
        """
        在已加载的模块对象中注册所有带装饰器的类。

        微内核在导入插件文件后调用本方法，完成发现阶段。

        参数：
            module: Python 模块对象，通常来自 sys.modules。

        返回：
            本次发现的带装饰器类列表。
        """
        discovered = []
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and is_component(attr):
                self.register_class(attr)
                discovered.append(attr)
        return discovered

    def all_classes(self) -> Dict[Type, ClassMeta]:
        """
        返回所有已注册的类。

        返回：
            类 -> ClassMeta 的字典。
        """
        return self._classes

    # ------------------------------------------------------------------
    # 组装阶段
    # ------------------------------------------------------------------

    def assemble(self) -> AssemblyReport:
        """
        按依赖顺序实例化所有已注册的类。

        流程：
        1. 通过拓扑排序确定实例化顺序（Mapper -> Service -> Controller）。
        2. 依次实例化每个类，注入已创建的依赖。
        3. 失败的类标记为 None，其依赖者也会因拿不到实例而失败。
        4. 生成并返回 AssemblyReport。

        返回：
            包含成功实例、失败信息和调用图的组装报告。
        """
        self.report = AssemblyReport()
        order = self._topological_order()

        for cls in order:
            meta = self._classes[cls]
            try:
                instance = self._instantiate(cls, meta)
                self._instances[cls] = instance
                self.report.success.append(
                    InstanceRecord(
                        instance=instance,
                        module_name=meta.module_name,
                        component_type=meta.component_type,
                    )
                )
                self._add_to_call_graph(cls, meta)
            except Exception as exc:
                msg = f"{cls.__name__}: {exc}"
                self.report.failed.append((cls.__name__, msg, traceback.format_exc()))
                # 标记为失败，依赖它的类会被跳过
                self._instances[cls] = None

        return self.report

    def _topological_order(self) -> List[Type]:
        """
        使用 Kahn 算法计算实例化顺序。

        排序规则：
        - 按组件类型优先级：Mapper(0) < Service(1) < Controller(2)。
        - 同优先级按类名字母顺序，保证输出稳定可预测。
        - 若存在循环依赖，抛出 RuntimeError。

        返回：
            按依赖顺序排列的类列表。
        """
        type_rank = {
            ComponentType.MAPPER: 0,
            ComponentType.SERVICE: 1,
            ComponentType.CONTROLLER: 2,
        }

        in_degree: Dict[Type, int] = {cls: 0 for cls in self._classes}
        graph: Dict[Type, List[Type]] = {cls: [] for cls in self._classes}

        for cls, meta in self._classes.items():
            for dep_name, dep_annotation in meta.dependencies:
                dep_cls = self._resolve_dependency(dep_annotation)
                if dep_cls is None:
                    continue
                if dep_cls not in self._classes:
                    continue
                graph[dep_cls].append(cls)
                in_degree[cls] += 1

        # 优先队列：按组件优先级排序，再按类名排序以保证确定性
        queue = deque(
            sorted(
                [c for c, d in in_degree.items() if d == 0],
                key=lambda c: (type_rank.get(self._classes[c].component_type, 99), c.__name__),
            )
        )

        order = []
        while queue:
            cls = queue.popleft()
            order.append(cls)
            for dependent in sorted(graph[cls], key=lambda c: c.__name__):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # 检测循环依赖
        if len(order) != len(self._classes):
            unresolved = [c.__name__ for c in self._classes if c not in order]
            raise RuntimeError(f"检测到循环依赖：{unresolved}")

        return order

    def _resolve_dependency(self, annotation: Any) -> Optional[Type]:
        """
        将类型注解映射为已注册的类。

        支持：
        - 普通类类型（如 UserMapper）
        - 字符串前向引用（如 "UserMapper"）
        - typing.ForwardRef 对象

        当依赖模块被热重载后，原始注解中的类对象可能已被容器替换。
        此时通过类名再查找一次，保证跨模块依赖仍可解析。

        参数：
            annotation: 类型注解。

        返回：
            对应的类；如果无法解析则返回 None。
        """
        if isinstance(annotation, type):
            if annotation in self._classes:
                return annotation
            # 按类名兜底：处理热重载后旧类对象失效的情况
            return self._by_name.get(annotation.__name__)
        if isinstance(annotation, str):
            return self._by_name.get(annotation)
        # typing.ForwardRef
        if hasattr(annotation, "__forward_arg__"):
            return self._by_name.get(annotation.__forward_arg__)
        return None

    def _instantiate(self, cls: Type, meta: ClassMeta) -> Any:
        """
        实例化一个类，并注入构造参数与字段依赖。

        流程：
        1. 根据 ClassMeta.dependencies 准备 kwargs。
        2. 从 _instances 中查找依赖实例；若依赖失败（为 None）则抛出异常。
        3. 调用 cls(**kwargs) 创建实例。
        4. 对 inject_fields 中的字段进行字段注入。

        参数：
            cls: 待实例化的类。
            meta: 该类的 ClassMeta 元数据。

        返回：
            实例化后的对象。
        """
        kwargs = {}
        for dep_name, dep_annotation in meta.dependencies:
            dep_cls = self._resolve_dependency(dep_annotation)
            if dep_cls is None:
                continue
            dep_instance = self._instances.get(dep_cls)
            if dep_instance is None:
                raise RuntimeError(
                    f"{cls.__name__} 的依赖 {dep_cls.__name__} 不可用"
                )
            kwargs[dep_name] = dep_instance

        instance = cls(**kwargs)

        # 字段注入
        for field_name in meta.inject_fields:
            annotation = cls.__annotations__.get(field_name)
            dep_cls = self._resolve_dependency(annotation)
            if dep_cls and dep_cls in self._instances and self._instances[dep_cls] is not None:
                setattr(instance, field_name, self._instances[dep_cls])

        return instance

    def _add_to_call_graph(self, cls: Type, meta: ClassMeta) -> None:
        """
        将当前组件及其直接依赖记录到调用图。

        调用图用于生成作弊纸（cheat-sheet）和前端架构可视化。

        参数：
            cls: 已实例化的类。
            meta: 该类附加的 ClassMeta 元数据。
        """
        mod = meta.module_name
        ctype = meta.component_type.value
        self.report.call_graph.setdefault(mod, {}).setdefault(ctype, [])
        # 记录直接依赖，用于绘制调用图
        dep_names = []
        for dep_name, dep_annotation in meta.dependencies:
            dep_cls = self._resolve_dependency(dep_annotation)
            if dep_cls:
                dep_names.append(dep_cls.__name__)
        entry = f"{cls.__name__}({', '.join(dep_names) or 'None'})"
        self.report.call_graph[mod][ctype].append(entry)

    # ------------------------------------------------------------------
    # 运行时辅助函数
    # ------------------------------------------------------------------

    def get_instance(self, cls: Type) -> Any:
        """
        根据类获取已组装的实例。

        参数：
            cls: 已注册的类。

        返回：
            实例对象；若未组装或组装失败则返回 None。
        """
        return self._instances.get(cls)

    def get_instances_by_module(self, module_name: str) -> List[Any]:
        """
        获取某个模块下的所有成功实例。

        参数：
            module_name: 插件模块名。

        返回：
            该模块下所有成功实例的列表。
        """
        return [
            r.instance
            for r in (self.report.success if self.report else [])
            if r.module_name == module_name
        ]

    def reset(self) -> None:
        """
        清空容器状态。

        用于测试或完全重新加载插件前重置发现与组装结果。
        """
        self._classes.clear()
        self._instances.clear()
        self._by_name.clear()
        self.report = None
