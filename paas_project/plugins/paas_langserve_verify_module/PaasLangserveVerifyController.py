"""
PaasLangserveVerifyController HTTP 接口层。
"""

from pydantic import BaseModel

from paas_core import Controller, GET, POST

from .PaasLangserveVerifyService import PaasLangserveVerifyService


class PaasLangserveVerifyCreateRequest(BaseModel):
    """创建记录的 API 请求体。"""

    name: str


class PaasLangserveVerifyResponse(BaseModel):
    """记录的 API 响应体。"""

    id: int
    name: str


@Controller("/api/paas_langserve_verifies")
class PaasLangserveVerifyController:
    def __init__(self, paas_langserve_verify_service: PaasLangserveVerifyService):
        self.paas_langserve_verify_service = paas_langserve_verify_service

    @GET("/", calls=['PaasLangserveVerifyService.list'], feature="查询列表")
    def list(self):
        """GET /api/paas_langserve_verifies/"""
        return self.paas_langserve_verify_service.list()

    @GET("/{id}", calls=['PaasLangserveVerifyService.get_detail'], feature="查询详情")
    def get_detail(self, id: str):
        """GET /api/paas_langserve_verifies/{id}"""
        item = self.paas_langserve_verify_service.get_detail(id)
        if item is None:
            return {"error": "not found"}
        return PaasLangserveVerifyResponse(**item).model_dump()

    @POST("/", calls=['PaasLangserveVerifyService.create'], feature="创建记录")
    def create(self, payload: dict):
        """POST /api/paas_langserve_verifies/"""
        req = PaasLangserveVerifyCreateRequest(**payload)
        new_item = self.paas_langserve_verify_service.create(req.name)
        return PaasLangserveVerifyResponse(**new_item).model_dump()
