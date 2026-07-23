"""
CommentService 业务逻辑层。
"""

from dataclasses import dataclass
from typing import List, Optional

from paas_core import Service, service_method

from .CommentMapper import CommentMapper


@dataclass
class CommentItem:
    """服务层 Comment 领域模型。"""

    id: int
    name: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


@Service
class CommentService:
    def __init__(self, comment_mapper: CommentMapper):
        self.comment_mapper = comment_mapper

    @service_method(params=[], calls=["CommentMapper.list"], feature="查询评论列表")
    def list_comments(self) -> List[dict]:
        """查询评论列表。"""
        rows = self.comment_mapper.list()
        return [CommentItem(**row).to_dict() for row in rows]

    @service_method(params=["id"], calls=["CommentMapper.get_by_id"], feature="查询评论详情")
    def get_comment(self, id: int) -> Optional[dict]:
        """查询评论详情。"""
        item = self.comment_mapper.get_by_id(int(id))
        if item is None:
            return None
        return CommentItem(**item).to_dict()

    @service_method(params=["name"], calls=["CommentMapper.create"], feature="创建评论")
    def create_comment(self, name: str) -> dict:
        """创建评论。"""
        new_item = self.comment_mapper.create(name)
        return CommentItem(**new_item).to_dict()
