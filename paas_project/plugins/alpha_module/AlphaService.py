"""
AlphaService 业务逻辑层。
"""

from dataclasses import dataclass
from typing import List, Optional

from paas_core import Service, service_method

from .AlphaMapper import AlphaMapper


@dataclass
class AlphaItem:
    """服务层 Alpha 领域模型。"""

    id: int
    name: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


@Service
class AlphaService:
    def __init__(self, alpha_mapper: AlphaMapper):
        self.alpha_mapper = alpha_mapper

    @service_method(params=['name'], calls=['AlphaMapper.create'], feature="创建 Alpha")
    def create_alpha(self, name: str) -> dict:
        """创建 Alpha。"""
        new_item = self.alpha_mapper.create(name)
        return AlphaItem(**new_item).to_dict()

    @service_method(params=['id'], calls=['AlphaMapper.get_by_id'], feature="查询 Alpha 详情")
    def get_alpha(self, id: str) -> Optional[dict]:
        """查询 Alpha 详情。"""
        item = self.alpha_mapper.get_by_id(int(id))
        if item is None:
            return None
        return AlphaItem(**item).to_dict()

    @service_method(params=[], calls=['AlphaMapper.list_all'], feature="查询 Alpha 列表")
    def list_alphas(self) -> List[dict]:
        """查询 Alpha 列表。"""
        rows = self.alpha_mapper.list_all()
        return [AlphaItem(**row).to_dict() for row in rows]
