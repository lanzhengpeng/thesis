"""
用户模块 HTTP 接口层。
"""

from paas_core import Controller, GET, POST
from .UserService import UserService


@Controller("/api/users")
class UserController:
    def __init__(self, user_service: UserService):
        self.user_service = user_service

    @GET("/", calls=["UserService.list_users"], feature="查询列表")
    def list_users(self):
        """GET /api/users/"""
        return self.user_service.list_users()

    @GET("/{user_id}", calls=["UserService.get_user"], feature="查询用户")
    def get_user(self, user_id: str):
        """GET /api/users/{user_id}"""
        user = self.user_service.get_user(int(user_id))
        if user is None:
            return {"error": "not found"}
        return user

    @POST("/", calls=["UserService.register"], feature="创建用户")
    def create_user(self, payload: dict):
        """POST /api/users/"""
        return self.user_service.register(
            payload.get("username", ""),
            payload.get("email", ""),
        )
