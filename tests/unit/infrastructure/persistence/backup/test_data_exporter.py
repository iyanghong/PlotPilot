"""数据库表数据动态发现 + JSON 导出单元测试 — 作者：Axelton"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from infrastructure.persistence.backup.data_exporter import (
    BackupData,
    DataExporter,
)


# ============================================================
#  辅助函数：创建模拟 db 对象
# ============================================================
def _make_mock_db(fetch_all_return=None, fetch_one_return=None):
    """创建一个带有 fetch_all 和 fetch_one 的模拟 db 对象。"""
    db = MagicMock()
    if fetch_all_return is not None:
        db.fetch_all.return_value = fetch_all_return
    if fetch_one_return is not None:
        db.fetch_one.return_value = fetch_one_return
    return db


def _make_pragma_result(columns: list):
    """构造 PRAGMA table_info 的返回结果。

    每个元素是一个包含 "name" 键的字典。
    """
    return [{"name": col} for col in columns]


# ============================================================
#  测试：_has_column
# ============================================================
class TestHasColumn:
    """测试 _has_column 方法"""

    def test_returns_true_when_column_exists(self):
        """当列存在时返回 True"""
        db = _make_mock_db(
            fetch_all_return=_make_pragma_result(["id", "novel_id", "title"])
        )
        exporter = DataExporter()
        result = exporter._has_column(db, "test_table", "novel_id")
        assert result is True
        db.fetch_all.assert_called_once_with("PRAGMA table_info('test_table')")

    def test_returns_false_when_column_absent(self):
        """当列不存在时返回 False"""
        db = _make_mock_db(
            fetch_all_return=_make_pragma_result(["id", "title", "content"])
        )
        exporter = DataExporter()
        result = exporter._has_column(db, "test_table", "novel_id")
        assert result is False

    def test_returns_false_on_exception(self):
        """PRAGMA 查询异常时返回 False"""
        db = _make_mock_db()
        db.fetch_all.side_effect = Exception("table not found")
        exporter = DataExporter()
        result = exporter._has_column(db, "bad_table", "novel_id")
        assert result is False


# ============================================================
#  测试：_discover_novel_tables
# ============================================================
class TestDiscoverNovelTables:
    """测试 _discover_novel_tables 方法"""

    def test_finds_tables_with_novel_id(self):
        """能找到含有 novel_id 列的表"""
        # sqlite_master 返回所有用户表
        all_tables = [
            {"name": "novels"},
            {"name": "chapters"},
            {"name": "users"},
            {"name": "characters"},
            {"name": "worldbuilding_items"},
            {"name": "sqlite_sequence"},
        ]

        # PRAGMA table_info 按表名返回不同结果
        def fetch_all_side_effect(sql, params=()):
            if sql.startswith("SELECT name FROM sqlite_master"):
                return all_tables
            if "PRAGMA table_info('novels')" in sql:
                return _make_pragma_result(["id", "novel_id", "title"])
            if "PRAGMA table_info('chapters')" in sql:
                return _make_pragma_result(["id", "novel_id", "number"])
            if "PRAGMA table_info('users')" in sql:
                return _make_pragma_result(["id", "username", "password"])
            if "PRAGMA table_info('characters')" in sql:
                return _make_pragma_result(["id", "name", "novel_id"])
            if "PRAGMA table_info('worldbuilding_items')" in sql:
                return _make_pragma_result(["id", "name"])
            return []

        db = _make_mock_db()
        db.fetch_all.side_effect = fetch_all_side_effect

        exporter = DataExporter()
        result = exporter._discover_novel_tables(db)

        # novels, chapters, characters 有 novel_id
        # users 是全局表，应被排除
        # worldbuilding_items 无 novel_id 列
        assert sorted(result) == ["chapters", "characters", "novels"]

    def test_excludes_global_tables(self):
        """排除 _GLOBAL_TABLES 中的全局表"""
        all_tables = [{"name": "users"}, {"name": "system_settings"}, {"name": "novels"}]

        def fetch_all_side_effect(sql, params=()):
            if sql.startswith("SELECT name FROM sqlite_master"):
                return all_tables
            if "PRAGMA table_info('novels')" in sql:
                return _make_pragma_result(["id", "novel_id"])
            if "PRAGMA table_info('users')" in sql:
                return _make_pragma_result(["id", "username"])
            return []

        db = _make_mock_db()
        db.fetch_all.side_effect = fetch_all_side_effect

        exporter = DataExporter()
        result = exporter._discover_novel_tables(db)

        # users 和 system_settings 都应被排除
        assert "users" not in result
        assert "system_settings" not in result
        # novels 应被包含
        assert "novels" in result


# ============================================================
#  测试：_export_table_rows
# ============================================================
class TestExportTableRows:
    """测试 _export_table_rows 方法"""

    def test_returns_rows_for_novel_id(self):
        """返回指定 novel_id 的数据行"""
        expected_rows = [
            {"id": "ch1", "novel_id": "nov1", "title": "Chapter 1"},
            {"id": "ch2", "novel_id": "nov1", "title": "Chapter 2"},
        ]
        db = _make_mock_db(fetch_all_return=expected_rows)

        exporter = DataExporter()
        result = exporter._export_table_rows(db, "chapters", "nov1")

        assert result == expected_rows
        db.fetch_all.assert_called_once_with(
            'SELECT * FROM "chapters" WHERE novel_id = ?', ("nov1",)
        )

    def test_returns_empty_list_on_exception(self):
        """异常时返回空列表"""
        db = _make_mock_db()
        db.fetch_all.side_effect = Exception("no such table")

        exporter = DataExporter()
        result = exporter._export_table_rows(db, "bad_table", "nov1")

        assert result == []


# ============================================================
#  测试：_export_indirect_table
# ============================================================
class TestExportIndirectTable:
    """测试 _export_indirect_table 方法"""

    def test_executes_join_sql_and_returns_rows(self):
        """执行 JOIN SQL 并返回结果"""
        expected_rows = [
            {"id": "msg1", "session_id": "s1", "content": "Hello"},
        ]
        db = _make_mock_db(fetch_all_return=expected_rows)

        join_sql = (
            "SELECT am.* FROM {table} am "
            "JOIN assist_sessions s ON am.session_id = s.id "
            "WHERE s.novel_id = ?"
        )
        params_fn = lambda novel_id: (novel_id,)

        exporter = DataExporter()
        result = exporter._export_indirect_table(
            db, "assist_messages", join_sql, params_fn, "nov1"
        )

        expected_sql = (
            "SELECT am.* FROM assist_messages am "
            "JOIN assist_sessions s ON am.session_id = s.id "
            "WHERE s.novel_id = ?"
        )
        assert result == expected_rows
        db.fetch_all.assert_called_once_with(expected_sql, ("nov1",))

    def test_returns_empty_list_on_exception(self):
        """异常时返回空列表"""
        db = _make_mock_db()
        db.fetch_all.side_effect = Exception("join failed")

        join_sql = "SELECT am.* FROM {table} am JOIN assist_sessions s ON am.session_id = s.id WHERE s.novel_id = ?"
        params_fn = lambda novel_id: (novel_id,)

        exporter = DataExporter()
        result = exporter._export_indirect_table(
            db, "assist_messages", join_sql, params_fn, "nov1"
        )

        assert result == []


# ============================================================
#  测试：export_novel_data
# ============================================================
class TestExportNovelData:
    """测试 export_novel_data 主方法"""

    def test_builds_backup_data_with_correct_tables(self):
        """构建包含正确表数据的 BackupData"""
        # 模拟发现到的表
        all_tables = [
            {"name": "novels"},
            {"name": "chapters"},
            {"name": "users"},
        ]

        # 模拟表数据行
        novel_rows = [{"id": "nov1", "novel_id": "nov1", "title": "My Novel"}]
        chapter_rows = [
            {"id": "ch1", "novel_id": "nov1", "number": 1},
            {"id": "ch2", "novel_id": "nov1", "number": 2},
        ]

        def fetch_all_side_effect(sql, params=()):
            if sql.startswith("SELECT name FROM sqlite_master"):
                return all_tables
            if "PRAGMA table_info('novels')" in sql:
                return _make_pragma_result(["id", "novel_id", "title"])
            if "PRAGMA table_info('chapters')" in sql:
                return _make_pragma_result(["id", "novel_id", "number"])
            if "PRAGMA table_info('users')" in sql:
                return _make_pragma_result(["id", "username"])
            if 'SELECT * FROM "novels" WHERE novel_id' in sql:
                return novel_rows
            if 'SELECT * FROM "chapters" WHERE novel_id' in sql:
                return chapter_rows
            # 间接表 assist_messages 返回空
            if "JOIN assist_sessions" in sql:
                return []
            return []

        db = _make_mock_db()
        db.fetch_all.side_effect = fetch_all_side_effect

        exporter = DataExporter()
        result = exporter.export_novel_data(db, "nov1")

        assert isinstance(result, BackupData)
        assert result.novel_id == "nov1"
        assert result.version == "1.0"
        assert result.source_db_type == "sqlite"
        # users 是全局表，不应出现在导出结果中
        assert "users" not in result.tables
        # novels 和 chapters 应在结果中
        assert "novels" in result.tables
        assert result.tables["novels"] == novel_rows
        assert "chapters" in result.tables
        assert result.tables["chapters"] == chapter_rows

    def test_empty_tables_are_omitted(self):
        """空表不应出现在结果中"""
        all_tables = [{"name": "novels"}, {"name": "chapters"}]

        def fetch_all_side_effect(sql, params=()):
            if sql.startswith("SELECT name FROM sqlite_master"):
                return all_tables
            if "PRAGMA table_info('novels')" in sql:
                return _make_pragma_result(["id", "novel_id", "title"])
            if "PRAGMA table_info('chapters')" in sql:
                return _make_pragma_result(["id", "novel_id", "number"])
            # novels 表有数据
            if 'SELECT * FROM "novels" WHERE novel_id' in sql:
                return [{"id": "nov1", "novel_id": "nov1", "title": "Test"}]
            # chapters 表为空
            if 'SELECT * FROM "chapters" WHERE novel_id' in sql:
                return []
            # 间接表返回空
            if "JOIN assist_sessions" in sql:
                return []
            return []

        db = _make_mock_db()
        db.fetch_all.side_effect = fetch_all_side_effect

        exporter = DataExporter()
        result = exporter.export_novel_data(db, "nov1")

        # novels 有数据，应存在
        assert "novels" in result.tables
        # chapters 为空，应被省略
        assert "chapters" not in result.tables


# ============================================================
#  测试：write_to_json
# ============================================================
class TestWriteToJson:
    """测试 write_to_json 方法"""

    def test_creates_valid_json_file_with_correct_structure(self):
        """创建具有正确结构的有效 JSON 文件"""
        data = BackupData(novel_id="nov_test")
        data.tables = {
            "novels": [{"id": "nov_test", "novel_id": "nov_test", "title": "Test Novel"}],
            "chapters": [
                {"id": "ch1", "novel_id": "nov_test", "number": 1},
                {"id": "ch2", "novel_id": "nov_test", "number": 2},
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "backup.json"

            exporter = DataExporter()
            byte_count = exporter.write_to_json(data, str(output_path))

            # 验证文件已创建
            assert output_path.exists()

            # 验证文件内容
            content = output_path.read_text(encoding="utf-8")
            parsed = json.loads(content)

            assert parsed["version"] == "1.0"
            assert parsed["novel_id"] == "nov_test"
            assert parsed["source_db_type"] == "sqlite"
            assert "exported_at" in parsed
            assert "tables" in parsed
            assert len(parsed["tables"]["novels"]) == 1
            assert parsed["tables"]["novels"][0]["title"] == "Test Novel"
            assert len(parsed["tables"]["chapters"]) == 2

            # 验证字节数
            assert byte_count > 0
            assert byte_count == len(content.encode("utf-8"))

    def test_exported_at_is_iso_format(self):
        """exported_at 是 ISO 格式的时间戳"""
        data = BackupData(novel_id="nov_test")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "backup.json"

            exporter = DataExporter()
            exporter.write_to_json(data, str(output_path))

            content = output_path.read_text(encoding="utf-8")
            parsed = json.loads(content)

            # ISO 格式应包含 "T"（日期时间分隔符）
            assert "T" in parsed["exported_at"]


# ============================================================
#  测试：BackupData.to_dict
# ============================================================
class TestBackupDataToDict:
    """测试 BackupData.to_dict() 方法"""

    def test_returns_expected_dict_structure(self):
        """返回预期的字典结构"""
        data = BackupData(novel_id="nov42")
        data.tables = {
            "novels": [{"id": "nov42", "novel_id": "nov42", "title": "A Novel"}],
        }

        result = data.to_dict()

        assert isinstance(result, dict)
        assert result["version"] == "1.0"
        assert result["novel_id"] == "nov42"
        assert result["source_db_type"] == "sqlite"
        assert "exported_at" in result
        assert "tables" in result
        assert result["tables"] == data.tables
        assert len(result["tables"]["novels"]) == 1

    def test_empty_tables_dict_by_default(self):
        """默认 tables 为空字典"""
        data = BackupData(novel_id="nov_empty")
        result = data.to_dict()

        assert result["tables"] == {}
