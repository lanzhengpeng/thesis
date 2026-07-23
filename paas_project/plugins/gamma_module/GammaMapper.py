"""
GammaMapper 数据访问层。
"""

from dataclasses import dataclass
from typing import List, Optional

from paas_core import Mapper, sql_operation

from plugins.database.db import get_db


@dataclass
class Gamma:
    """Gamma 数据模型（对应数据库表 gammas）。"""

    id: int
    name: str
    status: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "status": self.status}


@Mapper
class GammaMapper:
    def __init__(self):
        self._ensure_table()

    def _ensure_table(self) -> None:
        with get_db() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS gammas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @sql_operation(sql="SELECT id, name, status FROM gammas", params=[], feature="查询 Gamma 测试实体列表")
    def list(self) -> List[dict]:
        """查询 Gamma 测试实体列表。"""
        with get_db() as conn:
            rows = conn.execute("SELECT id, name, status FROM gammas").fetchall()
            return [
                Gamma(id=row["id"], name=row["name"], status=row["status"]).to_dict()
                for row in rows
            ]

    @sql_operation(sql="SELECT id, name, status FROM gammas WHERE id = ?", params=["id"], feature="根据 ID 查询 Gamma 测试实体详情")
    def get_by_id(self, id: int) -> Optional[dict]:
        """根据 ID 查询 Gamma 测试实体详情。"""
        with get_db() as conn:
            row = conn.execute(
                "SELECT id, name, status FROM gammas WHERE id = ?", (id,)
            ).fetchone()
            if row is None:
                return None
            return Gamma(
                id=row["id"], name=row["name"], status=row["status"]
            ).to_dict()

    @sql_operation(sql="INSERT INTO gammas (name, status) VALUES (?, ?)", params=["name", "status"], feature="创建新的 Gamma 测试实体")
    def create(self, name: str, status: str) -> dict:
        """创建新的 Gamma 测试实体。"""
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO gammas (name, status) VALUES (?, ?)", (name, status)
            )
            conn.commit()
            new_id = cursor.lastrowid
            return Gamma(id=new_id, name=name, status=status).to_dict()
