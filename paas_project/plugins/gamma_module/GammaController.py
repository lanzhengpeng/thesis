from paas_core import Controller, GET, POST
from .GammaService import GammaService


@Controller("/api/gammas")
class GammaController:
    def __init__(self, gamma_service: GammaService):
        self.gamma_service = gamma_service

    @GET("/", calls=["GammaService.list_gammas"], feature="查询 Gamma 测试实体列表")
    def list_gammas(self):
        return self.gamma_service.list_gammas()

    @GET("/{id}", calls=["GammaService.get_gamma"], feature="根据 ID 查询 Gamma 测试实体详情")
    def get_gamma(self, id: int):
        return self.gamma_service.get_gamma(id)

    @POST("/", calls=["GammaService.create_gamma"], feature="创建新的 Gamma 测试实体")
    def create_gamma(self, payload: dict):
        return self.gamma_service.create_gamma(payload["name"], payload["status"])
