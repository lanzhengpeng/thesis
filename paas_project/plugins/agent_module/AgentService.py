"""
AgentService 业务逻辑层。
"""

from paas_core import Service, service_method
from .AgentMapper import AgentMapper

@Service
class AgentService:
    def __init__(self, agent_mapper: AgentMapper):
        self.agent_mapper = agent_mapper

    @service_method(params=['name'], calls=['AgentMapper.create'], feature="创建 Agent")
    def create_agent(self, name: str) -> dict | None:
        """创建 Agent。"""
        return self.agent_mapper.create(name)

    @service_method(params=['id'], calls=['AgentMapper.get_by_id'], feature="查询 Agent 详情")
    def get_agent(self, id: str) -> dict | None:
        """查询 Agent 详情。"""
        return self.agent_mapper.get(id)

    @service_method(params=[], calls=['AgentMapper.list'], feature="查询 Agent 列表")
    def list_agents(self) -> dict | None:
        """查询 Agent 列表。"""
        return self.agent_mapper.list()
