"""
订单模块数据访问层。
"""

from dataclasses import dataclass
from typing import List, Optional

from paas_core import Mapper, sql_operation

from plugins.database.db import get_db


@dataclass
class Order:
    """Order 数据模型（对应数据库表 orders）。"""

    id: int
    user_id: int
    total: float

    def to_dict(self) -> dict:
        return {"id": self.id, "user_id": self.user_id, "total": self.total}


@Mapper
class OrderMapper:
    def __init__(self):
        self._ensure_table()

    def _ensure_table(self) -> None:
        with get_db() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    total REAL NOT NULL
                )
                """
            )
            conn.commit()

    @sql_operation(sql="SELECT id, user_id, total FROM orders", params=[], feature="全量列表")
    def list_all(self) -> List[dict]:
        """查询所有订单。"""
        with get_db() as conn:
            rows = conn.execute("SELECT id, user_id, total FROM orders").fetchall()
            return [
                Order(id=row["id"], user_id=row["user_id"], total=row["total"]).to_dict()
                for row in rows
            ]

    @sql_operation(
        sql="SELECT id, user_id, total FROM orders WHERE id = ?",
        params=["order_id"],
        feature="查询订单",
    )
    def get(self, order_id: int) -> Optional[dict]:
        """根据 ID 查询订单。"""
        with get_db() as conn:
            row = conn.execute(
                "SELECT id, user_id, total FROM orders WHERE id = ?", (order_id,)
            ).fetchone()
            if row is None:
                return None
            return Order(
                id=row["id"], user_id=row["user_id"], total=row["total"]
            ).to_dict()

    @sql_operation(
        sql="INSERT INTO orders (user_id, total) VALUES (?, ?)",
        params=["user_id", "total"],
        feature="创建订单",
    )
    def create(self, user_id: int, total: float) -> dict:
        """创建订单。"""
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO orders (user_id, total) VALUES (?, ?)",
                (user_id, total),
            )
            conn.commit()
            new_id = cursor.lastrowid
            return Order(id=new_id, user_id=user_id, total=total).to_dict()
