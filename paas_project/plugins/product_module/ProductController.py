"""
ProductController HTTP 接口层。
"""

from paas_core import Controller, GET, POST
from .ProductService import ProductService

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
        return self.product_service.create_product(**payload)

    @GET("/{product_id}", calls=['ProductService.get_product'], feature="商品详情")
    def get_product(self):
        """GET /api/products/{product_id}"""
        return self.product_service.get_product()
