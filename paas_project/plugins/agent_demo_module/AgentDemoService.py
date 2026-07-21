"""
AgentDemoService 业务逻辑层。
"""

from paas_core import Service, service_method
from .AgentDemoMapper import AgentDemoMapper

@Service
class AgentDemoService:
    def __init__(self, agent_demo_mapper: AgentDemoMapper):
        self.agent_demo_mapper = agent_demo_mapper

    @service_method(params=[], calls=['AgentDemoMapper.list'], feature="查询 AgentDemo 列表")
    def list_agent_demos(self) -> dict | None:
        """查询 AgentDemo 列表。"""
        return self.agent_demo_mapper.list()

    @service_method(params=['id'], calls=['AgentDemoMapper.get_by_id'], feature="查询 AgentDemo 详情")
    def get_agent_demo(self, id: str) -> dict | None:
        """查询 AgentDemo 详情。"""
        return self.agent_demo_mapper.get(id)

    @service_method(params=['name'], calls=['AgentDemoMapper.create'], feature="创建 AgentDemo")
    def create_agent_demo(self, name: str) -> dict | None:
        """创建 AgentDemo。"""
        return self.agent_demo_mapper.create(name)
