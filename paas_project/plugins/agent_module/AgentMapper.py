"""
AgentMapper 数据访问层。
"""

from dataclasses import dataclass
from typing import List, Optional

from paas_core import Mapper, sql_operation

from plugins.database.db import get_db


@dataclass
class Agent:
    """Agent 数据模型（对应数据库表 agents）。"""

    id: int
    name: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


@Mapper
class AgentMapper:
    def __init__(self):
        self._ensure_table()

    def _ensure_table(self) -> None:
        with get_db() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @sql_operation(sql="SELECT id, name FROM agents", params=[], feature="查询 Agent 列表")
    def list(self) -> List[dict]:
        """查询 Agent 列表。"""
        with get_db() as conn:
            rows = conn.execute("SELECT id, name FROM agents").fetchall()
            return [Agent(id=row["id"], name=row["name"]).to_dict() for row in rows]

    @sql_operation(sql="SELECT id, name FROM agents WHERE id = ?", params=['id'], feature="根据 ID 查询 Agent")
    def get_by_id(self, id: int) -> Optional[dict]:
        """根据 ID 查询 Agent。"""
        with get_db() as conn:
            row = conn.execute(
                "SELECT id, name FROM agents WHERE id = ?", (id,)
            ).fetchone()
            if row is None:
                return None
            return Agent(id=row["id"], name=row["name"]).to_dict()

    @sql_operation(sql="INSERT INTO agents (name) VALUES (?)", params=['name'], feature="创建 Agent 记录")
    def create(self, name: str) -> dict:
        """创建 Agent 记录。"""
        with get_db() as conn:
            cursor = conn.execute("INSERT INTO agents (name) VALUES (?)", (name,))
            conn.commit()
            new_id = cursor.lastrowid
            return Agent(id=new_id, name=name).to_dict()
