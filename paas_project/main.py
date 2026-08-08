"""
微内核 PaaS 启动入口
====================

运行方式：

    # 同时启动系统口（8000）、服务口（8001）和 LangGraph dev server（8123）
    python main.py

    # 仅启动系统口
    python main.py --mode system

    # 仅启动服务口
    python main.py --mode service

    # 不启动 LangGraph dev server
    python main.py --no-langgraph

兼容旧入口（单端口聚合模式）：

    uvicorn paas_core.server.web_server:create_app --reload --port 8000
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# 确保项目根目录在 PYTHONPATH 中
ROOT = Path(__file__).resolve().parent
if getattr(sys, "frozen", False):
    # 冻结模式下 service_entry.py 已将运行时目录置顶 sys.path，
    # 这里只需保证 bundle 根目录可被导入，不要覆盖前面设置好的顺序。
    if str(ROOT) not in sys.path:
        sys.path.append(str(ROOT))
else:
    sys.path.insert(0, str(ROOT))

LANGGRAPH_PORT = int(os.environ.get("PAA_LANGGRAPH_PORT", "8123"))
LANGGRAPH_CONFIG = ROOT / "langgraph.json"

from paas_core.kernel.microkernel import MicroKernel
from paas_core.kernel.plugin_watcher import PluginWatcher
from paas_core.server.service.service_server import SERVICE_PORT, create_service_app


def boot(plugins_dir: Optional[Path] = None) -> MicroKernel:
    print("=" * 60)
    print("正在启动模块化微内核 PaaS...")
    print("=" * 60)

    kernel = MicroKernel(plugins_dir=plugins_dir)
    report = kernel.boot()

    print("\n[发现报告]")
    for mr in kernel.module_reports:
        status_icon = "✓" if mr.status == "ok" else "✗"
        print(f"  {status_icon} {mr.module_name}: {mr.status}")
        if mr.discovered_classes:
            for c in mr.discovered_classes:
                print(f"      - {c}")
        if mr.status == "failed":
            print(f"      错误: {mr.message}")

    print("\n[组装报告]")
    print(f"  成功: {len(report.success)}")
    print(f"  失败: {len(report.failed)}")
    for name, msg, _ in report.failed:
        print(f"    - {name}: {msg.split(chr(10))[0]}")

    print("\n[作弊纸]")
    cheat = kernel.generate_cheat_sheet()
    print(json.dumps(cheat, indent=2, ensure_ascii=False))

    return kernel


def run_system_server(reload: bool = False) -> None:
    """在独立进程中运行系统口（8000）。"""
    import uvicorn
    from paas_core.server.system.system_server import SYSTEM_PORT, create_system_app

    print(f"\n[系统口] 监听 0.0.0.0:{SYSTEM_PORT}")
    if reload:
        # uvicorn --reload 要求通过导入字符串加载 app
        uvicorn.run(
            "paas_core.server.system.system_app:app",
            host="0.0.0.0",
            port=SYSTEM_PORT,
            reload=True,
        )
    else:
        kernel = boot()
        app = create_system_app(kernel)
        uvicorn.run(app, host="0.0.0.0", port=SYSTEM_PORT, reload=False)


def run_service_server(plugins_dir: Optional[Path] = None, reload: bool = False) -> None:
    """在独立进程中运行服务口（8001），并监听插件变更实现热更新。"""
    import uvicorn

    if reload:
        # uvicorn --reload 要求通过导入字符串加载 app；PluginWatcher 在模块内启动
        uvicorn.run(
            "paas_core.server.service.service_app:app",
            host="0.0.0.0",
            port=SERVICE_PORT,
            reload=True,
        )
        return

    if plugins_dir is None and getattr(sys, "frozen", False):
        from paas_core.frozen_runtime import ensure_runtime_assets

        _, plugins_dir = ensure_runtime_assets()

    kernel = boot(plugins_dir=plugins_dir)
    app, dispatcher = create_service_app(kernel)

    # 文件监听器：当 plugins/ 下任何 .py 文件变更时，重建内核并原子替换分发器
    def _on_plugin_changed(plugin_name: str, event_type: str) -> None:
        print(f"\n[服务口] 检测到插件变更: {plugin_name} ({event_type})，正在热更新...")
        try:
            # 使用完整重启而非单插件重载，确保跨模块依赖重新解析
            report = kernel.reboot()

            if report.failed:
                failed_names = [name for name, _, _ in report.failed]
                print(f"[服务口] 热更新完成，但以下组件失败: {failed_names}")
            else:
                print(f"[服务口] 热更新成功: {len(report.success)} 个组件已加载")

            # 原子替换 dispatcher 持有的内核引用，后续请求立即使用新内核
            dispatcher.set_kernel(kernel)
        except Exception as exc:
            print(f"[服务口] 热更新失败，保留旧内核: {exc}")

    watcher = PluginWatcher(
        plugins_dir=kernel.plugins_dir,
        callback=_on_plugin_changed,
    )
    watcher.start()

    print(f"\n[服务口] 监听 0.0.0.0:{SERVICE_PORT}")
    try:
        uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT, reload=False)
    finally:
        watcher.stop()


def _start_langgraph_server(port: int = LANGGRAPH_PORT) -> subprocess.Popen:
    """启动 LangGraph dev server（供前端 @langchain/langgraph-sdk 连接）。"""
    if not LANGGRAPH_CONFIG.exists():
        raise FileNotFoundError(f"LangGraph 配置文件不存在: {LANGGRAPH_CONFIG}")

    cmd = [
        sys.executable,
        "-m",
        "langgraph_cli",
        "dev",
        "--config",
        str(LANGGRAPH_CONFIG),
        "--port",
        str(port),
        "--host",
        "127.0.0.1",
        "--no-browser",
        "--no-reload",
    ]
    print(f"\n[LangGraph] 启动 LangGraph dev server，监听 127.0.0.1:{port}")
    # 直接继承当前 stdout/stderr，让 LangGraph 日志与 PaaS 日志混合同屏输出
    return subprocess.Popen(cmd, cwd=str(ROOT))


def _start_processes(reload: bool = False, start_langgraph: bool = True) -> None:
    """同时启动系统口、服务口，以及可选的 LangGraph dev server。"""
    langgraph_proc: Optional[subprocess.Popen] = None

    def _cleanup_langgraph() -> None:
        if langgraph_proc is not None and langgraph_proc.poll() is None:
            print("\n[LangGraph] 正在关闭 dev server...")
            langgraph_proc.terminate()
            try:
                langgraph_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                langgraph_proc.kill()
                langgraph_proc.wait()

    if start_langgraph:
        try:
            langgraph_proc = _start_langgraph_server()
            # 等待 server 就绪（最多 30 秒）
            _wait_for_langgraph(LANGGRAPH_PORT, timeout=30)
        except Exception as exc:
            print(f"[LangGraph] 启动失败: {exc}")
            _cleanup_langgraph()
            raise

    try:
        if reload:
            # uvicorn --reload 需要正确的 stdin 继承，multiprocessing spawn 会关闭 stdin 导致报错。
            # reload 模式下改为用 subprocess 启动两个独立的 main.py 进程。
            print("[主进程] reload 模式：将分别启动系统口和服务口两个独立进程")
            system_cmd = [sys.executable, str(ROOT / "main.py"), "--mode", "system", "--reload"]
            service_cmd = [sys.executable, str(ROOT / "main.py"), "--mode", "service", "--reload"]

            procs = [
                subprocess.Popen(system_cmd, cwd=str(ROOT)),
                subprocess.Popen(service_cmd, cwd=str(ROOT)),
            ]
            try:
                for p in procs:
                    p.wait()
            except KeyboardInterrupt:
                print("\n[主进程] 收到中断信号，正在关闭子进程...")
                for p in procs:
                    p.terminate()
                for p in procs:
                    p.wait()
                print("[主进程] 已关闭")
            finally:
                _cleanup_langgraph()
            return

        multiprocessing.set_start_method("spawn", force=True)

        system_proc = multiprocessing.Process(
            target=run_system_server, name="system-server", kwargs={"reload": False}
        )
        service_proc = multiprocessing.Process(
            target=run_service_server, name="service-server", kwargs={"reload": False}
        )

        system_proc.start()
        service_proc.start()

        try:
            system_proc.join()
            service_proc.join()
        except KeyboardInterrupt:
            print("\n[主进程] 收到中断信号，正在关闭子进程...")
            system_proc.terminate()
            service_proc.terminate()
            system_proc.join()
            service_proc.join()
            print("[主进程] 已关闭")
    finally:
        _cleanup_langgraph()


def _wait_for_langgraph(port: int, timeout: float = 30.0) -> None:
    """轮询等待 LangGraph server 健康检查通过。"""
    import time
    import urllib.request

    url = f"http://127.0.0.1:{port}/ok"
    deadline = time.time() + timeout
    last_error = ""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    print(f"[LangGraph] dev server 已就绪: {url}")
                    return
        except Exception as exc:
            last_error = str(exc)
        time.sleep(0.5)
    raise RuntimeError(f"LangGraph server 在 {timeout}s 内未就绪: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="模块化微内核 PaaS 启动入口")
    parser.add_argument(
        "--mode",
        choices=["all", "system", "service"],
        default="all",
        help="启动模式：all（默认，双进程）、system（仅系统口）、service（仅服务口）",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="开启 uvicorn 代码热重载（开发模式）",
    )
    parser.add_argument(
        "--no-langgraph",
        action="store_true",
        help="禁止在 mode=all 时自动启动 LangGraph dev server",
    )
    args = parser.parse_args()

    if args.mode == "all":
        _start_processes(reload=args.reload, start_langgraph=not args.no_langgraph)
    elif args.mode == "system":
        run_system_server(reload=args.reload)
    elif args.mode == "service":
        run_service_server(reload=args.reload)


if __name__ == "__main__":
    main()
