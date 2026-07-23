"""
订单模块业务逻辑层。
演示跨模块依赖：OrderService 依赖 UserService。
"""

from dataclasses import dataclass
from typing import List, Optional

from paas_core import Service, service_method
from plugins.user_module.UserService import UserService

from .OrderMapper import OrderMapper


@dataclass
class OrderItem:
    """服务层 Order 领域模型。"""

    id: int
    user_id: int
    total: float

    def to_dict(self) -> dict:
        return {"id": self.id, "user_id": self.user_id, "total": self.total}


@Service
class OrderService:
    def __init__(self, order_mapper: OrderMapper, user_service: UserService):
        self.order_mapper = order_mapper
        self.user_service = user_service

    @service_method(
        params=["user_id", "total"],
        calls=["UserService.get_user", "OrderMapper.create"],
        feature="创建订单",
    )
    def create_order(self, user_id: int, total: float) -> dict:
        """创建订单前校验用户是否存在。"""
        user = self.user_service.get_user(user_id)
        if user is None:
            return {"error": "user not found"}
        new_item = self.order_mapper.create(user_id, total)
        return OrderItem(**new_item).to_dict()

    @service_method(
        params=["order_id"],
        calls=["OrderMapper.get"],
        feature="查询订单",
    )
    def get_order(self, order_id: int) -> Optional[dict]:
        """查询单个订单。"""
        item = self.order_mapper.get(order_id)
        if item is None:
            return None
        return OrderItem(**item).to_dict()

    @service_method(calls=["OrderMapper.list_all"], feature="全量列表")
    def list_orders(self) -> List[dict]:
        """查询订单列表。"""
        rows = self.order_mapper.list_all()
        return [OrderItem(**row).to_dict() for row in rows]
