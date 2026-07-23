"""
DirectService 业务逻辑层。
"""

from paas_core import Service, service_method
from .DirectMapper import DirectMapper

@Service
class DirectService:
    def __init__(self, direct_mapper: DirectMapper):
        self.direct_mapper = direct_mapper

    @service_method(params=['name'], calls=['DirectMapper.create'], feature="创建 direct 业务处理")
    def create_direct(self, name: str) -> dict | None:
        """创建 direct 业务处理。"""
        return self.direct_mapper.create(name)

    @service_method(params=[], calls=['DirectMapper.list'], feature="查询 direct 列表业务处理")
    def list_directs(self) -> dict | None:
        """查询 direct 列表业务处理。"""
        return self.direct_mapper.list()
