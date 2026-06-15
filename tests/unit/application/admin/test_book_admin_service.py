"""BookAdminService 单元测试 — 作者：Axelton"""
from unittest.mock import MagicMock
import pytest
from application.admin.book_admin_service import BookAdminService


@pytest.fixture
def mock_novel_repo():
    return MagicMock()


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def service(mock_novel_repo, mock_db):
    return BookAdminService(novel_repository=mock_novel_repo, db=mock_db)


def _create_mock_novel(
    novel_id: str = "n1",
    title: str = "Test Novel",
    author: str = "Author Name",
    current_stage: str = "writing",
    autopilot_status: str = "stopped",
    user_id: str = "u1",
):
    """创建模拟的 Novel 实体，匹配实际 Novel 实体属性访问模式"""
    mock = MagicMock()
    mock.novel_id.value = novel_id
    mock.title = title
    mock.author = author
    # 注意：从 DB 加载时 Novel 实体的 current_stage 才反映实际阶段
    # stage 是旧版兼容字段，_row_to_novel 中未传入，默认为 PLANNING
    mock.current_stage.value = current_stage
    mock.autopilot_status.value = autopilot_status
    mock.user_id = user_id
    return mock


class TestListBooks:
    def test_returns_paginated_books(self, service, mock_novel_repo, mock_db):
        """测试基本分页返回"""
        mock_novel = _create_mock_novel(
            novel_id="n1", title="Test Novel", author="Author",
            current_stage="writing", user_id="u1",
        )
        mock_novel_repo.list_all.return_value = [mock_novel]
        mock_db.fetch_one.return_value = {"word_count": 15000, "chapter_count": 10}

        result = service.list_books(page=1, page_size=20)

        assert result["total"] == 1
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == "n1"
        assert result["data"][0]["title"] == "Test Novel"
        assert result["data"][0]["author"] == "Author"
        assert result["data"][0]["stage"] == "writing"
        assert result["data"][0]["autopilot_status"] == "stopped"
        assert result["data"][0]["user_id"] == "u1"
        assert result["data"][0]["word_count"] == 15000
        assert result["data"][0]["chapter_count"] == 10

    def test_filters_by_search_title(self, service, mock_novel_repo, mock_db):
        """测试按标题搜索过滤"""
        n1 = _create_mock_novel(novel_id="n1", title="Star Wars")
        n2 = _create_mock_novel(novel_id="n2", title="Star Trek")
        n3 = _create_mock_novel(novel_id="n3", title="Dune")
        mock_novel_repo.list_all.return_value = [n1, n2, n3]
        mock_db.fetch_one.return_value = {"word_count": 0, "chapter_count": 0}

        result = service.list_books(search="Star")

        assert result["total"] == 2
        assert len(result["data"]) == 2
        titles = [b["title"] for b in result["data"]]
        assert "Star Wars" in titles
        assert "Star Trek" in titles

    def test_filters_by_search_id(self, service, mock_novel_repo, mock_db):
        """测试按 ID 搜索过滤"""
        n1 = _create_mock_novel(novel_id="abc123", title="Foo")
        n2 = _create_mock_novel(novel_id="xyz789", title="Bar")
        mock_novel_repo.list_all.return_value = [n1, n2]
        mock_db.fetch_one.return_value = {"word_count": 0, "chapter_count": 0}

        result = service.list_books(search="abc")

        assert result["total"] == 1
        assert result["data"][0]["id"] == "abc123"

    def test_filters_by_user_id(self, service, mock_novel_repo, mock_db):
        """测试按用户 ID 过滤"""
        n1 = _create_mock_novel(novel_id="n1", user_id="u1")
        n2 = _create_mock_novel(novel_id="n2", user_id="u2")
        mock_novel_repo.list_all.return_value = [n1, n2]
        mock_db.fetch_one.return_value = {"word_count": 0, "chapter_count": 0}

        result = service.list_books(user_id="u1")

        assert result["total"] == 1
        assert result["data"][0]["id"] == "n1"

    def test_filters_by_stage(self, service, mock_novel_repo, mock_db):
        """测试按阶段过滤（使用 current_stage.value）"""
        n1 = _create_mock_novel(novel_id="n1", current_stage="writing")
        n2 = _create_mock_novel(novel_id="n2", current_stage="completed")
        mock_novel_repo.list_all.return_value = [n1, n2]
        mock_db.fetch_one.return_value = {"word_count": 0, "chapter_count": 0}

        result = service.list_books(stage="writing")

        assert result["total"] == 1
        assert result["data"][0]["id"] == "n1"

    def test_pagination(self, service, mock_novel_repo, mock_db):
        """测试分页"""
        novels = [_create_mock_novel(novel_id=f"n{i}") for i in range(25)]
        mock_novel_repo.list_all.return_value = novels
        mock_db.fetch_one.return_value = {"word_count": 0, "chapter_count": 0}

        result = service.list_books(page=2, page_size=10)

        assert result["total"] == 25
        assert result["page"] == 2
        assert result["page_size"] == 10
        assert len(result["data"]) == 10
        # 第二页应该从索引 10 开始
        assert result["data"][0]["id"] == "n10"

    def test_empty_db_stats(self, service, mock_novel_repo, mock_db):
        """测试数据库统计返回 None 时的降级处理"""
        mock_novel = _create_mock_novel()
        mock_novel_repo.list_all.return_value = [mock_novel]
        mock_db.fetch_one.return_value = None  # 模拟无章节记录

        result = service.list_books()

        assert result["total"] == 1
        assert result["data"][0]["word_count"] == 0
        assert result["data"][0]["chapter_count"] == 0

    def test_combined_filters(self, service, mock_novel_repo, mock_db):
        """测试组合过滤"""
        n1 = _create_mock_novel(novel_id="n1", title="Epic", user_id="u1", current_stage="writing")
        n2 = _create_mock_novel(novel_id="n2", title="Epic II", user_id="u2", current_stage="writing")
        n3 = _create_mock_novel(novel_id="n3", title="Epic III", user_id="u1", current_stage="completed")
        mock_novel_repo.list_all.return_value = [n1, n2, n3]
        mock_db.fetch_one.return_value = {"word_count": 0, "chapter_count": 0}

        result = service.list_books(search="Epic", user_id="u1", stage="writing")

        assert result["total"] == 1
        assert result["data"][0]["id"] == "n1"


class TestDeleteBook:
    def test_deletes_novel(self, service, mock_novel_repo):
        """测试删除书籍时传入 NovelId 值对象"""
        service.delete_book("n1")
        mock_novel_repo.delete.assert_called_once()
        # 验证传入的是 NovelId 值对象
        call_arg = mock_novel_repo.delete.call_args[0][0]
        assert call_arg.value == "n1"


class TestTransferOwner:
    def test_transfers_owner(self, service, mock_novel_repo):
        """测试转移归属时传入 NovelId 值对象和 user_id 列名"""
        service.transfer_owner("n1", "new_user")
        mock_novel_repo.patch.assert_called_once()
        call_arg = mock_novel_repo.patch.call_args[0][0]
        assert call_arg.value == "n1"
        assert mock_novel_repo.patch.call_args[1] == {"user_id": "new_user"}
