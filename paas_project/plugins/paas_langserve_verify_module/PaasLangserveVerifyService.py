"""
PaasLangserveVerifyService 业务逻辑层。
"""

from dataclasses import dataclass
from typing import List, Optional

from paas_core import Service, service_method

from .PaasLangserveVerifyMapper import PaasLangserveVerifyMapper


@dataclass
class PaasLangserveVerifyItem:
    """服务层 PaasLangserveVerify 领域模型。"""

    id: int
    name: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


@Service
class PaasLangserveVerifyService:
    def __init__(self, paas_langserve_verify_mapper: PaasLangserveVerifyMapper):
        self.paas_langserve_verify_mapper = paas_langserve_verify_mapper

    @service_method(params=[], calls=['PaasLangserveVerifyMapper.list'], feature="查询列表")
    def list(self) -> List[dict]:
        """查询列表。"""
        rows = self.paas_langserve_verify_mapper.list()
        return [PaasLangserveVerifyItem(**row).to_dict() for row in rows]

    @service_method(params=['id'], calls=['PaasLangserveVerifyMapper.get_by_id'], feature="查询详情")
    def get_detail(self, id: str) -> Optional[dict]:
        """查询详情。"""
        item = self.paas_langserve_verify_mapper.get_by_id(int(id))
        if item is None:
            return None
        return PaasLangserveVerifyItem(**item).to_dict()

    @service_method(params=['name'], calls=['PaasLangserveVerifyMapper.create'], feature="创建记录")
    def create(self, name: str) -> dict:
        """创建记录。"""
        new_item = self.paas_langserve_verify_mapper.create(name)
        return PaasLangserveVerifyItem(**new_item).to_dict()
