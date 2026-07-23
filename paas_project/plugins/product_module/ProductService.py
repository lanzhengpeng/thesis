"""
ProductService 业务逻辑层。
"""

from dataclasses import dataclass
from typing import List, Optional

from paas_core import Service, service_method

from .ProductMapper import ProductMapper


@dataclass
class ProductItem:
    """服务层 Product 领域模型。"""

    id: int
    name: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


@Service
class ProductService:
    def __init__(self, product_mapper: ProductMapper):
        self.product_mapper = product_mapper

    @service_method(params=['name'], calls=['ProductMapper.create'], feature="创建商品")
    def create_product(self, name: str) -> dict:
        """创建商品。"""
        new_item = self.product_mapper.create(name)
        return ProductItem(**new_item).to_dict()

    @service_method(params=[], calls=['ProductMapper.list_all'], feature="查询商品列表")
    def list_products(self) -> List[dict]:
        """查询商品列表。"""
        rows = self.product_mapper.list_all()
        return [ProductItem(**row).to_dict() for row in rows]

    @service_method(params=['product_id'], calls=['ProductMapper.get_by_id'], feature="查询商品详情")
    def get_product(self, product_id: str) -> Optional[dict]:
        """查询商品详情。"""
        item = self.product_mapper.get_by_id(int(product_id))
        if item is None:
            return None
        return ProductItem(**item).to_dict()
