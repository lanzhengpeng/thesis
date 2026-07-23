"""
订单模块 HTTP 接口层。
"""

from pydantic import BaseModel

from paas_core import Controller, GET, POST

from .OrderService import OrderService


class OrderCreateRequest(BaseModel):
    """创建订单的 API 请求体。"""

    user_id: int
    total: float


class OrderResponse(BaseModel):
    """订单的 API 响应体。"""

    id: int
    user_id: int
    total: float


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
        return OrderResponse(**order).model_dump()

    @POST("/", calls=["OrderService.create_order"], feature="创建订单")
    def create_order(self, payload: dict):
        """POST /api/orders/"""
        req = OrderCreateRequest(**payload)
        return self.order_service.create_order(req.user_id, req.total)
