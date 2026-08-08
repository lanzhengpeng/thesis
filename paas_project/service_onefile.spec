# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec：把 8001 服务口打包为单文件可执行程序。

用法：
    pyinstaller service_onefile.spec --clean --noconfirm

产物：dist/paas_service（macOS/Linux）或 dist/paas_service.exe（Windows）
"""

from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

SPEC_DIR = Path(SPECPATH)
PROJECT_ROOT = SPEC_DIR

# 需要显式收集的子模块（动态导入或框架深层依赖）
hiddenimports = (
    collect_submodules("uvicorn")
    + collect_submodules("watchdog")
    + collect_submodules("fastapi")
    + collect_submodules("starlette")
    + collect_submodules("pydantic")
    + collect_submodules("langgraph")
    + collect_submodules("langchain")
    + collect_submodules("langchain_core")
    + collect_submodules("langchain_openai")
    + [
        # 微内核动态注册的 Agent 工具
        "paas_core.agent.tools",
        "paas_core.agent.tools.calculator",
        "paas_core.agent.tools.database",
        "paas_core.agent.tools.search",
        "paas_core.agent.tools.tool_node",
        "paas_core.agent.tools.weather",
        # 常用 ASGI / 网络依赖
        "httptools",
        "websockets",
        "aiosqlite",
    ]
)

a = Analysis(
    ["service_entry.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        # 业务插件与业务 SQLite 数据库（按 data file 打包，保持 .py 源码可被动态加载）
        ("plugins", "plugins"),
        # LangGraph checkpoint 默认目录（运行时会重定向到可写位置）
        ("database", "database"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "PIL",
        "pytest",
        "numpy",
        "paas_core.server.system",
        "paas_core.finder",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="paas_service",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,
)
