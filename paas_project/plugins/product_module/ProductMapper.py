"""
ProductMapper 数据访问层。
"""

from paas_core import Mapper, sql_operation

@Mapper
class ProductMapper:
    def __init__(self):
        self._items = {}
        self._next_id = 1

    @sql_operation(sql="INSERT INTO items (name) VALUES (%s)", params=['name'], feature="创建商品")
    def create(self, name: str) -> dict:
        """创建商品。"""
        item_id = self._next_id
        self._next_id += 1
        item = {'id': item_id, 'name': name}
        self._items[item_id] = item
        return item

    @sql_operation(sql="SELECT * FROM items", feature="查询全部商品")
    def list_all(self) -> list:
        """查询全部商品。"""
        return list(self._items.values())

    @sql_operation(sql="SELECT 1", params=['product_id'], feature="根据ID查询商品")
    def get_by_id(self, product_id: str):
        """根据ID查询商品。"""
        pass
