"""
BetaService 业务逻辑层。
"""

from paas_core import Service, service_method
from .BetaMapper import BetaMapper

@Service
class BetaService:
    def __init__(self, beta_mapper: BetaMapper):
        self.beta_mapper = beta_mapper

    @service_method(params=[], calls=['BetaMapper.list'], feature="查询 Beta 列表")
    def list_betas(self) -> dict | None:
        """查询 Beta 列表。"""
        return self.beta_mapper.list()

    @service_method(params=['id'], calls=['BetaMapper.get_by_id'], feature="查询 Beta 详情")
    def get_beta(self, id: str) -> dict | None:
        """查询 Beta 详情。"""
        return self.beta_mapper.get(id)

    @service_method(params=['name'], calls=['BetaMapper.create'], feature="创建 Beta")
    def create_beta(self, name: str) -> dict | None:
        """创建 Beta。"""
        return self.beta_mapper.create(name)
