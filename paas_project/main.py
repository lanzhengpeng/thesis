"""
微内核 PaaS 启动入口
====================

运行方式：

    # 同时启动系统口（8000）和服务口（8001）
    python main.py

    # 仅启动系统口
    python main.py --mode system

    # 仅启动服务口
    python main.py --mode service

兼容旧入口（单端口聚合模式）：

    uvicorn paas_core.web_server:create_app --reload --port 8000
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import sys
from pathlib import Path

# 确保项目根目录在 PYTHONPATH 中
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from paas_core.microkernel import MicroKernel
from paas_core.service_server import SERVICE_PORT, create_service_app
from paas_core.system_server import SYSTEM_PORT, create_system_app


def boot() -> MicroKernel:
    print("=" * 60)
    print("正在启动模块化微内核 PaaS...")
    print("=" * 60)

    kernel = MicroKernel()
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


def run_system_server() -> None:
    """在独立进程中运行系统口（8000）。"""
    kernel = boot()
    app = create_system_app(kernel)
    import uvicorn

    print(f"\n[系统口] 监听 0.0.0.0:{SYSTEM_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=SYSTEM_PORT)


def run_service_server() -> None:
    """在独立进程中运行服务口（8001）。"""
    kernel = boot()
    app = create_service_app(kernel)
    import uvicorn

    print(f"\n[服务口] 监听 0.0.0.0:{SERVICE_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)


def _start_processes() -> None:
    """以 spawn 方式同时启动两个服务进程。"""
    multiprocessing.set_start_method("spawn", force=True)

    system_proc = multiprocessing.Process(target=run_system_server, name="system-server")
    service_proc = multiprocessing.Process(target=run_service_server, name="service-server")

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


def main() -> None:
    parser = argparse.ArgumentParser(description="模块化微内核 PaaS 启动入口")
    parser.add_argument(
        "--mode",
        choices=["all", "system", "service"],
        default="all",
        help="启动模式：all（默认，双进程）、system（仅系统口）、service（仅服务口）",
    )
    args = parser.parse_args()

    if args.mode == "all":
        _start_processes()
    elif args.mode == "system":
        run_system_server()
    elif args.mode == "service":
        run_service_server()


if __name__ == "__main__":
    main()
