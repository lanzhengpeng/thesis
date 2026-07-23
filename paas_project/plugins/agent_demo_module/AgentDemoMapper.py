"""
AgentDemoMapper 数据访问层。
"""

from dataclasses import dataclass
from typing import List, Optional

from paas_core import Mapper, sql_operation

from plugins.database.db import get_db


@dataclass
class AgentDemo:
    """AgentDemo 数据模型（对应数据库表 agent_demos）。"""

    id: int
    name: str

    def to_dict(self) -> dict:
        """序列化为普通字典，便于 Service / Controller 返回。"""
        return {"id": self.id, "name": self.name}


@Mapper
class AgentDemoMapper:
    def __init__(self):
        self._ensure_table()

    def _ensure_table(self) -> None:
        """确保 agent_demos 表存在。"""
        with get_db() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_demos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @sql_operation(sql="SELECT id, name FROM agent_demos", params=[], feature="查询全部 AgentDemo 数据")
    def list(self) -> List[dict]:
        """查询全部 AgentDemo 数据。"""
        with get_db() as conn:
            rows = conn.execute("SELECT id, name FROM agent_demos").fetchall()
            return [AgentDemo(id=row["id"], name=row["name"]).to_dict() for row in rows]

    @sql_operation(sql="SELECT id, name FROM agent_demos WHERE id = ?", params=['id'], feature="根据 ID 查询 AgentDemo")
    def get_by_id(self, id: int) -> Optional[dict]:
        """根据 ID 查询 AgentDemo。"""
        with get_db() as conn:
            row = conn.execute(
                "SELECT id, name FROM agent_demos WHERE id = ?", (id,)
            ).fetchone()
            if row is None:
                return None
            return AgentDemo(id=row["id"], name=row["name"]).to_dict()

    @sql_operation(sql="INSERT INTO agent_demos (name) VALUES (?)", params=['name'], feature="创建 AgentDemo")
    def create(self, name: str) -> dict:
        """创建 AgentDemo。"""
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO agent_demos (name) VALUES (?)", (name,)
            )
            conn.commit()
            new_id = cursor.lastrowid
            return AgentDemo(id=new_id, name=name).to_dict()
