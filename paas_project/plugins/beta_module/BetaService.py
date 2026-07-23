"""
BetaService 业务逻辑层。
"""

from dataclasses import dataclass
from typing import List, Optional

from paas_core import Service, service_method

from .BetaMapper import BetaMapper


@dataclass
class BetaItem:
    """服务层 Beta 领域模型。"""

    id: int
    name: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


@Service
class BetaService:
    def __init__(self, beta_mapper: BetaMapper):
        self.beta_mapper = beta_mapper

    @service_method(params=[], calls=['BetaMapper.list'], feature="查询 Beta 列表")
    def list_betas(self) -> List[dict]:
        """查询 Beta 列表。"""
        rows = self.beta_mapper.list()
        return [BetaItem(**row).to_dict() for row in rows]

    @service_method(params=['id'], calls=['BetaMapper.get_by_id'], feature="查询 Beta 详情")
    def get_beta(self, id: str) -> Optional[dict]:
        """查询 Beta 详情。"""
        item = self.beta_mapper.get_by_id(int(id))
        if item is None:
            return None
        return BetaItem(**item).to_dict()

    @service_method(params=['name'], calls=['BetaMapper.create'], feature="创建 Beta")
    def create_beta(self, name: str) -> dict:
        """创建 Beta。"""
        new_item = self.beta_mapper.create(name)
        return BetaItem(**new_item).to_dict()
