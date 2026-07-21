from typing import Dict, List, Optional
from paas_core import Mapper, sql_operation


@Mapper
class CommentMapper:
    def __init__(self):
        self._items: Dict[int, dict] = {}
        self._next_id: int = 1

    @sql_operation(sql="SELECT * FROM comments", params=[], feature="查询评论列表")
    def list(self) -> List[dict]:
        return list(self._items.values())

    @sql_operation(sql="SELECT * FROM comments WHERE id = ?", params=["id"], feature="根据ID查询评论详情")
    def get_by_id(self, id: int) -> Optional[dict]:
        return self._items.get(int(id))

    @sql_operation(sql="INSERT INTO comments (name) VALUES (?)", params=["name"], feature="创建评论")
    def create(self, name: str) -> dict:
        comment = {"id": self._next_id, "name": name}
        self._items[self._next_id] = comment
        self._next_id += 1
        return comment
