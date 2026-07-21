"""
AlphaService 业务逻辑层。
"""

from paas_core import Service, service_method
from .AlphaMapper import AlphaMapper

@Service
class AlphaService:
    def __init__(self, alpha_mapper: AlphaMapper):
        self.alpha_mapper = alpha_mapper

    @service_method(params=['name'], calls=['AlphaMapper.create'], feature="创建 Alpha")
    def create_alpha(self, name: str) -> dict | None:
        """创建 Alpha。"""
        return self.alpha_mapper.create(name)

    @service_method(params=['id'], calls=['AlphaMapper.get_by_id'], feature="查询 Alpha 详情")
    def get_alpha(self, id: str) -> dict | None:
        """查询 Alpha 详情。"""
        return self.alpha_mapper.get(id)

    @service_method(params=[], calls=['AlphaMapper.list_all'], feature="查询 Alpha 列表")
    def list_alphas(self) -> dict | None:
        """查询 Alpha 列表。"""
        return self.alpha_mapper.list_all()
