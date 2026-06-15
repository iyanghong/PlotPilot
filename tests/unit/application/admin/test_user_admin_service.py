"""UserAdminService 单元测试 — 作者：Axelton"""
from unittest.mock import MagicMock

import pytest

from application.admin.user_admin_service import UserAdminService
from domain.auth.entities.user import User, UserRole


@pytest.fixture
def mock_repo():
    """模拟 UserRepository"""
    repo = MagicMock()
    repo.list_all.return_value = []
    repo.count.return_value = 0
    return repo


@pytest.fixture
def mock_auth():
    """模拟 AuthService"""
    return MagicMock()


@pytest.fixture
def service(mock_repo, mock_auth):
    """创建 UserAdminService 实例（注入模拟依赖）"""
    return UserAdminService(user_repository=mock_repo, auth_service=mock_auth)


class TestListUsers:
    """list_users 测试"""

    def test_returns_paginated_list(self, service, mock_repo):
        """验证返回分页列表"""
        mock_repo.count.return_value = 25
        mock_repo.list_all.return_value = [
            User(id="u1", username="alice", password_hash="h1", role=UserRole.USER),
            User(id="u2", username="bob", password_hash="h2", role=UserRole.ADMIN),
        ]

        result = service.list_users(page=1, page_size=10)

        assert result["total"] == 25
        assert result["page"] == 1
        assert result["page_size"] == 10
        assert len(result["data"]) == 2
        assert result["data"][0]["username"] == "alice"
        assert result["data"][1]["role"] == "admin"

    def test_with_search_filters_by_username(self, service, mock_repo):
        """验证搜索过滤"""
        mock_repo.count.return_value = 3
        mock_repo.list_all.return_value = [
            User(id="u1", username="alice", password_hash="h1", role=UserRole.USER),
            User(id="u2", username="bob", password_hash="h2", role=UserRole.ADMIN),
            User(id="u3", username="charlie", password_hash="h3", role=UserRole.USER),
        ]

        result = service.list_users(page=1, page_size=10, search="ali")

        assert result["total"] == 1  # 搜索后的匹配数
        assert len(result["data"]) == 1
        assert result["data"][0]["username"] == "alice"

    def test_pagination_second_page(self, service, mock_repo):
        """验证第二页分页"""
        mock_repo.count.return_value = 25
        mock_repo.list_all.return_value = [
            User(id=f"u{i}", username=f"user{i}", password_hash="h", role=UserRole.USER)
            for i in range(25)
        ]

        result = service.list_users(page=2, page_size=10)

        assert result["page"] == 2
        assert result["total"] == 25
        assert len(result["data"]) == 10
        assert result["data"][0]["username"] == "user10"


class TestCreateUser:
    """create_user 测试"""

    def test_delegates_to_auth_service_with_user_role_enum(self, service, mock_auth):
        """验证将字符串角色转换为 UserRole 枚举后委托给 AuthService"""
        mock_auth.register.return_value = User(
            id="u3", username="charlie", password_hash="hash", role=UserRole.USER
        )

        result = service.create_user(username="charlie", password="secret123")

        mock_auth.register.assert_called_once_with("charlie", "secret123", UserRole.USER)
        assert result.username == "charlie"

    def test_creates_admin_user(self, service, mock_auth):
        """验证创建管理员用户"""
        mock_auth.register.return_value = User(
            id="u4", username="admin2", password_hash="hash", role=UserRole.ADMIN
        )

        result = service.create_user(username="admin2", password="secret123", role="admin")

        mock_auth.register.assert_called_once_with("admin2", "secret123", UserRole.ADMIN)
        assert result.role == UserRole.ADMIN

    def test_raises_value_error_on_duplicate_username(self, service, mock_auth):
        """验证用户名重复时抛出 ValueError"""
        mock_auth.register.return_value = None  # AuthService 返回 None 表示用户名已存在

        with pytest.raises(ValueError, match="用户名已存在"):
            service.create_user(username="alice", password="secret123")

    def test_invalid_role_falls_back_to_user(self, service, mock_auth):
        """验证无效角色值回退到 USER"""
        mock_auth.register.return_value = User(
            id="u5", username="test", password_hash="hash", role=UserRole.USER
        )

        result = service.create_user(username="test", password="secret123", role="invalid_role")

        mock_auth.register.assert_called_once_with("test", "secret123", UserRole.USER)
        assert result.role == UserRole.USER


class TestUpdateUser:
    """update_user 测试"""

    def test_updates_role(self, service, mock_repo):
        """验证更新角色"""
        user = User(id="u1", username="alice", password_hash="h1", role=UserRole.USER)
        mock_repo.get_by_id.return_value = user

        result = service.update_user(user_id="u1", role="admin")

        assert result.role == UserRole.ADMIN
        mock_repo.save.assert_called_once_with(user)

    def test_updates_password(self, service, mock_repo):
        """验证更新密码（应重新哈希）"""
        user = User(id="u1", username="alice", password_hash="old_hash", role=UserRole.USER)
        mock_repo.get_by_id.return_value = user

        result = service.update_user(user_id="u1", password="new_password")

        assert result.password_hash != "old_hash"
        assert result.password_hash != "new_password"  # 应该是哈希后的值
        mock_repo.save.assert_called_once_with(user)

    def test_updates_both_role_and_password(self, service, mock_repo):
        """验证同时更新角色和密码"""
        user = User(id="u1", username="alice", password_hash="old_hash", role=UserRole.USER)
        mock_repo.get_by_id.return_value = user

        result = service.update_user(user_id="u1", role="admin", password="new_password")

        assert result.role == UserRole.ADMIN
        assert result.password_hash != "old_hash"
        mock_repo.save.assert_called_once()

    def test_raises_value_error_when_user_not_found(self, service, mock_repo):
        """验证用户不存在时抛出 ValueError"""
        mock_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="用户不存在"):
            service.update_user(user_id="nonexistent", role="admin")


class TestDeleteUser:
    """delete_user 测试"""

    def test_deletes_existing_user(self, service, mock_repo):
        """验证删除存在的用户"""
        user = User(id="u1", username="alice", password_hash="h1", role=UserRole.USER)
        mock_repo.get_by_id.return_value = user

        service.delete_user(user_id="u1")

        mock_repo.delete.assert_called_once_with("u1")

    def test_raises_value_error_when_user_not_found(self, service, mock_repo):
        """验证删除不存在的用户抛出 ValueError"""
        mock_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="用户不存在"):
            service.delete_user(user_id="nonexistent")
