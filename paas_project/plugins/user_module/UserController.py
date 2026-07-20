"""
用户模块 HTTP 接口层。
"""

from paas_core import Controller, GET, POST
from .UserService import UserService


@Controller("/api/users")
class UserController:
    def __init__(self, user_service: UserService):
        self.user_service = user_service

    @GET("/")
    def list_users(self):
        """GET /api/users/"""
        return self.user_service.list_users()

    @GET("/{user_id}")
    def get_user(self, user_id: str):
        """GET /api/users/{user_id}"""
        user = self.user_service.get_user(int(user_id))
        if user is None:
            return {"error": "not found"}
        return user

    @POST("/")
    def create_user(self, payload: dict):
        """POST /api/users/"""
        return self.user_service.register(
            payload.get("username", ""),
            payload.get("email", ""),
        )
