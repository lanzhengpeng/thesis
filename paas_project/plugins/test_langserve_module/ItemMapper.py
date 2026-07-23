"""
ItemMapper 数据访问层。
"""

from paas_core import Mapper, sql_operation

@Mapper
class ItemMapper:
    def __init__(self):
        self._items = {}
        self._next_id = 1

    @sql_operation(sql="SELECT * FROM items", feature="全量列表")
    def list_all(self) -> list:
        """全量列表。"""
        return list(self._items.values())

    @sql_operation(sql="SELECT * FROM items WHERE id = %s", params=['item_id'], feature="根据 ID 查询")
    def get(self, item_id: str) -> dict | None:
        """根据 ID 查询。"""
        return self._items.get(item_id)

    @sql_operation(sql="INSERT INTO items (name) VALUES (%s)", params=['name'], feature="创建")
    def create(self, name: str) -> dict:
        """创建。"""
        item_id = self._next_id
        self._next_id += 1
        item = {'id': item_id, 'name': name}
        self._items[item_id] = item
        return item
