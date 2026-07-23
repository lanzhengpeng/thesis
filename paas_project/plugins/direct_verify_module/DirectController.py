"""
DirectController HTTP 接口层。
"""

from paas_core import Controller, GET, POST
from .DirectService import DirectService

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
        return self.direct_service.create_direct(**payload)
