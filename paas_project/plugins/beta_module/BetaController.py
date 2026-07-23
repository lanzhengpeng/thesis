"""
BetaController HTTP 接口层。
"""

from pydantic import BaseModel

from paas_core import Controller, GET, POST

from .BetaService import BetaService


class BetaCreateRequest(BaseModel):
    """创建 Beta 的 API 请求体。"""

    name: str


class BetaResponse(BaseModel):
    """Beta 的 API 响应体。"""

    id: int
    name: str


@Controller("/api/betas")
class BetaController:
    def __init__(self, beta_service: BetaService):
        self.beta_service = beta_service

    @GET("/", calls=['BetaService.list_betas'], feature="查询列表")
    def list_betas(self):
        """GET /api/betas/"""
        return self.beta_service.list_betas()

    @GET("/{id}", calls=['BetaService.get_beta'], feature="查询详情")
    def get_beta(self, id: str):
        """GET /api/betas/{id}"""
        item = self.beta_service.get_beta(id)
        if item is None:
            return {"error": "not found"}
        return BetaResponse(**item).model_dump()

    @POST("/", calls=['BetaService.create_beta'], feature="创建 Beta")
    def create_beta(self, payload: dict):
        """POST /api/betas/"""
        req = BetaCreateRequest(**payload)
        new_item = self.beta_service.create_beta(req.name)
        return BetaResponse(**new_item).model_dump()
