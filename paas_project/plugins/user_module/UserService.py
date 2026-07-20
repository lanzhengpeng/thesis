"""
用户模块业务逻辑层。
"""

from paas_core import Service
from .UserMapper import UserMapper


@Service
class UserService:
    def __init__(self, user_mapper: UserMapper):
        self.user_mapper = user_mapper

    def register(self, username: str, email: str) -> dict:
        """用户注册。"""
        return self.user_mapper.create(username, email)

    def get_user(self, user_id: int) -> dict | None:
        """查询单个用户。"""
        return self.user_mapper.get(user_id)

    def list_users(self) -> list:
        """查询用户列表。"""
        return self.user_mapper.list_all()
