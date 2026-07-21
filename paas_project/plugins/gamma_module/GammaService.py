from paas_core import Service, service_method
from .GammaMapper import GammaMapper


@Service
class GammaService:
    def __init__(self, gamma_mapper: GammaMapper):
        self.gamma_mapper = gamma_mapper

    @service_method(params=[], calls=["GammaMapper.list"], feature="查询 Gamma 测试实体列表")
    def list_gammas(self):
        return self.gamma_mapper.list()

    @service_method(params=["id"], calls=["GammaMapper.get_by_id"], feature="根据 ID 查询 Gamma 测试实体详情")
    def get_gamma(self, id: int):
        return self.gamma_mapper.get_by_id(id)

    @service_method(params=["name", "status"], calls=["GammaMapper.create"], feature="创建新的 Gamma 测试实体")
    def create_gamma(self, name: str, status: str):
        return self.gamma_mapper.create(name, status)
