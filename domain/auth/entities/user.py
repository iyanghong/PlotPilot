"""用户实体和角色枚举

作者: Axelton
"""
from enum import Enum
from typing import Any
from domain.shared.base_entity import BaseEntity


class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"  # 管理员：可查看所有小说
    USER = "user"  # 普通用户：仅查看自己的小说


class User(BaseEntity):
    """用户实体"""

    def __init__(
        self,
        id: str,
        username: str,
        password_hash: str,
        role: UserRole = UserRole.USER,
    ):
        super().__init__(id)
        self.username = username
        self.password_hash = password_hash
        self.role = role

    def is_admin(self) -> bool:
        """是否管理员"""
        return self.role == UserRole.ADMIN

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, User):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, username={self.username!r}, role={self.role.value!r})"
