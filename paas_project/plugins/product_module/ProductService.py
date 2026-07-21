"""
ProductService 业务逻辑层。
"""

from paas_core import Service, service_method
from .ProductMapper import ProductMapper

@Service
class ProductService:
    def __init__(self, product_mapper: ProductMapper):
        self.product_mapper = product_mapper

    @service_method(params=['name'], calls=['ProductMapper.create'], feature="创建商品")
    def create_product(self, name: str) -> dict | None:
        """创建商品。"""
        return self.product_mapper.create(name)

    @service_method(params=[], calls=['ProductMapper.list_all'], feature="查询商品列表")
    def list_products(self) -> dict | None:
        """查询商品列表。"""
        return self.product_mapper.list_all()

    @service_method(params=['product_id'], calls=['ProductMapper.get_by_id'], feature="查询商品详情")
    def get_product(self, product_id: str) -> dict | None:
        """查询商品详情。"""
        return self.product_mapper.get(product_id)
