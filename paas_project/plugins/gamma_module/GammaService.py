"""
GammaService 业务逻辑层。
"""

from dataclasses import dataclass
from typing import List, Optional

from paas_core import Service, service_method

from .GammaMapper import GammaMapper


@dataclass
class GammaItem:
    """服务层 Gamma 领域模型。"""

    id: int
    name: str
    status: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "status": self.status}


@Service
class GammaService:
    def __init__(self, gamma_mapper: GammaMapper):
        self.gamma_mapper = gamma_mapper

    @service_method(params=[], calls=["GammaMapper.list"], feature="查询 Gamma 测试实体列表")
    def list_gammas(self) -> List[dict]:
        """查询 Gamma 测试实体列表。"""
        rows = self.gamma_mapper.list()
        return [GammaItem(**row).to_dict() for row in rows]

    @service_method(params=["id"], calls=["GammaMapper.get_by_id"], feature="根据 ID 查询 Gamma 测试实体详情")
    def get_gamma(self, id: int) -> Optional[dict]:
        """根据 ID 查询 Gamma 测试实体详情。"""
        item = self.gamma_mapper.get_by_id(int(id))
        if item is None:
            return None
        return GammaItem(**item).to_dict()

    @service_method(params=["name", "status"], calls=["GammaMapper.create"], feature="创建新的 Gamma 测试实体")
    def create_gamma(self, name: str, status: str) -> dict:
        """创建新的 Gamma 测试实体。"""
        new_item = self.gamma_mapper.create(name, status)
        return GammaItem(**new_item).to_dict()
