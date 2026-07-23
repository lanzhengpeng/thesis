"""
GammaController HTTP 接口层。
"""

from pydantic import BaseModel

from paas_core import Controller, GET, POST

from .GammaService import GammaService


class GammaCreateRequest(BaseModel):
    """创建 Gamma 测试实体的 API 请求体。"""

    name: str
    status: str


class GammaResponse(BaseModel):
    """Gamma 测试实体的 API 响应体。"""

    id: int
    name: str
    status: str


@Controller("/api/gammas")
class GammaController:
    def __init__(self, gamma_service: GammaService):
        self.gamma_service = gamma_service

    @GET("/", calls=["GammaService.list_gammas"], feature="查询 Gamma 测试实体列表")
    def list_gammas(self):
        """GET /api/gammas/"""
        return self.gamma_service.list_gammas()

    @GET("/{id}", calls=["GammaService.get_gamma"], feature="根据 ID 查询 Gamma 测试实体详情")
    def get_gamma(self, id: int):
        """GET /api/gammas/{id}"""
        item = self.gamma_service.get_gamma(id)
        if item is None:
            return {"error": "not found"}
        return GammaResponse(**item).model_dump()

    @POST("/", calls=["GammaService.create_gamma"], feature="创建新的 Gamma 测试实体")
    def create_gamma(self, payload: dict):
        """POST /api/gammas/"""
        req = GammaCreateRequest(**payload)
        new_item = self.gamma_service.create_gamma(req.name, req.status)
        return GammaResponse(**new_item).model_dump()
