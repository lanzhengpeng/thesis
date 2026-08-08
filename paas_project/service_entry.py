"""
8001 服务口单文件可执行程序入口
================================

用于 PyInstaller 打包。在导入 main 之前先把 bundle 中的 plugins/、database/
拷贝到可写运行时目录，并修正 sys.path 与环境变量。
"""

from __future__ import annotations

import sys


def _prepare_frozen_runtime() -> None:
    """冻结模式下准备可写运行时资源。"""
    from paas_core.frozen_runtime import ensure_runtime_assets

    ensure_runtime_assets()


if getattr(sys, "frozen", False):
    _prepare_frozen_runtime()

# 导入并启动服务口；plugins_dir 由 main.py 在冻结模式下自动从 runtime 获取
import main

if __name__ == "__main__":
    main.run_service_server(reload=False)
