"""
Finder 文件服务
==============

实现对项目文件的安全增删改查。所有路径均被解析为绝对路径，并校验其必须
落在允许的根目录内；任何试图越界访问的操作都会抛出 PathNotAllowedError。
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List

from paas_core.finder.schemas import DirectoryEntry, EntryType


class FinderError(Exception):
    """Finder 业务异常基类。"""

    pass


class PathNotAllowedError(FinderError):
    """请求路径超出允许的操作范围。"""

    pass


class PathNotFoundError(FinderError):
    """请求路径不存在。"""

    pass


class PathAlreadyExistsError(FinderError):
    """目标路径已存在。"""

    pass


class NotAFileError(FinderError):
    """期望是文件但实际不是。"""

    pass


class NotADirectoryError(FinderError):
    """期望是目录但实际不是。"""

    pass


class FileService:
    """
    受限文件系统服务。

    参数：
        base_dir: 允许操作的根目录。所有请求路径均会被解析并限制在此目录内。
    """

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir).resolve()
        if not self.base_dir.exists():
            self.base_dir.mkdir(parents=True, exist_ok=True)
        if not self.base_dir.is_dir():
            raise ValueError(f"base_dir 必须是目录: {self.base_dir}")

    # ------------------------------------------------------------------
    # 路径安全校验
    # ------------------------------------------------------------------

    def _resolve(self, relative_path: str) -> Path:
        """
        将相对路径解析为绝对路径，并确保落在 base_dir 内。

        说明：
        - 先对 relative_path 做 strip，禁止以 / 开头。
        - 使用 base_dir / relative_path 后再 resolve，防止 ../ 等目录遍历。
        """
        relative_path = relative_path.replace("\\", "/").lstrip("/")
        target = (self.base_dir / relative_path).resolve()

        # 确保 target 是 base_dir 本身或位于 base_dir 之下
        if target != self.base_dir and not str(target).startswith(
            str(self.base_dir) + "/"
        ):
            raise PathNotAllowedError(f"路径不允许访问: {relative_path}")

        return target

    def _require_exists(self, path: Path) -> None:
        if not path.exists():
            raise PathNotFoundError(f"路径不存在: {self._relative(path)}")

    def _require_not_exists(self, path: Path) -> None:
        if path.exists():
            raise PathAlreadyExistsError(f"路径已存在: {self._relative(path)}")

    def _relative(self, path: Path) -> str:
        """返回相对 base_dir 的字符串路径。"""
        try:
            return path.relative_to(self.base_dir).as_posix()
        except ValueError:
            return str(path)

    # ------------------------------------------------------------------
    # 查询操作
    # ------------------------------------------------------------------

    def list_directory(self, relative_path: str = "") -> List[DirectoryEntry]:
        """列出目录内容。"""
        target = self._resolve(relative_path)
        self._require_exists(target)
        if not target.is_dir():
            raise NotADirectoryError(f"不是目录: {self._relative(target)}")

        entries: List[DirectoryEntry] = []
        for child in sorted(target.iterdir()):
            entry_type = EntryType.DIRECTORY if child.is_dir() else EntryType.FILE
            size = child.stat().st_size if entry_type == EntryType.FILE else None
            entries.append(
                DirectoryEntry(
                    name=child.name,
                    type=entry_type,
                    path=self._relative(child),
                    size=size,
                )
            )
        return entries

    def read_file(
        self, relative_path: str, encoding: str = "utf-8"
    ) -> tuple[str, int]:
        """读取文本文件内容。返回 (content, size)。"""
        target = self._resolve(relative_path)
        self._require_exists(target)
        if target.is_dir():
            raise NotAFileError(f"不能读取目录: {self._relative(target)}")

        content = target.read_text(encoding=encoding)
        size = target.stat().st_size
        return content, size

    # ------------------------------------------------------------------
    # 写入操作
    # ------------------------------------------------------------------

    def write_file(
        self,
        relative_path: str,
        content: str,
        encoding: str = "utf-8",
        overwrite: bool = True,
    ) -> None:
        """写入文件。若父目录不存在则自动创建。"""
        target = self._resolve(relative_path)

        if target.exists() and not overwrite:
            raise PathAlreadyExistsError(f"文件已存在: {self._relative(target)}")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding=encoding)

    def create_directory(self, relative_path: str) -> None:
        """创建目录（递归）。"""
        target = self._resolve(relative_path)
        self._require_not_exists(target)
        target.mkdir(parents=True, exist_ok=False)

    # ------------------------------------------------------------------
    # 删除操作
    # ------------------------------------------------------------------

    def delete(self, relative_path: str) -> None:
        """删除文件或目录（目录会递归删除）。"""
        target = self._resolve(relative_path)
        self._require_exists(target)

        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()

    # ------------------------------------------------------------------
    # 移动/重命名
    # ------------------------------------------------------------------

    def move(self, src_relative: str, dst_relative: str) -> None:
        """移动或重命名文件/目录。"""
        src = self._resolve(src_relative)
        dst = self._resolve(dst_relative)

        self._require_exists(src)
        if dst.exists():
            raise PathAlreadyExistsError(f"目标路径已存在: {self._relative(dst)}")

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
