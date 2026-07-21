"""
AgentDemoMapper 数据访问层。
"""

from paas_core import Mapper, sql_operation

@Mapper
class AgentDemoMapper:
    def __init__(self):
        self._items = {}
        self._next_id = 1

    @sql_operation(sql="SELECT 1", params=[], feature="查询全部 AgentDemo 记录")
    def list(self, ):
        """查询全部 AgentDemo 记录。"""
        pass

    @sql_operation(sql="SELECT 1", params=['id'], feature="根据 ID 查询 AgentDemo 详情")
    def get_by_id(self, id: str):
        """根据 ID 查询 AgentDemo 详情。"""
        pass

    @sql_operation(sql="INSERT INTO items (name) VALUES (%s)", params=['name'], feature="创建 AgentDemo 记录")
    def create(self, name: str) -> dict:
        """创建 AgentDemo 记录。"""
        item_id = self._next_id
        self._next_id += 1
        item = {'id': item_id, 'name': name}
        self._items[item_id] = item
        return item
