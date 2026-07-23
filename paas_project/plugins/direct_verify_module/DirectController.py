"""
DirectController HTTP 接口层。
"""

from pydantic import BaseModel

from paas_core import Controller, GET, POST

from .DirectService import DirectService


class DirectCreateRequest(BaseModel):
    """创建 direct 的 API 请求体。"""

    name: str


class DirectResponse(BaseModel):
    """direct 的 API 响应体。"""

    id: int
    name: str


@Controller("/api/directs")
class DirectController:
    def __init__(self, direct_service: DirectService):
        self.direct_service = direct_service

    @GET("/", calls=['DirectService.list_directs'], feature="查询 direct 列表")
    def list_directs(self):
        """GET /api/directs/"""
        return self.direct_service.list_directs()

    @POST("/", calls=['DirectService.create_direct'], feature="创建 direct")
    def create_direct(self, payload: dict):
        """POST /api/directs/"""
        req = DirectCreateRequest(**payload)
        new_item = self.direct_service.create_direct(req.name)
        return DirectResponse(**new_item).model_dump()
