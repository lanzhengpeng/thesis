from paas_core import Controller, GET, POST
from .CommentMapper import CommentMapper
from .CommentService import CommentService


@Controller("/api/comments")
class CommentController:
    def __init__(self, comment_mapper: CommentMapper, comment_service: CommentService):
        self.comment_mapper = comment_mapper
        self.comment_service = comment_service

    @GET("/", calls=["CommentMapper.list"], feature="查询列表")
    def list_comments(self):
        return self.comment_mapper.list()

    @GET("/{id}", calls=["CommentMapper.get_by_id"], feature="查询详情")
    def get_comment(self, id: int):
        return self.comment_mapper.get_by_id(id)

    @POST("/", calls=["CommentService.create_comment"], feature="创建评论")
    def create_comment(self, payload: dict):
        name = payload.get("name")
        return self.comment_service.create_comment(name)
