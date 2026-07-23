"""
ItemMapper 数据访问层。
"""

from dataclasses import dataclass
from typing import List, Optional

from paas_core import Mapper, sql_operation

from plugins.database.db import get_db


@dataclass
class Item:
    """Item 数据模型（对应数据库表 items）。"""

    id: int
    name: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


@Mapper
class ItemMapper:
    def __init__(self):
        self._ensure_table()

    def _ensure_table(self) -> None:
        with get_db() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @sql_operation(sql="SELECT id, name FROM items", params=[], feature="全量列表")
    def list_all(self) -> List[dict]:
        """全量列表。"""
        with get_db() as conn:
            rows = conn.execute("SELECT id, name FROM items").fetchall()
            return [Item(id=row["id"], name=row["name"]).to_dict() for row in rows]

    @sql_operation(sql="SELECT id, name FROM items WHERE id = ?", params=['item_id'], feature="根据 ID 查询")
    def get(self, item_id: int) -> Optional[dict]:
        """根据 ID 查询。"""
        with get_db() as conn:
            row = conn.execute(
                "SELECT id, name FROM items WHERE id = ?", (item_id,)
            ).fetchone()
            if row is None:
                return None
            return Item(id=row["id"], name=row["name"]).to_dict()

    @sql_operation(sql="INSERT INTO items (name) VALUES (?)", params=['name'], feature="创建")
    def create(self, name: str) -> dict:
        """创建。"""
        with get_db() as conn:
            cursor = conn.execute("INSERT INTO items (name) VALUES (?)", (name,))
            conn.commit()
            new_id = cursor.lastrowid
            return Item(id=new_id, name=name).to_dict()
