"""
用户模块业务逻辑层。
"""

from paas_core import Service, service_method
from .UserMapper import UserMapper


@Service
class UserService:
    def __init__(self, user_mapper: UserMapper):
        self.user_mapper = user_mapper

    @service_method(
        params=["username", "email"],
        calls=["UserMapper.create"],
        feature="用户注册",
    )
    def register(self, username: str, email: str) -> dict:
        """用户注册。"""
        return self.user_mapper.create(username, email)

    @service_method(
        params=["user_id"],
        calls=["UserMapper.get"],
        feature="查询用户",
    )
    def get_user(self, user_id: int) -> dict | None:
        """查询单个用户。"""
        return self.user_mapper.get(user_id)

    @service_method(calls=["UserMapper.list_all"], feature="全量列表")
    def list_users(self) -> list:
        """查询用户列表。"""
        return self.user_mapper.list_all()
