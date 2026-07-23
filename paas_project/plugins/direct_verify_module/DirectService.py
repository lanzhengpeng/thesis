"""
DirectService 业务逻辑层。
"""

from dataclasses import dataclass
from typing import List

from paas_core import Service, service_method

from .DirectMapper import DirectMapper


@dataclass
class DirectItem:
    """服务层 Direct 领域模型。"""

    id: int
    name: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


@Service
class DirectService:
    def __init__(self, direct_mapper: DirectMapper):
        self.direct_mapper = direct_mapper

    @service_method(params=[], calls=['DirectMapper.list'], feature="查询 direct 列表业务处理")
    def list_directs(self) -> List[dict]:
        """查询 direct 列表业务处理。"""
        rows = self.direct_mapper.list()
        return [DirectItem(**row).to_dict() for row in rows]

    @service_method(params=['name'], calls=['DirectMapper.create'], feature="创建 direct 业务处理")
    def create_direct(self, name: str) -> dict:
        """创建 direct 业务处理。"""
        new_item = self.direct_mapper.create(name)
        return DirectItem(**new_item).to_dict()
