"""
用户模块业务逻辑层。
"""

from dataclasses import dataclass
from typing import List, Optional

from paas_core import Service, service_method

from .UserMapper import UserMapper


@dataclass
class UserItem:
    """服务层 User 领域模型。"""

    id: int
    username: str
    email: str

    def to_dict(self) -> dict:
        return {"id": self.id, "username": self.username, "email": self.email}


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
        new_item = self.user_mapper.create(username, email)
        return UserItem(**new_item).to_dict()

    @service_method(
        params=["user_id"],
        calls=["UserMapper.get"],
        feature="查询用户",
    )
    def get_user(self, user_id: int) -> Optional[dict]:
        """查询单个用户。"""
        item = self.user_mapper.get(user_id)
        if item is None:
            return None
        return UserItem(**item).to_dict()

    @service_method(calls=["UserMapper.list_all"], feature="全量列表")
    def list_users(self) -> List[dict]:
        """查询用户列表。"""
        rows = self.user_mapper.list_all()
        return [UserItem(**row).to_dict() for row in rows]
