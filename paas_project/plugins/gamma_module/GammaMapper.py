from typing import Any, Dict, List, Optional
from paas_core import Mapper, sql_operation


@Mapper
class GammaMapper:
    def __init__(self):
        self._items: Dict[int, Any] = {}
        self._next_id: int = 1

    @sql_operation(sql="SELECT * FROM gamma", params=[], feature="查询 Gamma 测试实体列表")
    def list(self) -> List[Any]:
        return list(self._items.values())

    @sql_operation(sql="SELECT * FROM gamma WHERE id = ?", params=["id"], feature="根据 ID 查询 Gamma 测试实体详情")
    def get_by_id(self, id: int) -> Optional[Any]:
        return self._items.get(id)

    @sql_operation(sql="INSERT INTO gamma (name, status) VALUES (?, ?)", params=["name", "status"], feature="创建新的 Gamma 测试实体")
    def create(self, name: str, status: str) -> Any:
        gamma = {"id": self._next_id, "name": name, "status": status}
        self._items[self._next_id] = gamma
        self._next_id += 1
        return gamma
