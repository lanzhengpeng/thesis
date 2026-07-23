"""
AgentController HTTP 接口层。
"""

from paas_core import Controller, GET, POST
from .AgentService import AgentService

@Controller("/api/agents")
class AgentController:
    def __init__(self, agent_service: AgentService):
        self.agent_service = agent_service

    @GET("/", calls=['AgentService.list_agents'], feature="查询列表")
    def list_agents(self):
        """GET /api/agents/"""
        return self.agent_service.list_agents()

    @GET("/{id}", calls=['AgentService.get_agent'], feature="查询详情")
    def get_agent(self, id: str):
        """GET /api/agents/{id}"""
        item = self.agent_service.get_agent(int(id))
        if item is None:
            return {"error": "not found"}
        return item

    @POST("/", calls=['AgentService.create_agent'], feature="创建 Agent")
    def create_agent(self, payload: dict):
        """POST /api/agents/"""
        return self.agent_service.create_agent(**payload)
