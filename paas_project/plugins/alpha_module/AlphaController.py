"""
AlphaController HTTP 接口层。
"""

from pydantic import BaseModel

from paas_core import Controller, GET, POST

from .AlphaService import AlphaService


class AlphaCreateRequest(BaseModel):
    """创建 Alpha 的 API 请求体。"""

    name: str


class AlphaResponse(BaseModel):
    """Alpha 的 API 响应体。"""

    id: int
    name: str


@Controller("/api/alphas")
class AlphaController:
    def __init__(self, alpha_service: AlphaService):
        self.alpha_service = alpha_service

    @GET("/", calls=['AlphaService.list_alphas'], feature="查询列表")
    def list_alphas(self):
        """GET /api/alphas/"""
        return self.alpha_service.list_alphas()

    @GET("/{id}", calls=['AlphaService.get_alpha'], feature="查询详情")
    def get_alpha(self, id: str):
        """GET /api/alphas/{id}"""
        item = self.alpha_service.get_alpha(id)
        if item is None:
            return {"error": "not found"}
        return AlphaResponse(**item).model_dump()

    @POST("/", calls=['AlphaService.create_alpha'], feature="创建")
    def create_alpha(self, payload: dict):
        """POST /api/alphas/"""
        req = AlphaCreateRequest(**payload)
        new_item = self.alpha_service.create_alpha(req.name)
        return AlphaResponse(**new_item).model_dump()
