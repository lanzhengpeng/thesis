"""
用户模块 HTTP 接口层。
"""

from pydantic import BaseModel

from paas_core import Controller, GET, POST, HTTPException

from .UserService import UserService


class UserCreateRequest(BaseModel):
    """创建用户的 API 请求体。"""

    username: str
    email: str


class UserResponse(BaseModel):
    """用户的 API 响应体。"""

    id: int
    username: str
    email: str


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
        return UserResponse(**user).model_dump()

    @POST("/", calls=["UserService.register"], feature="创建用户")
    def create_user(self, payload: dict):
        """POST /api/users/"""
        req = UserCreateRequest(**payload)
        if not req.username:
            raise HTTPException(status_code=400, detail="username is required")
        if not req.email or "@" not in req.email:
            raise HTTPException(status_code=400, detail="email is required and must contain '@'")
        new_item = self.user_service.register(req.username, req.email)
        return UserResponse(**new_item).model_dump()
