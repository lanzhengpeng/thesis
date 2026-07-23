"""
ItemController HTTP 接口层。
"""

from pydantic import BaseModel

from paas_core import Controller, GET, POST

from .ItemService import ItemService


class ItemCreateRequest(BaseModel):
    """创建 Item 的 API 请求体。"""

    name: str


class ItemResponse(BaseModel):
    """Item 的 API 响应体。"""

    id: int
    name: str


@Controller("/api/items")
class ItemController:
    def __init__(self, item_service: ItemService):
        self.item_service = item_service

    @GET("/", calls=['ItemService.list_items'], feature="查询列表")
    def list_items(self):
        """GET /api/items/"""
        return self.item_service.list_items()

    @GET("/{id}", calls=['ItemService.get_item'], feature="查询详情")
    def get_item(self, id: str):
        """GET /api/items/{id}"""
        item = self.item_service.get_item(id)
        if item is None:
            return {"error": "not found"}
        return ItemResponse(**item).model_dump()

    @POST("/", calls=['ItemService.create_item'], feature="创建")
    def create_item(self, payload: dict):
        """POST /api/items/"""
        req = ItemCreateRequest(**payload)
        new_item = self.item_service.create_item(req.name)
        return ItemResponse(**new_item).model_dump()
