"""JSON 数据导入 + 事务性恢复单元测试 — 作者：Axelton"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from infrastructure.persistence.backup.data_exporter import BackupData, _GLOBAL_TABLES
from infrastructure.persistence.backup.data_importer import DataImporter


# ============================================================
#  辅助函数
# ============================================================

def _make_mock_db():
    """创建一个带有 execute 和 fetch_all 的模拟 db 对象。"""
    db = MagicMock()
    return db


def _write_json_file(tmpdir: str, payload: dict) -> str:
    """将字典写入 JSON 文件并返回文件路径。"""
    filepath = str(Path(tmpdir) / "backup.json")
    Path(filepath).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return filepath


def _make_backup_payload(novel_id: str = "nov_test", tables: dict = None) -> dict:
    """构造一个标准的备份 JSON 字典。"""
    if tables is None:
        tables = {
            "novels": [
                {"id": "nov_test", "novel_id": "nov_test", "title": "Test Novel"}
            ],
            "chapters": [
                {"id": "ch1", "novel_id": "nov_test", "number": 1, "content": "Once upon a time"},
                {"id": "ch2", "novel_id": "nov_test", "number": 2, "content": "The end"},
            ],
        }
    return {
        "version": "1.0",
        "novel_id": novel_id,
        "exported_at": "2026-06-15T10:00:00Z",
        "source_db_type": "sqlite",
        "tables": tables,
    }


# ============================================================
#  测试：load_from_json
# ============================================================

class TestLoadFromJson:
    """测试 load_from_json 方法"""

    def test_loads_valid_json_and_returns_backup_data(self):
        """加载有效 JSON 并返回 BackupData 实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = _make_backup_payload()
            filepath = _write_json_file(tmpdir, payload)

            importer = DataImporter()
            result = importer.load_from_json(filepath, "nov_test")

            assert isinstance(result, BackupData)
            assert result.novel_id == "nov_test"
            assert result.version == "1.0"
            assert result.source_db_type == "sqlite"
            assert result.exported_at == "2026-06-15T10:00:00Z"
            assert "novels" in result.tables
            assert "chapters" in result.tables
            assert len(result.tables["novels"]) == 1
            assert len(result.tables["chapters"]) == 2

    def test_raises_value_error_when_novel_id_mismatches(self):
        """novel_id 不匹配时抛出 ValueError"""
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = _make_backup_payload(novel_id="nov_other")
            filepath = _write_json_file(tmpdir, payload)

            importer = DataImporter()
            with pytest.raises(ValueError, match="novel_id 不匹配"):
                importer.load_from_json(filepath, "nov_test")

    def test_defaults_missing_fields(self):
        """缺少可选字段时使用默认值"""
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = {
                "version": "1.0",
                "novel_id": "nov_minimal",
                "tables": {},
            }
            filepath = _write_json_file(tmpdir, payload)

            importer = DataImporter()
            result = importer.load_from_json(filepath, "nov_minimal")

            assert result.novel_id == "nov_minimal"
            assert result.source_db_type == "sqlite"
            assert result.version == "1.0"
            assert result.exported_at == ""
            assert result.tables == {}


# ============================================================
#  测试：_import_table
# ============================================================

class TestImportTable:
    """测试 _import_table 方法"""

    def test_performs_delete_then_insert_in_correct_order(self):
        """先执行 DELETE 再执行 INSERT，顺序正确"""
        db = _make_mock_db()
        rows = [
            {"id": "r1", "novel_id": "nov_x", "name": "Row One"},
            {"id": "r2", "novel_id": "nov_x", "name": "Row Two"},
        ]

        importer = DataImporter()
        importer._import_table(db, "test_table", rows, "nov_x")

        # 验证调用顺序：先 DELETE，然后 INSERT 两次
        call_args_list = db.execute.call_args_list
        assert len(call_args_list) == 3  # 1 DELETE + 2 INSERT

        # 第一次调用应为 DELETE
        first_call = call_args_list[0]
        assert "DELETE FROM" in first_call[0][0]
        assert first_call[0][1] == ("nov_x",)

        # 后两次调用应为 INSERT
        for i in range(1, 3):
            assert "INSERT INTO" in call_args_list[i][0][0]

    def test_skips_empty_rows_no_execute_calls(self):
        """空行列表跳过，不执行任何 SQL"""
        db = _make_mock_db()

        importer = DataImporter()
        importer._import_table(db, "test_table", [], "nov_x")

        assert db.execute.call_count == 0

    def test_skips_global_tables(self):
        """跳过 _GLOBAL_TABLES 中定义的全局表"""
        db = _make_mock_db()

        # 选一个明确的全局表 — users
        rows = [{"id": 1, "username": "admin"}]

        importer = DataImporter()
        importer._import_table(db, "users", rows, "nov_x")

        # users 在 _GLOBAL_TABLES 中，应被跳过
        assert db.execute.call_count == 0

    def test_delete_failure_is_logged_but_insert_proceeds(self):
        """DELETE 失败时记录日志但 INSERT 继续执行"""
        db = _make_mock_db()
        # DELETE 抛异常，但 INSERT 应正常执行
        db.execute.side_effect = [
            Exception("no such column: novel_id"),  # DELETE 失败
            None,  # INSERT row 1 成功
            None,  # INSERT row 2 成功
        ]
        rows = [
            {"id": "r1", "session_id": "s1", "content": "Hello"},
            {"id": "r2", "session_id": "s1", "content": "World"},
        ]

        importer = DataImporter()
        # 不应抛出异常
        importer._import_table(db, "assist_messages", rows, "nov_x")

        # INSERT 应被调用了 2 次（DELETE 失败后继续）
        insert_calls = [c for c in db.execute.call_args_list if "INSERT" in str(c)]
        assert len(insert_calls) == 2

    def test_insert_sql_uses_quoted_identifiers(self):
        """INSERT SQL 使用双引号包裹表名和列名"""
        db = _make_mock_db()
        rows = [{"id": "r1", "novel_id": "nov_x", "title": "Test"}]

        importer = DataImporter()
        importer._import_table(db, "my_table", rows, "nov_x")

        # 取 INSERT 调用（跳过 DELETE 调用）
        insert_call = db.execute.call_args_list[1]
        insert_sql = insert_call[0][0]

        assert insert_sql.startswith('INSERT INTO "my_table"')
        assert '"id"' in insert_sql
        assert '"novel_id"' in insert_sql
        assert '"title"' in insert_sql


# ============================================================
#  测试：restore_from_json
# ============================================================

class TestRestoreFromJson:
    """测试 restore_from_json 方法"""

    def test_returns_correct_stats(self):
        """返回正确的统计信息"""
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = _make_backup_payload()
            filepath = _write_json_file(tmpdir, payload)

            db = _make_mock_db()
            importer = DataImporter()
            stats = importer.restore_from_json(db, filepath, "nov_test")

            assert stats == {"tables": 2, "total_rows": 3}  # 2 表, 1+2=3 行

    def test_calls_commit_on_success(self):
        """成功时调用 COMMIT"""
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = _make_backup_payload()
            filepath = _write_json_file(tmpdir, payload)

            db = _make_mock_db()
            importer = DataImporter()
            importer.restore_from_json(db, filepath, "nov_test")

            # 检查 COMMIT 被调用
            commit_calls = [
                c for c in db.execute.call_args_list
                if c[0][0] == "COMMIT"
            ]
            assert len(commit_calls) == 1

    def test_calls_rollback_on_error_and_re_raises(self):
        """出错时调用 ROLLBACK 并重新抛出异常"""
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = _make_backup_payload()
            filepath = _write_json_file(tmpdir, payload)

            db = _make_mock_db()
            # 调用顺序: BEGIN + DELETE novels + INSERT novels(失败) + ROLLBACK
            db.execute.side_effect = [
                None,  # BEGIN TRANSACTION
                None,  # DELETE FROM novels
                RuntimeError("INSERT 失败"),  # INSERT INTO novels
                None,  # ROLLBACK
            ]

            importer = DataImporter()
            with pytest.raises(RuntimeError, match="INSERT 失败"):
                importer.restore_from_json(db, filepath, "nov_test")

            # 检查 ROLLBACK 被调用
            rollback_calls = [
                c for c in db.execute.call_args_list
                if c[0][0] == "ROLLBACK"
            ]
            assert len(rollback_calls) == 1

    def test_calls_begin_transaction_before_import(self):
        """导入前先开启事务"""
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = _make_backup_payload()
            filepath = _write_json_file(tmpdir, payload)

            db = _make_mock_db()
            importer = DataImporter()
            importer.restore_from_json(db, filepath, "nov_test")

            # 第一次调用应为 BEGIN TRANSACTION
            first_call = db.execute.call_args_list[0]
            assert first_call[0][0] == "BEGIN TRANSACTION"

    def test_empty_tables_produces_zero_stats(self):
        """空表产生零统计"""
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = _make_backup_payload(novel_id="nov_minimal", tables={})
            filepath = _write_json_file(tmpdir, payload)

            db = _make_mock_db()
            importer = DataImporter()
            stats = importer.restore_from_json(db, filepath, "nov_minimal")

            assert stats == {"tables": 0, "total_rows": 0}

    def test_skips_global_table_during_restore(self):
        """恢复过程中跳过全局表"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tables = {
                "chapters": [
                    {"id": "ch1", "novel_id": "nov_test", "number": 1},
                ],
                "users": [  # 全局表，应被跳过
                    {"id": 1, "username": "admin"},
                ],
            }
            payload = _make_backup_payload(tables=tables)
            filepath = _write_json_file(tmpdir, payload)

            db = _make_mock_db()
            importer = DataImporter()
            stats = importer.restore_from_json(db, filepath, "nov_test")

            # users 是全局表，应被跳过，因此只导入了 chapters
            assert stats["total_rows"] == 1  # 仅 chapters 的 1 行
