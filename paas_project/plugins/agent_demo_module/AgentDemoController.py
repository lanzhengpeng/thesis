"""
AgentDemoController HTTP 接口层。
"""

from paas_core import Controller, GET, POST
from .AgentDemoService import AgentDemoService

@Controller("/api/agent_demos")
class AgentDemoController:
    def __init__(self, agent_demo_service: AgentDemoService):
        self.agent_demo_service = agent_demo_service

    @GET("/", calls=['AgentDemoService.list_agent_demos'], feature="查询列表")
    def list_agent_demos(self):
        """GET /api/agent_demos/"""
        return self.agent_demo_service.list_agent_demos()

    @GET("/{id}", calls=['AgentDemoService.get_agent_demo'], feature="查询详情")
    def get_agent_demo(self, id: str):
        """GET /api/agent_demos/{id}"""
        item = self.agent_demo_service.get_agent_demo(int(id))
        if item is None:
            return {"error": "not found"}
        return item

    @POST("/", calls=['AgentDemoService.create_agent_demo'], feature="创建")
    def create_agent_demo(self, payload: dict):
        """POST /api/agent_demos/"""
        return self.agent_demo_service.create_agent_demo(**payload)
