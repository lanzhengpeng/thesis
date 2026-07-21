"""
订单模块数据访问层。
"""

from paas_core import Mapper, sql_operation


@Mapper
class OrderMapper:
    def __init__(self):
        # 内存中的订单存储（仅用于骨架演示）
        self._orders = {}
        self._next_id = 1

    @sql_operation(
        sql="INSERT INTO orders (user_id, total) VALUES (%s, %s)",
        params=["user_id", "total"],
        feature="创建订单",
    )
    def create(self, user_id: int, total: float) -> dict:
        """创建订单。"""
        order_id = self._next_id
        self._next_id += 1
        order = {"id": order_id, "user_id": user_id, "total": total}
        self._orders[order_id] = order
        return order

    @sql_operation(
        sql="SELECT * FROM orders WHERE id = %s",
        params=["order_id"],
        feature="查询订单",
    )
    def get(self, order_id: int) -> dict | None:
        """根据 ID 查询订单。"""
        return self._orders.get(order_id)

    @sql_operation(sql="SELECT * FROM orders", feature="全量列表")
    def list_all(self) -> list:
        """查询所有订单。"""
        return list(self._orders.values())
