"""用户管理应用服务 — 作者：Axelton"""
from __future__ import annotations
import logging
from typing import Any, Dict, List

from domain.auth.entities.user import User, UserRole
from domain.auth.repositories.user_repository import UserRepository
from application.auth.auth_service import AuthService, _hash_password

logger = logging.getLogger(__name__)


class UserAdminService:
    """用户管理编排 — 组合 UserRepository 和 AuthService"""

    def __init__(self, user_repository: UserRepository, auth_service: AuthService):
        self._repo = user_repository
        self._auth = auth_service

    def list_users(self, page: int = 1, page_size: int = 20, search: str = "") -> Dict[str, Any]:
        """列出用户（分页 + 搜索）

        Args:
            page: 页码（从 1 开始）
            page_size: 每页数量
            search: 用户名搜索关键词

        Returns:
            包含 data / total / page / page_size 的字典
        """
        all_users = self._repo.list_all()
        total = self._repo.count()

        # 用户名模糊搜索
        if search:
            all_users = [u for u in all_users if search.lower() in u.username.lower()]

        # 内存分页
        start = (page - 1) * page_size
        page_users = all_users[start:start + page_size]

        return {
            "data": [
                {"id": u.id, "username": u.username, "role": u.role.value}
                for u in page_users
            ],
            "total": len(all_users) if search else total,
            "page": page,
            "page_size": page_size,
        }

    def create_user(self, username: str, password: str, role: str = None) -> User:
        """创建用户

        Args:
            username: 用户名
            password: 密码
            role: 角色（"admin" 或 "user"，默认 "user"）

        Returns:
            创建成功的 User 对象

        Raises:
            ValueError: 用户名已存在
        """
        # 将字符串角色转换为 UserRole 枚举
        if role:
            try:
                user_role = UserRole(role)
            except ValueError:
                user_role = UserRole.USER
        else:
            user_role = UserRole.USER

        user = self._auth.register(username, password, user_role)
        if user is None:
            raise ValueError(f"用户名已存在: {username}")
        logger.info("管理员创建用户: %s (角色: %s)", username, user_role.value)
        return user

    def update_user(self, user_id: str, role: str = None, password: str = None) -> User:
        """更新用户

        Args:
            user_id: 用户 ID
            role: 新角色（可选）
            password: 新密码（可选）

        Returns:
            更新后的 User 对象

        Raises:
            ValueError: 用户不存在
        """
        user = self._repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"用户不存在: {user_id}")

        if role:
            try:
                user.role = UserRole(role)
            except ValueError:
                pass  # 忽略无效角色值

        if password:
            user.password_hash = _hash_password(password)

        self._repo.save(user)
        logger.info("管理员更新用户: %s", user.username)
        return user

    def delete_user(self, user_id: str) -> None:
        """删除用户

        Args:
            user_id: 用户 ID

        Raises:
            ValueError: 用户不存在
        """
        user = self._repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"用户不存在: {user_id}")
        self._repo.delete(user.id)
        logger.info("管理员删除用户: %s", user.username)
