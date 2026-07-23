"""
CommentController HTTP 接口层。
"""

from pydantic import BaseModel

from paas_core import Controller, GET, POST

from .CommentService import CommentService


class CommentCreateRequest(BaseModel):
    """创建评论的 API 请求体。"""

    name: str


class CommentResponse(BaseModel):
    """评论的 API 响应体。"""

    id: int
    name: str


@Controller("/api/comments")
class CommentController:
    def __init__(self, comment_service: CommentService):
        self.comment_service = comment_service

    @GET("/", calls=["CommentService.list_comments"], feature="查询列表")
    def list_comments(self):
        """GET /api/comments/"""
        return self.comment_service.list_comments()

    @GET("/{id}", calls=["CommentService.get_comment"], feature="查询详情")
    def get_comment(self, id: int):
        """GET /api/comments/{id}"""
        item = self.comment_service.get_comment(id)
        if item is None:
            return {"error": "not found"}
        return CommentResponse(**item).model_dump()

    @POST("/", calls=["CommentService.create_comment"], feature="创建评论")
    def create_comment(self, payload: dict):
        """POST /api/comments/"""
        req = CommentCreateRequest(**payload)
        new_item = self.comment_service.create_comment(req.name)
        return CommentResponse(**new_item).model_dump()
