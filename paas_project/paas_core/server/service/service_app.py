"""
服务口热重载入ロ。

uvicorn --reload 要求以导入字符串形式提供 app。本模块导入时启动内核、创建服务口 app，
并启动 PluginWatcher 监听 plugins/ 目录变更，在子进程内完成热更新。
"""

import atexit

from paas_core.kernel.microkernel import MicroKernel
from paas_core.kernel.plugin_watcher import PluginWatcher
from paas_core.server.service.service_server import create_service_app

kernel = MicroKernel()
kernel.boot()
app, dispatcher = create_service_app(kernel)


def _on_plugin_changed(plugin_name: str, event_type: str) -> None:
    print(f"\n[服务口] 检测到插件变更: {plugin_name} ({event_type})，正在热更新...")
    try:
        report = kernel.reboot()
        if report.failed:
            failed_names = [name for name, _, _ in report.failed]
            print(f"[服务口] 热更新完成，但以下组件失败: {failed_names}")
        else:
            print(f"[服务口] 热更新成功: {len(report.success)} 个组件已加载")
        dispatcher.set_kernel(kernel)
    except Exception as exc:
        print(f"[服务口] 热更新失败，保留旧内核: {exc}")


watcher = PluginWatcher(
    plugins_dir=kernel.plugins_dir,
    callback=_on_plugin_changed,
)
watcher.start()
atexit.register(watcher.stop)
