from paas_core import Service, service_method
from .CommentMapper import CommentMapper


@Service
class CommentService:
    def __init__(self, comment_mapper: CommentMapper):
        self.comment_mapper = comment_mapper

    @service_method(params=[], calls=["CommentMapper.list"], feature="查询评论列表")
    def list_comments(self):
        return self.comment_mapper.list()

    @service_method(params=["id"], calls=["CommentMapper.get_by_id"], feature="查询评论详情")
    def get_comment(self, id: int):
        return self.comment_mapper.get_by_id(id)

    @service_method(params=["name"], calls=["CommentMapper.create"], feature="创建评论")
    def create_comment(self, name: str):
        return self.comment_mapper.create(name)
