"""
AlphaMapper 数据访问层。
"""

from paas_core import Mapper, sql_operation

@Mapper
class AlphaMapper:
    def __init__(self):
        self._items = {}
        self._next_id = 1

    @sql_operation(sql="INSERT INTO items (name) VALUES (%s)", params=['name'], feature="创建 Alpha 记录")
    def create(self, name: str) -> dict:
        """创建 Alpha 记录。"""
        item_id = self._next_id
        self._next_id += 1
        item = {'id': item_id, 'name': name}
        self._items[item_id] = item
        return item

    @sql_operation(sql="SELECT 1", params=['id'], feature="根据 ID 查询 Alpha 详情")
    def get_by_id(self, id: str):
        """根据 ID 查询 Alpha 详情。"""
        pass

    @sql_operation(sql="SELECT * FROM items", feature="查询 Alpha 列表")
    def list_all(self) -> list:
        """查询 Alpha 列表。"""
        return list(self._items.values())
