"""
DirectMapper 数据访问层。
"""

from dataclasses import dataclass
from typing import List

from paas_core import Mapper, sql_operation

from plugins.database.db import get_db


@dataclass
class Direct:
    """Direct 数据模型（对应数据库表 directs）。"""

    id: int
    name: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


@Mapper
class DirectMapper:
    def __init__(self):
        self._ensure_table()

    def _ensure_table(self) -> None:
        with get_db() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS directs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @sql_operation(sql="SELECT id, name FROM directs", params=[], feature="查询 direct 列表")
    def list(self) -> List[dict]:
        """查询 direct 列表。"""
        with get_db() as conn:
            rows = conn.execute("SELECT id, name FROM directs").fetchall()
            return [Direct(id=row["id"], name=row["name"]).to_dict() for row in rows]

    @sql_operation(sql="INSERT INTO directs (name) VALUES (?)", params=['name'], feature="创建 direct 记录")
    def create(self, name: str) -> dict:
        """创建 direct 记录。"""
        with get_db() as conn:
            cursor = conn.execute("INSERT INTO directs (name) VALUES (?)", (name,))
            conn.commit()
            new_id = cursor.lastrowid
            return Direct(id=new_id, name=name).to_dict()
