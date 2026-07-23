"""
AlphaMapper 数据访问层。
"""

from dataclasses import dataclass
from typing import List, Optional

from paas_core import Mapper, sql_operation

from plugins.database.db import get_db


@dataclass
class Alpha:
    """Alpha 数据模型（对应数据库表 alphas）。"""

    id: int
    name: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


@Mapper
class AlphaMapper:
    def __init__(self):
        self._ensure_table()

    def _ensure_table(self) -> None:
        with get_db() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alphas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @sql_operation(sql="SELECT id, name FROM alphas", params=[], feature="查询 Alpha 列表")
    def list_all(self) -> List[dict]:
        """查询 Alpha 列表。"""
        with get_db() as conn:
            rows = conn.execute("SELECT id, name FROM alphas").fetchall()
            return [Alpha(id=row["id"], name=row["name"]).to_dict() for row in rows]

    @sql_operation(sql="SELECT id, name FROM alphas WHERE id = ?", params=['id'], feature="根据 ID 查询 Alpha 详情")
    def get_by_id(self, id: int) -> Optional[dict]:
        """根据 ID 查询 Alpha 详情。"""
        with get_db() as conn:
            row = conn.execute(
                "SELECT id, name FROM alphas WHERE id = ?", (id,)
            ).fetchone()
            if row is None:
                return None
            return Alpha(id=row["id"], name=row["name"]).to_dict()

    @sql_operation(sql="INSERT INTO alphas (name) VALUES (?)", params=['name'], feature="创建 Alpha 记录")
    def create(self, name: str) -> dict:
        """创建 Alpha 记录。"""
        with get_db() as conn:
            cursor = conn.execute("INSERT INTO alphas (name) VALUES (?)", (name,))
            conn.commit()
            new_id = cursor.lastrowid
            return Alpha(id=new_id, name=name).to_dict()
