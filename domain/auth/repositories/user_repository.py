"""用户仓储接口（抽象）

作者: Axelton
"""
from abc import ABC, abstractmethod
from typing import Optional
from domain.auth.entities.user import User


class UserRepository(ABC):
    """用户仓储接口"""

    @abstractmethod
    def save(self, user: User) -> None:
        """保存用户"""
        pass

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]:
        """根据 ID 获取用户"""
        pass

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        pass

    @abstractmethod
    def exists_by_username(self, username: str) -> bool:
        """检查用户名是否已存在"""
        pass

    @abstractmethod
    def count(self) -> int:
        """获取用户总数"""
        pass
