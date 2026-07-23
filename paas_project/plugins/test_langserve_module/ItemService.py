"""
ItemService 业务逻辑层。
"""

from dataclasses import dataclass
from typing import List, Optional

from paas_core import Service, service_method

from .ItemMapper import ItemMapper


@dataclass
class ItemItem:
    """服务层 Item 领域模型。"""

    id: int
    name: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


@Service
class ItemService:
    def __init__(self, item_mapper: ItemMapper):
        self.item_mapper = item_mapper

    @service_method(params=[], calls=['ItemMapper.list_all'], feature="查询列表")
    def list_items(self) -> List[dict]:
        """查询列表。"""
        rows = self.item_mapper.list_all()
        return [ItemItem(**row).to_dict() for row in rows]

    @service_method(params=['item_id'], calls=['ItemMapper.get'], feature="查询详情")
    def get_item(self, item_id: str) -> Optional[dict]:
        """查询详情。"""
        item = self.item_mapper.get(int(item_id))
        if item is None:
            return None
        return ItemItem(**item).to_dict()

    @service_method(params=['name'], calls=['ItemMapper.create'], feature="创建")
    def create_item(self, name: str) -> dict:
        """创建。"""
        new_item = self.item_mapper.create(name)
        return ItemItem(**new_item).to_dict()
