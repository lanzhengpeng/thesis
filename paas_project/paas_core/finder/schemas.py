"""
Finder 数据模型
==============

定义文件 CRUD 接口的请求与响应结构。
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class EntryType(str, Enum):
    """文件系统条目类型。"""

    FILE = "file"
    DIRECTORY = "directory"


class PathIn(BaseModel):
    """仅包含路径的请求模型。"""

    path: str = Field(
        ...,
        description="相对于允许根目录的路径，例如 'user_module/main.py' 或空字符串表示根目录",
    )

    @field_validator("path")
    @classmethod
    def _normalize_path(cls, value: str) -> str:
        return value.replace("\\", "/").lstrip("/")


class FileWriteIn(PathIn):
    """写入文件请求模型。"""

    content: str = Field(default="", description="文件内容")
    encoding: str = Field(default="utf-8", description="文件编码")
    overwrite: bool = Field(default=True, description="是否覆盖已存在文件")


class MoveIn(BaseModel):
    """重命名/移动请求模型。"""

    src: str = Field(..., description="源路径")
    dst: str = Field(..., description="目标路径")

    @field_validator("src", "dst")
    @classmethod
    def _normalize_path(cls, value: str) -> str:
        return value.replace("\\", "/").lstrip("/")


class DirectoryEntry(BaseModel):
    """目录列表中的单个条目。"""

    name: str
    type: EntryType
    path: str
    size: Optional[int] = None


class FileContentOut(BaseModel):
    """读取文件响应模型。"""

    path: str
    content: str
    encoding: str
    size: int


class PathOut(BaseModel):
    """操作成功后的路径响应模型。"""

    path: str
    message: str
