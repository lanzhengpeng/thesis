"""
PaasLangserveVerifyService 业务逻辑层。
"""

from paas_core import Service, service_method
from .PaasLangserveVerifyMapper import PaasLangserveVerifyMapper

@Service
class PaasLangserveVerifyService:
    def __init__(self, paas_langserve_verify_mapper: PaasLangserveVerifyMapper):
        self.paas_langserve_verify_mapper = paas_langserve_verify_mapper

    @service_method(params=[], calls=['PaasLangserveVerifyMapper.list'], feature="查询列表")
    def list(self) -> dict | None:
        """查询列表。"""
        return self.paas_langserve_verify_mapper.list()

    @service_method(params=['id'], calls=['PaasLangserveVerifyMapper.get_by_id'], feature="查询详情")
    def get_detail(self, id: str) -> dict | None:
        """查询详情。"""
        return self.paas_langserve_verify_mapper.get(id)

    @service_method(params=['name'], calls=['PaasLangserveVerifyMapper.create'], feature="创建记录")
    def create(self, name: str) -> dict | None:
        """创建记录。"""
        return self.paas_langserve_verify_mapper.create(name)
