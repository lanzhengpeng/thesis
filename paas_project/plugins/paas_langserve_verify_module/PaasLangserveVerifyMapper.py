"""
PaasLangserveVerifyMapper 数据访问层。
"""

from dataclasses import dataclass
from typing import List, Optional

from paas_core import Mapper, sql_operation

from plugins.database.db import get_db


@dataclass
class PaasLangserveVerify:
    """PaasLangserveVerify 数据模型（对应数据库表 paas_langserve_verifies）。"""

    id: int
    name: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


@Mapper
class PaasLangserveVerifyMapper:
    def __init__(self):
        self._ensure_table()

    def _ensure_table(self) -> None:
        with get_db() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS paas_langserve_verifies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @sql_operation(sql="SELECT id, name FROM paas_langserve_verifies", params=[], feature="查询全部记录")
    def list(self) -> List[dict]:
        """查询全部记录。"""
        with get_db() as conn:
            rows = conn.execute("SELECT id, name FROM paas_langserve_verifies").fetchall()
            return [
                PaasLangserveVerify(id=row["id"], name=row["name"]).to_dict()
                for row in rows
            ]

    @sql_operation(sql="SELECT id, name FROM paas_langserve_verifies WHERE id = ?", params=['id'], feature="根据ID查询记录")
    def get_by_id(self, id: int) -> Optional[dict]:
        """根据ID查询记录。"""
        with get_db() as conn:
            row = conn.execute(
                "SELECT id, name FROM paas_langserve_verifies WHERE id = ?", (id,)
            ).fetchone()
            if row is None:
                return None
            return PaasLangserveVerify(id=row["id"], name=row["name"]).to_dict()

    @sql_operation(sql="INSERT INTO paas_langserve_verifies (name) VALUES (?)", params=['name'], feature="创建记录")
    def create(self, name: str) -> dict:
        """创建记录。"""
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO paas_langserve_verifies (name) VALUES (?)", (name,)
            )
            conn.commit()
            new_id = cursor.lastrowid
            return PaasLangserveVerify(id=new_id, name=name).to_dict()
