"""
用户模块数据访问层。
"""

from dataclasses import dataclass
from typing import List, Optional

from paas_core import Mapper, sql_operation

from plugins.database.db import get_db


@dataclass
class User:
    """User 数据模型（对应数据库表 users）。"""

    id: int
    username: str
    email: str

    def to_dict(self) -> dict:
        return {"id": self.id, "username": self.username, "email": self.email}


@Mapper
class UserMapper:
    def __init__(self):
        self._ensure_table()

    def _ensure_table(self) -> None:
        with get_db() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    email TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @sql_operation(sql="SELECT id, username, email FROM users", params=[], feature="全量列表")
    def list_all(self) -> List[dict]:
        """查询所有用户。"""
        with get_db() as conn:
            rows = conn.execute("SELECT id, username, email FROM users").fetchall()
            return [
                User(id=row["id"], username=row["username"], email=row["email"]).to_dict()
                for row in rows
            ]

    @sql_operation(
        sql="SELECT id, username, email FROM users WHERE id = ?",
        params=["user_id"],
        feature="查询用户",
    )
    def get(self, user_id: int) -> Optional[dict]:
        """根据 ID 查询用户。"""
        with get_db() as conn:
            row = conn.execute(
                "SELECT id, username, email FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if row is None:
                return None
            return User(
                id=row["id"], username=row["username"], email=row["email"]
            ).to_dict()

    @sql_operation(
        sql="INSERT INTO users (username, email) VALUES (?, ?)",
        params=["username", "email"],
        feature="创建用户",
    )
    def create(self, username: str, email: str) -> dict:
        """创建用户。"""
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO users (username, email) VALUES (?, ?)",
                (username, email),
            )
            conn.commit()
            new_id = cursor.lastrowid
            return User(id=new_id, username=username, email=email).to_dict()
