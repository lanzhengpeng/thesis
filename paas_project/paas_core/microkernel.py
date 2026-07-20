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

from .di_container import AssemblyReport, DIContainer
from .sdk import ComponentType, get_meta, is_component


PLUGINS_DIR = Path(__file__).resolve().parent.parent / "plugins"


@dataclass
class ModuleLoadReport:
    """模块加载报告。"""

    module_name: str
    status: str  # "ok" 或 "failed"
    message: str = ""
    trace: str = ""
    discovered_classes: List[str] = field(default_factory=list)


class MicroKernel:
    def __init__(self, plugins_dir: Optional[Path] = None):
        self.plugins_dir = Path(plugins_dir or PLUGINS_DIR)
        self.container = DIContainer()
        self.module_reports: List[ModuleLoadReport] = []
        self._loaded_module_specs: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # 启动生命周期
    # ------------------------------------------------------------------

    def boot(self) -> AssemblyReport:
        """完整启动：扫描插件、导入模块、组装实例。"""
        self._scan_plugins()
        return self.container.assemble()

    def _scan_plugins(self) -> None:
        """遍历 plugins/ 目录下的所有插件模块。"""
        if not self.plugins_dir.exists():
            return

        for plugin_dir in sorted(self.plugins_dir.iterdir()):
            if not plugin_dir.is_dir():
                continue
            if plugin_dir.name.startswith("_"):
                continue
            self._load_plugin(plugin_dir)

    def _load_plugin(self, plugin_dir: Path) -> None:
        """加载单个插件目录下的所有 Python 文件。"""
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
        """导入插件目录下的一个 Python 文件。"""
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

    def reload_plugin(self, plugin_name: str) -> AssemblyReport:
        """重新加载单个插件并重新组装整个系统。"""
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
        """卸载一个插件并重新组装系统。"""
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
        }

    # ------------------------------------------------------------------
    # 内省辅助函数
    # ------------------------------------------------------------------

    def get_loaded_modules(self) -> List[str]:
        """获取所有成功加载的模块名。"""
        return [r.module_name for r in self.module_reports if r.status == "ok"]

    def get_failed_modules(self) -> List[dict]:
        """获取所有加载失败的模块信息。"""
        return [
            {"module": r.module_name, "error": r.message}
            for r in self.module_reports
            if r.status == "failed"
        ]
