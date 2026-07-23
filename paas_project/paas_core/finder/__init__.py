"""
项目文件查找器（Finder）
========================

提供对项目文件的受限增删改查能力。所有操作必须在允许的根目录（默认为
项目根目录下的 plugins/）内进行，并通过路径解析防止目录遍历攻击。
"""

from __future__ import annotations

from paas_core.finder.file_service import FileService
from paas_core.finder.schemas import (
    DirectoryEntry,
    FileContentOut,
    FileWriteIn,
    MoveIn,
    PathIn,
    PathOut,
)

__all__ = [
    "DirectoryEntry",
    "FileContentOut",
    "FileService",
    "FileWriteIn",
    "MoveIn",
    "PathIn",
    "PathOut",
]
