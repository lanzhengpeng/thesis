"""
AgentService 业务逻辑层。
"""

from dataclasses import dataclass
from typing import List, Optional

from paas_core import Service, service_method

from .AgentMapper import AgentMapper


@dataclass
class AgentItem:
    """服务层 Agent 领域模型。"""

    id: int
    name: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


@Service
class AgentService:
    def __init__(self, agent_mapper: AgentMapper):
        self.agent_mapper = agent_mapper

    @service_method(params=['name'], calls=['AgentMapper.create'], feature="创建 Agent")
    def create_agent(self, name: str) -> dict:
        """创建 Agent。"""
        new_item = self.agent_mapper.create(name)
        return AgentItem(**new_item).to_dict()

    @service_method(params=['id'], calls=['AgentMapper.get_by_id'], feature="查询 Agent 详情")
    def get_agent(self, id: str) -> Optional[dict]:
        """查询 Agent 详情。"""
        item = self.agent_mapper.get_by_id(int(id))
        if item is None:
            return None
        return AgentItem(**item).to_dict()

    @service_method(params=[], calls=['AgentMapper.list'], feature="查询 Agent 列表")
    def list_agents(self) -> List[dict]:
        """查询 Agent 列表。"""
        rows = self.agent_mapper.list()
        return [AgentItem(**row).to_dict() for row in rows]
