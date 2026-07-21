"""
订单模块业务逻辑层。
演示跨模块依赖：OrderService 依赖 UserService。
"""

from paas_core import Service, service_method
from plugins.user_module.UserService import UserService
from .OrderMapper import OrderMapper


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
        return self.order_mapper.create(user_id, total)

    @service_method(
        params=["order_id"],
        calls=["OrderMapper.get"],
        feature="查询订单",
    )
    def get_order(self, order_id: int) -> dict | None:
        """查询单个订单。"""
        return self.order_mapper.get(order_id)

    @service_method(calls=["OrderMapper.list_all"], feature="全量列表")
    def list_orders(self) -> list:
        """查询订单列表。"""
        return self.order_mapper.list_all()
