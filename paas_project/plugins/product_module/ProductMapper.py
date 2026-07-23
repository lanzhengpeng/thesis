"""
ProductMapper 数据访问层。
"""

from dataclasses import dataclass
from typing import List, Optional

from paas_core import Mapper, sql_operation

from plugins.database.db import get_db


@dataclass
class Product:
    """Product 数据模型（对应数据库表 products）。"""

    id: int
    name: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


@Mapper
class ProductMapper:
    def __init__(self):
        self._ensure_table()

    def _ensure_table(self) -> None:
        with get_db() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @sql_operation(sql="SELECT id, name FROM products", params=[], feature="查询全部商品")
    def list_all(self) -> List[dict]:
        """查询全部商品。"""
        with get_db() as conn:
            rows = conn.execute("SELECT id, name FROM products").fetchall()
            return [Product(id=row["id"], name=row["name"]).to_dict() for row in rows]

    @sql_operation(sql="SELECT id, name FROM products WHERE id = ?", params=['product_id'], feature="根据ID查询商品")
    def get_by_id(self, product_id: int) -> Optional[dict]:
        """根据ID查询商品。"""
        with get_db() as conn:
            row = conn.execute(
                "SELECT id, name FROM products WHERE id = ?", (product_id,)
            ).fetchone()
            if row is None:
                return None
            return Product(id=row["id"], name=row["name"]).to_dict()

    @sql_operation(sql="INSERT INTO products (name) VALUES (?)", params=['name'], feature="创建商品")
    def create(self, name: str) -> dict:
        """创建商品。"""
        with get_db() as conn:
            cursor = conn.execute("INSERT INTO products (name) VALUES (?)", (name,))
            conn.commit()
            new_id = cursor.lastrowid
            return Product(id=new_id, name=name).to_dict()
