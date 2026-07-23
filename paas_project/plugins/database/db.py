"""
共享 SQLite 数据库连接
======================

为 plugins/ 下的业务模块提供统一的本地 SQLite 访问入口。
数据库文件位于 plugins/database/paas.sqlite，启动时自动创建。
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


PLUGINS_DIR = Path(__file__).resolve().parent
DB_PATH = PLUGINS_DIR / "paas.sqlite"


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """
    获取一个 SQLite 连接上下文。

    自动开启外键约束，并返回支持列名作为属性访问的行对象。
    使用 with 语句可确保连接正确关闭。
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """
    初始化数据库文件。

    如果数据库文件不存在则创建空文件；业务表由各 Mapper 在首次使用时自行创建，
    避免微内核启动阶段对表结构产生强耦合。
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists():
        DB_PATH.touch()
