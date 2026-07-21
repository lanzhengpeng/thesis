"""
并发锁工具
==========

为智能体写文件与内核重载提供跨进程互斥能力。
"""

from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


DB_DIR = Path(__file__).resolve().parent.parent.parent / "database"
_CROSS_PROCESS_LOCK_FILE = DB_DIR / ".plugin_write.lock"


def _ensure_lock_dir() -> None:
    """确保锁文件目录存在。"""
    DB_DIR.mkdir(parents=True, exist_ok=True)


class _NoOpLock:
    """空锁，用于无法使用文件锁的平台。"""

    def acquire(self) -> None:
        pass

    def release(self) -> None:
        pass


class _FcntlLock:
    """基于 fcntl 的跨进程互斥锁（POSIX 系统）。"""

    def __init__(self, lock_file: Path):
        self._lock_file = lock_file
        self._fd: int = -1

    def acquire(self) -> None:
        import fcntl

        _ensure_lock_dir()
        self._fd = os.open(str(self._lock_file), os.O_CREAT | os.O_RDWR)
        fcntl.flock(self._fd, fcntl.LOCK_EX)

    def release(self) -> None:
        import fcntl

        if self._fd >= 0:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            self._fd = -1


def _make_cross_process_lock() -> _FcntlLock | _NoOpLock:
    """根据平台选择合适的跨进程锁。"""
    try:
        import fcntl  # noqa: F401
        return _FcntlLock(_CROSS_PROCESS_LOCK_FILE)
    except ImportError:
        return _NoOpLock()


_CROSS_PROCESS_LOCK = _make_cross_process_lock()
_THREAD_LOCK = threading.Lock()


@contextmanager
def plugin_write_lock() -> Generator[None, None, None]:
    """
    跨进程写锁上下文管理器。

    在持有该锁期间，其他进程无法同时写插件或重载内核。
    """
    _CROSS_PROCESS_LOCK.acquire()
    try:
        yield
    finally:
        _CROSS_PROCESS_LOCK.release()
