"""
微内核
======

负责扫描 AI 沙箱（plugins/）、导入模块、捕获失败，并编排依赖注入容器完成组装。

内核本身从不执行 AI 生成的业务逻辑，只负责加载类并将实例化委托给 DI 容器。
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from paas_core.sdk import ComponentType, get_meta, is_component

from .di_container import AssemblyReport, DIContainer


PLUGINS_DIR = Path(__file__).resolve().parent.parent.parent / "plugins"


@dataclass
class ModuleLoadReport:
    """
    单个插件模块的加载报告。

    字段说明：
        module_name: 插件目录名。
        status: "ok" 或 "failed"。
        message: 失败时的错误信息。
        trace: 失败时的完整堆栈。
        discovered_classes: 该模块下发现并注册的组件列表。
    """

    module_name: str
    status: str  # "ok" 或 "failed"
    message: str = ""
    trace: str = ""
    discovered_classes: List[str] = field(default_factory=list)


class MicroKernel:
    """
    微内核。

    职责：
    - 扫描 plugins/ 目录，按插件隔离导入 Python 文件。
    - 将发现的类交给 DIContainer 注册。
    - 捕获单个插件的异常，避免影响全局系统。
    - 支持插件热重载与卸载。
    - 生成作弊纸（cheat-sheet）供前端与 AI 参考。
    """

    def __init__(self, plugins_dir: Optional[Path] = None):
        """
        初始化微内核。

        参数：
            plugins_dir: 插件目录；默认使用项目根目录下的 plugins/。
        """
        self.plugins_dir = Path(plugins_dir or PLUGINS_DIR)
        self.container = DIContainer()
        self.module_reports: List[ModuleLoadReport] = []
        self._loaded_module_specs: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # 启动生命周期
    # ------------------------------------------------------------------

    def boot(self) -> AssemblyReport:
        """
        完整启动：扫描插件、导入模块、组装实例。

        返回：
            DI 容器生成的 AssemblyReport。
        """
        self._scan_plugins()
        return self.container.assemble()

    def _scan_plugins(self) -> None:
        """
        遍历 plugins/ 目录下的所有插件模块。

        跳过非目录项与以下划线开头的目录。
        """
        if not self.plugins_dir.exists():
            return

        for plugin_dir in sorted(self.plugins_dir.iterdir()):
            if not plugin_dir.is_dir():
                continue
            if plugin_dir.name.startswith("_"):
                continue
            self._load_plugin(plugin_dir)

    def _load_plugin(self, plugin_dir: Path) -> None:
        """
        加载单个插件目录下的所有 Python 文件。

        流程：
        1. 遍历插件目录中的 .py 文件。
        2. 导入每个文件并注册其中带装饰器的类。
        3. 收集该插件下发现的所有组件名称用于报告。
        4. 若过程中抛出异常，将该插件标记为失败，不影响其他插件。

        参数：
            plugin_dir: 插件目录的 Path 对象。
        """
        module_name = plugin_dir.name
        report = ModuleLoadReport(module_name=module_name, status="ok")

        try:
            py_files = sorted([p for p in plugin_dir.iterdir() if p.suffix == ".py"])
            for py_file in py_files:
                self._import_file(module_name, py_file)
                # 导入后注册该模块中新增的带装饰器类
                mod_key = f"plugins.{module_name}.{py_file.stem}"
                if mod_key in sys.modules:
                    self.container.discover_module_classes(sys.modules[mod_key])

            # 收集该插件下所有已发现类的名称，用于报告
            for cls, meta in self.container.all_classes().items():
                if meta.module_name == module_name:
                    report.discovered_classes.append(
                        f"{meta.component_type.value}:{cls.__name__}"
                    )

        except Exception as exc:
            report.status = "failed"
            report.message = str(exc)
            report.trace = traceback.format_exc()

        self.module_reports.append(report)

    def _import_file(self, plugin_name: str, py_file: Path, force: bool = False) -> None:
        """
        导入插件目录下的一个 Python 文件。

        参数：
            plugin_name: 插件目录名。
            py_file: Python 文件的 Path 对象。
            force: 是否强制重新导入；热重载时传 True。

        注意：
            初次启动时，如果某个模块已经通过插件内的相对导入被加载过，
            则不要重复执行。重复执行会产生重复的类对象，破坏依赖解析。
        """
        module_path = f"plugins.{plugin_name}.{py_file.stem}"

        # 初次启动时，如果某个模块已经通过插件内的相对导入被加载过，
        # 则不要重复执行。重复执行会产生重复的类对象，破坏依赖解析。
        if not force and module_path in sys.modules:
            self._loaded_module_specs[module_path] = sys.modules[module_path]
            return

        # 清除缓存模块以支持热重载
        if module_path in sys.modules:
            del sys.modules[module_path]

        spec = importlib.util.spec_from_file_location(module_path, py_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法为 {py_file} 创建模块规格")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_path] = module
        spec.loader.exec_module(module)
        self._loaded_module_specs[module_path] = module

    # ------------------------------------------------------------------
    # 动态操作
    # ------------------------------------------------------------------

    def load_plugin(self, plugin_name: str) -> AssemblyReport:
        """
        首次加载一个新插件目录。

        与 reload_plugin 不同，本方法不会清理已有插件的状态，
        适用于监听线程发现全新插件目录的场景。

        参数：
            plugin_name: 插件目录名。

        返回：
            重新组装后的 AssemblyReport。
        """
        plugin_dir = self.plugins_dir / plugin_name
        if not plugin_dir.exists():
            raise FileNotFoundError(f"找不到插件 {plugin_name}")

        self._load_plugin(plugin_dir)
        return self.container.assemble()

    def reboot(self) -> AssemblyReport:
        """
        完全重启微内核。

        流程：
        1. 清空 DI 容器注册表与实例。
        2. 从 sys.modules 中移除所有 plugins.* 模块。
        3. 重新扫描 plugins/ 目录并重新组装。

        适用于 8001 服务口的动态热更新：监听线程在后台创建新内核或
        重置当前内核后，无需重启进程即可生效。

        返回：
            重新组装后的 AssemblyReport。
        """
        self.container.reset()
        self.module_reports.clear()
        self._loaded_module_specs.clear()

        # 清理所有插件模块缓存，确保重新执行最新代码
        for key in list(sys.modules.keys()):
            if key.startswith("plugins."):
                del sys.modules[key]

        self._scan_plugins()
        return self.container.assemble()

    def reload_plugin(self, plugin_name: str) -> AssemblyReport:
        """
        重新加载单个插件并重新组装整个系统。

        流程：
        1. 从容器注册表中移除该插件的所有类与实例。
        2. 从 sys.modules 中移除该插件的所有模块。
        3. 重新导入并重新组装。

        参数：
            plugin_name: 插件目录名。

        返回：
            重新组装后的 AssemblyReport。
        """
        plugin_dir = self.plugins_dir / plugin_name
        if not plugin_dir.exists():
            raise FileNotFoundError(f"找不到插件 {plugin_name}")

        # 从容器的注册表中移除该插件的类
        stale_classes = [
            cls
            for cls, meta in self.container.all_classes().items()
            if meta.module_name == plugin_name
        ]
        for cls in stale_classes:
            del self.container._classes[cls]
            self.container._by_name.pop(cls.__name__, None)
            self.container._instances.pop(cls, None)

        # 从 sys.modules 中移除该插件的所有模块
        prefixes_to_remove = [
            f"plugins.{plugin_name}",
        ]
        for key in list(sys.modules.keys()):
            if any(key.startswith(p) for p in prefixes_to_remove):
                del sys.modules[key]

        # 重新导入并重新组装
        self._load_plugin(plugin_dir)
        return self.container.assemble()

    def unload_plugin(self, plugin_name: str) -> AssemblyReport:
        """
        卸载一个插件并重新组装系统。

        参数：
            plugin_name: 插件目录名。

        返回：
            卸载后的 AssemblyReport。
        """
        stale_classes = [
            cls
            for cls, meta in self.container.all_classes().items()
            if meta.module_name == plugin_name
        ]
        for cls in stale_classes:
            del self.container._classes[cls]
            self.container._by_name.pop(cls.__name__, None)
            self.container._instances.pop(cls, None)

        for key in list(sys.modules.keys()):
            if key.startswith(f"plugins.{plugin_name}"):
                del sys.modules[key]

        return self.container.assemble()

    # ------------------------------------------------------------------
    # 作弊纸生成
    # ------------------------------------------------------------------

    def generate_cheat_sheet(self) -> Dict[str, Any]:
        """
        生成全局调用图 / API 映射，供下一次 AI 唤醒时参考。

        返回字典包含：
            status: 状态字符串。
            modules: 已加载与失败模块列表。
            counts: Controller / Service / Mapper 数量。
            call_graph: 模块级调用关系图。
            api_map: 所有 Controller 方法对应的 HTTP 接口列表。

        返回：
            作弊纸数据字典。
        """
        report = self.container.report
        if report is None:
            return {}

        controllers = report.get_controllers()
        services = report.get_services()
        mappers = report.get_mappers()

        api_map = []
        for rec in controllers:
            meta = get_meta(rec.instance)
            for method in meta.methods:
                full_path = (meta.path + method.path).replace("//", "/")
                api_map.append(
                    {
                        "module": meta.module_name,
                        "method": method.http_method,
                        "path": full_path,
                        "handler": f"{rec.instance.__class__.__name__}.{method.name}",
                    }
                )

        components = self._build_component_view(report)

        return {
            "status": "ok",
            "modules": {
                "loaded": [r.module_name for r in self.module_reports if r.status == "ok"],
                "failed": [
                    {"module": r.module_name, "error": r.message}
                    for r in self.module_reports
                    if r.status == "failed"
                ],
            },
            "counts": {
                "controllers": len(controllers),
                "services": len(services),
                "mappers": len(mappers),
            },
            "call_graph": report.call_graph,
            "api_map": api_map,
            "components": components,
        }

    def _build_component_view(self, report: AssemblyReport) -> List[Dict[str, Any]]:
        """
        为每个已注册的 CSM 组件生成结构化元数据，包括构造参数、字段注入与 Controller 方法。
        """

        def _annotation_name(annotation: Any) -> str:
            if isinstance(annotation, type):
                return annotation.__name__
            if isinstance(annotation, str):
                return annotation
            if hasattr(annotation, "__forward_arg__"):
                return annotation.__forward_arg__
            return str(annotation)

        assembled_names = {r.instance.__class__.__name__ for r in report.success}
        components: List[Dict[str, Any]] = []

        for cls, meta in self.container.all_classes().items():
            constructor_params = [
                {"name": name, "type": _annotation_name(annotation)}
                for name, annotation in meta.dependencies
                if name not in meta.inject_fields
            ]

            inject_fields = []
            for field_name in meta.inject_fields:
                annotation = cls.__annotations__.get(field_name)
                inject_fields.append(
                    {"name": field_name, "type": _annotation_name(annotation)}
                )

            item: Dict[str, Any] = {
                "name": cls.__name__,
                "type": meta.component_type.value,
                "module": meta.module_name,
                "base_path": meta.path,
                "assembled": cls.__name__ in assembled_names,
                "constructor_params": constructor_params,
                "inject_fields": inject_fields,
                "methods": [],
            }

            for method in meta.methods:
                method_item: Dict[str, Any] = {
                    "name": method.name,
                    "feature": method.feature,
                    "params": method.params,
                    "calls": method.calls,
                    "sql": method.sql,
                }
                if meta.component_type == ComponentType.CONTROLLER:
                    method_item["http_method"] = method.http_method
                    method_item["path"] = (meta.path + (method.path or "")).replace("//", "/")
                item["methods"].append(method_item)

            components.append(item)

        components.sort(key=lambda c: (c["module"], c["type"], c["name"]))
        return components

    # ------------------------------------------------------------------
    # 内省辅助函数
    # ------------------------------------------------------------------

    def get_loaded_modules(self) -> List[str]:
        """
        获取所有成功加载的模块名。

        返回：
            模块名字符串列表。
        """
        return [r.module_name for r in self.module_reports if r.status == "ok"]

    def get_failed_modules(self) -> List[dict]:
        """
        获取所有加载失败的模块信息。

        返回：
            包含 module 与 error 字段的字典列表。
        """
        return [
            {"module": r.module_name, "error": r.message}
            for r in self.module_reports
            if r.status == "failed"
        ]
