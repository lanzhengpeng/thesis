"""
AgentDemoService 业务逻辑层。
"""

from dataclasses import dataclass
from typing import List, Optional

from paas_core import Service, service_method

from .AgentDemoMapper import AgentDemoMapper


@dataclass
class AgentDemoItem:
    """服务层 AgentDemo 领域模型。"""

    id: int
    name: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


@Service
class AgentDemoService:
    def __init__(self, agent_demo_mapper: AgentDemoMapper):
        self.agent_demo_mapper = agent_demo_mapper

    @service_method(params=[], calls=['AgentDemoMapper.list'], feature="查询 AgentDemo 列表")
    def list_agent_demos(self) -> List[dict]:
        """查询 AgentDemo 列表。"""
        rows = self.agent_demo_mapper.list()
        return [AgentDemoItem(**row).to_dict() for row in rows]

    @service_method(params=['id'], calls=['AgentDemoMapper.get_by_id'], feature="查询 AgentDemo 详情")
    def get_agent_demo(self, id: str) -> Optional[dict]:
        """查询 AgentDemo 详情。"""
        item = self.agent_demo_mapper.get_by_id(int(id))
        if item is None:
            return None
        return AgentDemoItem(**item).to_dict()

    @service_method(params=['name'], calls=['AgentDemoMapper.create'], feature="创建 AgentDemo")
    def create_agent_demo(self, name: str) -> dict:
        """创建 AgentDemo。"""
        new_item = self.agent_demo_mapper.create(name)
        return AgentDemoItem(**new_item).to_dict()
