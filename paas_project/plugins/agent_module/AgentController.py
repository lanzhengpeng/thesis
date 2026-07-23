"""
AgentController HTTP 接口层。
"""

from pydantic import BaseModel

from paas_core import Controller, GET, POST

from .AgentService import AgentService


class AgentCreateRequest(BaseModel):
    """创建 Agent 的 API 请求体。"""

    name: str


class AgentResponse(BaseModel):
    """Agent 的 API 响应体。"""

    id: int
    name: str


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
        item = self.agent_service.get_agent(id)
        if item is None:
            return {"error": "not found"}
        return AgentResponse(**item).model_dump()

    @POST("/", calls=['AgentService.create_agent'], feature="创建 Agent")
    def create_agent(self, payload: dict):
        """POST /api/agents/"""
        req = AgentCreateRequest(**payload)
        new_item = self.agent_service.create_agent(req.name)
        return AgentResponse(**new_item).model_dump()
