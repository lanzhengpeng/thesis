"""
订单模块业务逻辑层。
演示跨模块依赖：OrderService 依赖 UserService。
"""

from paas_core import Service
from plugins.user_module.UserService import UserService
from .OrderMapper import OrderMapper


@Service
class OrderService:
    def __init__(self, order_mapper: OrderMapper, user_service: UserService):
        self.order_mapper = order_mapper
        self.user_service = user_service

    def create_order(self, user_id: int, total: float) -> dict:
        """创建订单前校验用户是否存在。"""
        user = self.user_service.get_user(user_id)
        if user is None:
            return {"error": "user not found"}
        return self.order_mapper.create(user_id, total)

    def get_order(self, order_id: int) -> dict | None:
        """查询单个订单。"""
        return self.order_mapper.get(order_id)

    def list_orders(self) -> list:
        """查询订单列表。"""
        return self.order_mapper.list_all()
