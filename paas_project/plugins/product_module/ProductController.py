"""
ProductController HTTP 接口层。
"""

from pydantic import BaseModel

from paas_core import Controller, GET, POST

from .ProductService import ProductService


class ProductCreateRequest(BaseModel):
    """创建商品的 API 请求体。"""

    name: str


class ProductResponse(BaseModel):
    """商品的 API 响应体。"""

    id: int
    name: str


@Controller("/api/products")
class ProductController:
    def __init__(self, product_service: ProductService):
        self.product_service = product_service

    @GET("/", calls=['ProductService.list_products'], feature="商品列表")
    def list_products(self):
        """GET /api/products/"""
        return self.product_service.list_products()

    @POST("/", calls=['ProductService.create_product'], feature="创建商品")
    def create_product(self, payload: dict):
        """POST /api/products/"""
        req = ProductCreateRequest(**payload)
        new_item = self.product_service.create_product(req.name)
        return ProductResponse(**new_item).model_dump()

    @GET("/{product_id}", calls=['ProductService.get_product'], feature="商品详情")
    def get_product(self, product_id: str):
        """GET /api/products/{product_id}"""
        item = self.product_service.get_product(product_id)
        if item is None:
            return {"error": "not found"}
        return ProductResponse(**item).model_dump()
