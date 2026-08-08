"""
冻结运行时资源准备
====================

供 PyInstaller 单文件可执行程序使用：
- 检测当前是否处于 PyInstaller 冻结环境（sys.frozen / sys._MEIPASS）
- 把只读 bundle 中的 plugins/、database/ 拷贝到可写运行时目录
- 设置环境变量使业务 DB、LangGraph checkpoint DB 指向可写位置
- 把运行时目录置顶 sys.path，确保动态加载的插件来自可写副本
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Tuple


def is_frozen() -> bool:
    """当前是否运行在 PyInstaller 等冻结环境中。"""
    return getattr(sys, "frozen", False)


def bundled_root() -> Path:
    """
    获取 bundle 根目录。

    - 冻结模式下为 sys._MEIPASS（PyInstaller 解压到的临时目录）
    - 非冻结模式下为项目根目录（paas_project/）
    """
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


def executable_dir() -> Path:
    """获取当前可执行文件所在目录；非冻结环境下返回项目根目录。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return bundled_root()


def runtime_root() -> Path:
    """
    确定可写运行时根目录。

    优先级：
    1. PAA_RUNTIME_DIR 环境变量
    2. 可执行文件同目录下的 paas_runtime/
    """
    env = os.environ.get("PAA_RUNTIME_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return executable_dir() / "paas_runtime"


def ensure_runtime_assets() -> Tuple[Path, Path]:
    """
    确保运行时资源就绪。

    流程：
    1. 计算 bundle 根目录与运行时根目录
    2. 如运行时 plugins/ 不存在，从 bundle 完整拷贝
    3. 创建运行时 database/ 目录
    4. 将运行时根目录置顶 sys.path
    5. 设置 PAA_LANGGRAPH_CHECKPOINT_DB 指向可写位置

    返回：
        (runtime_root, plugins_dir)
    """
    internal_root = bundled_root()
    rt_root = runtime_root()
    plugins_src = internal_root / "plugins"
    plugins_dst = rt_root / "plugins"

    # 拷贝插件目录（含 plugins/database/paas.sqlite 等业务数据文件）
    if plugins_src.exists() and not plugins_dst.exists():
        rt_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(plugins_src, plugins_dst)
        print(f"[frozen_runtime] 已拷贝插件到: {plugins_dst}")

    # 确保 database/ 目录存在（LangGraph checkpoint 等）
    db_dir = rt_root / "database"
    db_dir.mkdir(parents=True, exist_ok=True)

    # 置顶运行时根目录，使 plugins.* 优先从可写副本加载
    rt_str = str(rt_root)
    if rt_str in sys.path:
        sys.path.remove(rt_str)
    sys.path.insert(0, rt_str)

    # 把 LangGraph checkpoint DB 固定到可写目录
    checkpoint_db = db_dir / "langgraph_checkpoints.sqlite"
    os.environ.setdefault(
        "PAA_LANGGRAPH_CHECKPOINT_DB",
        str(checkpoint_db),
    )

    return rt_root, plugins_dst
