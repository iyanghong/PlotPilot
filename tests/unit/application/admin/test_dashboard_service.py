# tests/unit/application/admin/test_dashboard_service.py
"""DashboardService 单元测试 — 作者：Axelton"""
from unittest.mock import MagicMock, call
import pytest
from application.admin.dashboard_service import DashboardService


@pytest.fixture
def mock_db():
    db = MagicMock()
    return db


@pytest.fixture
def service(mock_db):
    return DashboardService(mock_db)


class TestGetWritingStats:
    def test_returns_structure_with_scope_all(self, service, mock_db):
        """all 作用域返回全局写作统计"""
        mock_db.fetch_one.side_effect = [
            {"total_words": 50000, "total_chapters": 200, "completed_novels": 3,
             "avg_words_per_chapter": 250.0},
        ]
        mock_db.fetch_all.side_effect = [
            [{"date": "2026-06-14", "word_count": 1000}],
        ]

        result = service.get_writing_stats(scope="all")

        assert result["total_words"] == 50000
        assert result["total_chapters"] == 200
        assert result["completed_novels"] == 3
        assert result["avg_words_per_chapter"] == 250.0
        assert len(result["daily_trend"]) == 1

    def test_scope_user_filters_by_user_id(self, service, mock_db):
        """user 作用域通过 user_id 参数过滤并传给 SQL"""
        mock_db.fetch_one.return_value = {
            "total_words": 10000, "total_chapters": 50,
            "completed_novels": 1, "avg_words_per_chapter": 200.0,
        }
        mock_db.fetch_all.return_value = []

        result = service.get_writing_stats(scope="user", user_id="user-1")

        # user_id 应被传给 SQL 占位符
        args_list = mock_db.fetch_one.call_args
        assert "user-1" in args_list[0][1]

    def test_default_scope_is_all(self, service, mock_db):
        """默认 scope=all"""
        mock_db.fetch_one.return_value = {
            "total_words": 0, "total_chapters": 0,
            "completed_novels": 0, "avg_words_per_chapter": 0.0,
        }
        mock_db.fetch_all.return_value = []

        result = service.get_writing_stats()

        assert result["total_words"] == 0


class TestGetAiUsageStats:
    def test_returns_ai_usage_with_model_breakdown(self, service, mock_db):
        """返回 AI 调用统计含模型维度分组"""
        mock_db.fetch_one.side_effect = [
            {"total_calls": 500, "total_tokens": 300000},
            {"today_calls": 20, "today_tokens": 15000, "avg_latency_ms": 850.0},
        ]
        mock_db.fetch_all.side_effect = [
            [{"model": "claude", "calls": 300, "tokens": 200000}],
            [{"date": "2026-06-14", "call_count": 15}],
        ]

        result = service.get_ai_usage_stats(scope="all")

        assert result["total_calls"] == 500
        assert result["total_tokens"] == 300000
        assert result["today_calls"] == 20
        assert result["today_tokens"] == 15000
        assert result["avg_latency_ms"] == 850.0
        assert len(result["by_model"]) == 1
        assert len(result["daily_trend"]) == 1


class TestGetBookStats:
    def test_returns_book_stats_with_stage_distribution(self, service, mock_db):
        """返回书籍统计含阶段分布"""
        mock_db.fetch_one.return_value = {"total": 50, "active_this_week": 12}
        mock_db.fetch_all.side_effect = [
            [
                {"stage": "writing", "cnt": 20},
                {"stage": "planning", "cnt": 15},
            ],
            [{"week": "2026-W24", "count": 3}],
        ]

        result = service.get_book_stats(scope="all")

        assert result["total"] == 50
        assert result["active_this_week"] == 12
        assert result["by_stage"]["writing"] == 20
        assert result["by_stage"]["planning"] == 15
        assert len(result["weekly_new_trend"]) == 1


class TestGetQualityStats:
    def test_returns_quality_stats(self, service, mock_db):
        """返回叙事质量统计数据"""
        mock_db.fetch_one.side_effect = [
            {"closure_rate": 0.65, "open_count": 35},
            {"avg_score": 0.78},
            {"pass_rate": 0.82},
            {"drift_alerts": 3},
        ]

        result = service.get_quality_stats(scope="all")

        assert result["foreshadow_closure_rate"] == 0.65
        assert result["open_foreshadows"] == 35
        assert result["avg_style_score"] == 0.78
        assert result["audit_pass_rate"] == 0.82
        assert result["drift_alerts"] == 3


class TestGetCastForeshadowStats:
    def test_returns_character_and_foreshadow_stats(self, service, mock_db):
        """返回人物和伏笔统计"""
        mock_db.fetch_one.side_effect = [
            {"avg_characters": 8.5, "total_foreshadows": 120},
        ]
        mock_db.fetch_all.side_effect = [
            [{"status": "planted", "cnt": 50}, {"status": "closed", "cnt": 70}],
            [{"type": "protagonist", "cnt": 30}],
            [{"novel_id": "n1", "title": "Test", "character_count": 15}],
            [{"novel_id": "n1", "title": "Test", "foreshadow_count": 40}],
        ]

        result = service.get_cast_foreshadow_stats(scope="all")

        assert result["avg_characters_per_novel"] == 8.5
        assert result["total_foreshadows"] == 120
        assert result["by_status"]["planted"] == 50
        assert result["by_status"]["closed"] == 70
        assert len(result["top_novels_by_characters"]) == 1
