"""
ItemService 业务逻辑层。
"""

from paas_core import Service, service_method
from .ItemMapper import ItemMapper

@Service
class ItemService:
    def __init__(self, item_mapper: ItemMapper):
        self.item_mapper = item_mapper

    @service_method(params=[], calls=['ItemMapper.list_all'], feature="查询列表")
    def list_items(self) -> dict | None:
        """查询列表。"""
        return self.item_mapper.list_all()

    @service_method(params=['item_id'], calls=['ItemMapper.get'], feature="查询详情")
    def get_item(self, item_id: str) -> dict | None:
        """查询详情。"""
        return self.item_mapper.get(item_id)

    @service_method(params=['name'], calls=['ItemMapper.create'], feature="创建")
    def create_item(self, name: str) -> dict | None:
        """创建。"""
        return self.item_mapper.create(name)
