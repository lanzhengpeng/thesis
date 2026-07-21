"""
订单模块 HTTP 接口层。
"""

from paas_core import Controller, GET, POST
from .OrderService import OrderService


@Controller("/api/orders")
class OrderController:
    def __init__(self, order_service: OrderService):
        self.order_service = order_service

    @GET("/", calls=["OrderService.list_orders"], feature="查询列表")
    def list_orders(self):
        """GET /api/orders/"""
        return self.order_service.list_orders()

    @GET("/{order_id}", calls=["OrderService.get_order"], feature="查询订单")
    def get_order(self, order_id: str):
        """GET /api/orders/{order_id}"""
        order = self.order_service.get_order(int(order_id))
        if order is None:
            return {"error": "not found"}
        return order

    @POST("/", calls=["OrderService.create_order"], feature="创建订单")
    def create_order(self, payload: dict):
        """POST /api/orders/"""
        return self.order_service.create_order(
            int(payload.get("user_id", 0)),
            float(payload.get("total", 0.0)),
        )
