"""
用户模块数据访问层。
"""

from paas_core import Mapper


@Mapper
class UserMapper:
    def __init__(self):
        # 内存中的用户存储（仅用于骨架演示）
        self._users = {}
        self._next_id = 1

    def create(self, username: str, email: str) -> dict:
        """创建用户。"""
        user_id = self._next_id
        self._next_id += 1
        user = {"id": user_id, "username": username, "email": email}
        self._users[user_id] = user
        return user

    def get(self, user_id: int) -> dict | None:
        """根据 ID 查询用户。"""
        return self._users.get(user_id)

    def list_all(self) -> list:
        """查询所有用户。"""
        return list(self._users.values())
