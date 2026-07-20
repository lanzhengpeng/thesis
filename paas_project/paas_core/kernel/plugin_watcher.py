"""
插件文件监听器
==============

为 8001 服务口提供插件变更自动感知能力。

基于 watchdog 递归监听 plugins/ 目录，当任何 .py 文件发生
创建、修改或删除时，触发回调函数重建内核。
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable, Optional, Set


try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "plugin_watcher 依赖 watchdog，请执行：pip install watchdog>=4.0.0"
    ) from exc


# 默认去抖间隔（秒）：在该时间内发生的多次事件只会触发一次重建
DEFAULT_DEBOUNCE_SECONDS = 1.0


class PluginEventHandler(FileSystemEventHandler):
    """
    watchdog 事件处理器。

    过滤 plugins/ 目录下的 .py 文件事件，合并去抖后调用用户回调。
    """

    def __init__(
        self,
        callback: Callable[[str, str], None],
        debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS,
    ):
        """
        初始化事件处理器。

        参数：
            callback: 回调函数，接收 (plugin_name, event_type)。
            debounce_seconds: 去抖间隔，单位秒。
        """
        super().__init__()
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._pending_plugins: Set[str] = set()
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

    def on_any_event(self, event: FileSystemEvent) -> None:
        """
        处理任意文件系统事件。

        只关注 .py 文件；忽略目录操作与临时文件。
        """
        if event.is_directory:
            return

        src_path = Path(event.src_path)
        if src_path.suffix != ".py":
            return

        plugin_name = self._extract_plugin_name(src_path)
        if plugin_name is None:
            return

        event_type = event.event_type  # created / modified / deleted / moved
        with self._lock:
            self._pending_plugins.add(plugin_name)
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(
                self.debounce_seconds,
                self._fire_callbacks,
                args=(event_type,),
            )
            self._timer.start()

    def _extract_plugin_name(self, file_path: Path) -> Optional[str]:
        """
        从文件路径提取插件目录名。

        plugins/<plugin_name>/<file>.py -> plugin_name

        参数：
            file_path: 发生变更的 .py 文件路径。

        返回：
            插件目录名；若不在 plugins 下则返回 None。
        """
        try:
            # 找到 plugins 之后的第二段目录名
            parts = file_path.parts
            idx = parts.index("plugins")
            if len(parts) <= idx + 1:
                return None
            return parts[idx + 1]
        except ValueError:
            return None

    def _fire_callbacks(self, event_type: str) -> None:
        """
        去抖结束后触发回调。

        对每个受影响的插件调用一次 callback。
        """
        with self._lock:
            plugins = list(self._pending_plugins)
            self._pending_plugins.clear()
            self._timer = None

        for plugin_name in plugins:
            try:
                self.callback(plugin_name, event_type)
            except Exception as exc:
                print(f"[PluginWatcher] 处理插件 {plugin_name} 变更失败: {exc}")


class PluginWatcher:
    """
    插件目录监听器。

    封装 watchdog Observer，提供 start/stop 生命周期。
    """

    def __init__(
        self,
        plugins_dir: Path,
        callback: Callable[[str, str], None],
        debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS,
    ):
        """
        初始化监听器。

        参数：
            plugins_dir: 插件根目录。
            callback: 变更回调函数，接收 (plugin_name, event_type)。
            debounce_seconds: 去抖间隔。
        """
        self.plugins_dir = Path(plugins_dir)
        self._handler = PluginEventHandler(callback, debounce_seconds)
        self._observer = Observer()

    def start(self) -> None:
        """
        启动监听。

        如果 plugins_dir 不存在，则不启动并打印警告。
        """
        if not self.plugins_dir.exists():
            print(f"[PluginWatcher] 警告：{self.plugins_dir} 不存在，跳过监听")
            return

        self._observer.schedule(self._handler, str(self.plugins_dir), recursive=True)
        self._observer.start()
        print(f"[PluginWatcher] 开始监听 {self.plugins_dir}（去抖 {self._handler.debounce_seconds}s）")

    def stop(self) -> None:
        """
        停止监听。
        """
        self._observer.stop()
        self._observer.join()
