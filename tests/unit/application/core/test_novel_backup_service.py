"""NovelBackupService 单元测试 — 作者：Axelton"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.core.services.novel_backup_service import (
    NovelBackupService,
    _sanitize_filename,
)
from domain.novel.value_objects.novel_id import NovelId
from infrastructure.persistence.backup.data_exporter import BackupData


# ============================================================
#  测试夹具
# ============================================================


def _make_novel(title: str = "测试小说"):
    """创建一个模拟的 Novel 对象"""
    return SimpleNamespace(title=title)


def _make_novel_repo(novel=None):
    """创建一个模拟的 NovelRepository"""
    repo = MagicMock()
    repo.get_by_id.return_value = novel
    return repo


def _make_backup_data(novel_id: str = "test-novel-1", num_tables: int = 3):
    """创建一个包含测试数据的 BackupData"""
    tables = {}
    for i in range(num_tables):
        tables[f"table_{i}"] = [
            {"id": j, "novel_id": novel_id, "name": f"row_{j}"} for j in range(2)
        ]
    return BackupData(novel_id=novel_id, tables=tables)


# ============================================================
#  _validate_novel 测试
# ============================================================


class TestValidateNovel:
    """测试 _validate_novel 方法"""

    def test_raises_value_error_when_novel_not_found(self):
        """小说不存在时抛出 ValueError"""
        repo = _make_novel_repo(novel=None)
        service = NovelBackupService(novel_repository=repo)

        with pytest.raises(ValueError, match="小说不存在: missing-novel"):
            service._validate_novel("missing-novel")

    def test_returns_novel_when_found(self):
        """小说存在时返回 Novel 对象"""
        novel = _make_novel()
        repo = _make_novel_repo(novel=novel)
        service = NovelBackupService(novel_repository=repo)

        result = service._validate_novel("test-novel-1")

        assert result is novel
        repo.get_by_id.assert_called_once_with(NovelId("test-novel-1"))


# ============================================================
#  _list_novel_collections 测试
# ============================================================


class TestListNovelCollections:
    """测试 _list_novel_collections 方法"""

    def test_filters_directories_by_prefix(self, tmp_path):
        """按 novel_{id}_ 前缀过滤目录"""
        novel_id = "abc-123"
        (tmp_path / f"novel_{novel_id}_chunks").mkdir()
        (tmp_path / f"novel_{novel_id}_triples").mkdir()
        (tmp_path / "novel_other-id_chunks").mkdir()
        (tmp_path / "some_random_file.txt").write_text("test")
        (tmp_path / "not_a_novel_dir").mkdir()

        service = NovelBackupService(
            novel_repository=_make_novel_repo(),
            chromadb_persist_dir=str(tmp_path),
        )

        result = service._list_novel_collections(novel_id)

        assert sorted(result) == sorted([
            f"novel_{novel_id}_chunks",
            f"novel_{novel_id}_triples",
        ])

    def test_returns_empty_list_when_persist_dir_not_exists(self):
        """persist 目录不存在时返回空列表"""
        service = NovelBackupService(
            novel_repository=_make_novel_repo(),
            chromadb_persist_dir="/nonexistent/path",
        )

        result = service._list_novel_collections("some-id")

        assert result == []

    def test_returns_empty_list_when_no_matching_collections(self, tmp_path):
        """无匹配的 collection 时返回空列表"""
        (tmp_path / "novel_other-id_chunks").mkdir()
        (tmp_path / "some_file.txt").write_text("test")

        service = NovelBackupService(
            novel_repository=_make_novel_repo(),
            chromadb_persist_dir=str(tmp_path),
        )

        result = service._list_novel_collections("my-novel")

        assert result == []


# ============================================================
#  export_to_zip 测试
# ============================================================


class TestExportToZip:
    """测试 export_to_zip 方法"""

    def test_returns_bytes_and_filename(self):
        """导出成功时返回 (bytes, filename) 元组"""
        novel = _make_novel(title="星辰往事")
        repo = _make_novel_repo(novel=novel)
        service = NovelBackupService(novel_repository=repo)

        # Mock _build_backup_zip，令其实际创建 zip 文件
        def _mock_build(novel_id, zip_path):
            Path(zip_path).write_bytes(b"fake-zip-content")

        with patch.object(service, "_build_backup_zip", side_effect=_mock_build):
            result = service.export_to_zip("test-novel-1")

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bytes)
        assert isinstance(result[1], str)

        zip_bytes, filename = result
        assert filename.endswith(".zip")
        assert "星辰往事" in filename
        assert zip_bytes == b"fake-zip-content"

    def test_raises_value_error_when_novel_not_found(self):
        """小说不存在时抛出 ValueError"""
        repo = _make_novel_repo(novel=None)
        service = NovelBackupService(novel_repository=repo)

        with pytest.raises(ValueError, match="小说不存在: ghost-novel"):
            service.export_to_zip("ghost-novel")

    def test_filename_falls_back_to_novel_id_when_no_title(self):
        """小说无 title 属性时使用 novel_id 作为文件名"""
        novel = SimpleNamespace()  # 无 title 属性
        repo = _make_novel_repo(novel=novel)
        service = NovelBackupService(novel_repository=repo)

        def _mock_build(novel_id, zip_path):
            Path(zip_path).write_bytes(b"content")

        with patch.object(service, "_build_backup_zip", side_effect=_mock_build):
            _, filename = service.export_to_zip("no-title-novel")

        assert "no-title-novel" in filename


# ============================================================
#  _build_backup_zip 测试
# ============================================================


class TestBuildBackupZip:
    """测试 _build_backup_zip 方法"""

    def test_creates_valid_zip_with_entries(self, tmp_path):
        """创建的 ZIP 包含 data.json 条目"""
        novel = _make_novel()
        repo = _make_novel_repo(novel=novel)
        service = NovelBackupService(novel_repository=repo)
        backup_data = _make_backup_data()

        zip_path = tmp_path / "test_backup.zip"

        with patch(
            "application.core.services.novel_backup_service.get_database"
        ) as mock_db:
            with patch.object(
                service._data_exporter, "export_novel_data", return_value=backup_data
            ):
                # write_to_json 必须实际写入文件，因为 zipfile 会读取磁盘文件
                def _real_write(data, output_path):
                    Path(output_path).write_text(
                        json.dumps(data.to_dict(), ensure_ascii=False, default=str, indent=2),
                        encoding="utf-8",
                    )

                with patch.object(
                    service._data_exporter, "write_to_json", side_effect=_real_write
                ):
                    with patch.object(
                        service, "_export_chromadb_vectors"
                    ) as mock_vectors:
                        service._build_backup_zip("test-novel-1", str(zip_path))

        # 验证 ZIP 存在且有效
        assert zip_path.exists()
        with zipfile.ZipFile(str(zip_path), "r") as zf:
            names = zf.namelist()
            assert "data.json" in names

        mock_db.assert_called_once()
        mock_vectors.assert_called_once()

    def test_includes_chromadb_entries_when_vectors_exist(self, tmp_path):
        """存在向量时 ZIP 包含 chromadb/ 条目"""
        novel = _make_novel()
        repo = _make_novel_repo(novel=novel)
        service = NovelBackupService(novel_repository=repo)
        backup_data = _make_backup_data()

        zip_path = tmp_path / "test_backup_vectors.zip"

        with patch(
            "application.core.services.novel_backup_service.get_database"
        ):
            with patch.object(
                service._data_exporter, "export_novel_data", return_value=backup_data
            ):
                def _real_write(data, output_path):
                    Path(output_path).write_text(
                        json.dumps(data.to_dict(), ensure_ascii=False, default=str, indent=2),
                        encoding="utf-8",
                    )

                with patch.object(
                    service._data_exporter, "write_to_json", side_effect=_real_write
                ):
                    # 模拟 _export_chromadb_vectors 创建文件
                    def _create_vectors(novel_id, output_dir):
                        out = Path(output_dir)
                        (out / "novel_test-novel-1_chunks.json").write_text('{"ids": ["v1"]}')
                        (out / "novel_test-novel-1_triples.json").write_text('{"ids": ["v2"]}')
                        return True

                    with patch.object(
                        service, "_export_chromadb_vectors", side_effect=_create_vectors
                    ):
                        service._build_backup_zip("test-novel-1", str(zip_path))

        with zipfile.ZipFile(str(zip_path), "r") as zf:
            names = zf.namelist()
            assert "data.json" in names
            assert "chromadb/novel_test-novel-1_chunks.json" in names
            assert "chromadb/novel_test-novel-1_triples.json" in names


# ============================================================
#  _export_chromadb_vectors 测试
# ============================================================


class TestExportChromaDBVectors:
    """测试 _export_chromadb_vectors 方法"""

    def test_exports_all_novel_collections(self, tmp_path):
        """导出所有匹配的 collection"""
        chroma_dir = tmp_path / "chromadb"
        chroma_dir.mkdir()
        (chroma_dir / "novel_test-novel-1_chunks").mkdir()
        (chroma_dir / "novel_test-novel-1_triples").mkdir()

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        repo = _make_novel_repo()
        service = NovelBackupService(
            novel_repository=repo,
            chromadb_persist_dir=str(chroma_dir),
        )

        with patch.object(
            service._chromadb_exporter, "export_collection_to_json"
        ) as mock_export:
            mock_export.return_value = "/fake/path.json"
            result = service._export_chromadb_vectors("test-novel-1", str(output_dir))

        assert result is True
        assert mock_export.call_count == 2

    def test_returns_false_on_exception(self, tmp_path):
        """向量导出异常时返回 False（非致命）"""
        repo = _make_novel_repo()
        service = NovelBackupService(
            novel_repository=repo,
            chromadb_persist_dir=str(tmp_path),
        )

        # list_novel_collections 返回有效 collection 但导出时抛异常
        with patch.object(
            service, "_list_novel_collections", return_value=["novel_x_chunks"]
        ):
            with patch.object(
                service._chromadb_exporter,
                "export_collection_to_json",
                side_effect=RuntimeError("磁盘已满"),
            ):
                result = service._export_chromadb_vectors("test-novel-1", str(tmp_path))

        assert result is False


# ============================================================
#  restore_from_zip 测试
# ============================================================


class TestRestoreFromZip:
    """测试 restore_from_zip 方法"""

    def test_returns_correct_stats_after_import(self):
        """恢复成功后返回统计信息"""
        novel = _make_novel()
        repo = _make_novel_repo(novel=novel)
        service = NovelBackupService(novel_repository=repo)

        backup_data = _make_backup_data()
        real_data_json = json.dumps(
            backup_data.to_dict(), ensure_ascii=False, default=str, indent=2
        )

        zip_bytes_io = io.BytesIO()
        with zipfile.ZipFile(zip_bytes_io, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("data.json", real_data_json)

        with patch(
            "application.core.services.novel_backup_service.get_database"
        ):
            with patch.object(
                service._data_importer,
                "restore_from_json",
                return_value={"tables": 3, "total_rows": 6},
            ) as mock_restore:
                with patch.object(
                    service, "_import_chromadb_vectors", return_value=0
                ) as mock_vectors:
                    stats = service.restore_from_zip(
                        zip_bytes_io.getvalue(), "test-novel-1"
                    )

        assert stats["tables"] == 3
        assert stats["total_rows"] == 6
        mock_restore.assert_called_once()
        # 无 chromadb 目录，不调用向量导入
        mock_vectors.assert_not_called()

    def test_imports_vectors_when_chromadb_dir_present(self):
        """ZIP 包含 chromadb/ 目录时也恢复向量"""
        novel = _make_novel()
        repo = _make_novel_repo(novel=novel)
        service = NovelBackupService(novel_repository=repo)

        backup_data = _make_backup_data()
        real_data_json = json.dumps(
            backup_data.to_dict(), ensure_ascii=False, default=str, indent=2
        )

        zip_bytes_io = io.BytesIO()
        with zipfile.ZipFile(zip_bytes_io, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("data.json", real_data_json)
            zf.writestr(
                "chromadb/novel_test-novel-1_chunks.json",
                '{"ids": ["v1", "v2"]}',
            )

        with patch(
            "application.core.services.novel_backup_service.get_database"
        ):
            with patch.object(
                service._data_importer,
                "restore_from_json",
                return_value={"tables": 3, "total_rows": 6},
            ):
                with patch.object(
                    service, "_import_chromadb_vectors", return_value=2
                ) as mock_vectors:
                    stats = service.restore_from_zip(
                        zip_bytes_io.getvalue(), "test-novel-1"
                    )

        assert stats["vectors"] == 2
        mock_vectors.assert_called_once()

    def test_raises_value_error_when_data_json_missing(self):
        """ZIP 缺少 data.json 时抛出 ValueError"""
        novel = _make_novel()
        repo = _make_novel_repo(novel=novel)
        service = NovelBackupService(novel_repository=repo)

        zip_bytes_io = io.BytesIO()
        with zipfile.ZipFile(zip_bytes_io, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("chromadb/something.json", "{}")

        with patch(
            "application.core.services.novel_backup_service.get_database"
        ):
            with pytest.raises(ValueError, match="ZIP 包缺少 data.json"):
                service.restore_from_zip(zip_bytes_io.getvalue(), "test-novel-1")

    def test_raises_value_error_when_novel_not_found(self):
        """小说不存在时抛出 ValueError"""
        repo = _make_novel_repo(novel=None)
        service = NovelBackupService(novel_repository=repo)

        with pytest.raises(ValueError, match="小说不存在: ghost-novel"):
            service.restore_from_zip(b"fake-zip-content", "ghost-novel")


# ============================================================
#  _import_chromadb_vectors 测试
# ============================================================


class TestImportChromaDBVectors:
    """测试 _import_chromadb_vectors 方法"""

    def test_returns_zero_when_no_json_files(self, tmp_path):
        """无 JSON 文件时返回 0"""
        repo = _make_novel_repo()
        service = NovelBackupService(novel_repository=repo)

        empty_dir = tmp_path / "empty_chromadb"
        empty_dir.mkdir()

        result = service._import_chromadb_vectors(str(empty_dir))

        assert result == 0

    def test_imports_all_json_files(self, tmp_path):
        """导入所有 JSON 文件并返回总数"""
        repo = _make_novel_repo()
        service = NovelBackupService(novel_repository=repo)

        # 创建测试 JSON 文件
        input_dir = tmp_path / "chromadb"
        input_dir.mkdir()
        (input_dir / "novel_x_chunks.json").write_text('{"ids": ["v1", "v2"]}')
        (input_dir / "novel_x_triples.json").write_text('{"ids": ["v3"]}')

        mock_store = MagicMock()
        with patch(
            "application.core.services.novel_backup_service.ChromaDBVectorStore",
            return_value=mock_store,
        ):
            with patch.object(
                service._chromadb_exporter, "import_from_json", new_callable=AsyncMock
            ) as mock_import:
                mock_import.side_effect = [2, 1]  # 2 chunks, 1 triple
                result = service._import_chromadb_vectors(str(input_dir))

        assert result == 3
        assert mock_import.call_count == 2


# ============================================================
#  _sanitize_filename 测试
# ============================================================


class TestSanitizeFilename:
    """测试 _sanitize_filename 函数"""

    def test_normal_title(self):
        """正常标题生成正确的文件名"""
        result = _sanitize_filename("星辰往事", "abc-123")
        assert result.startswith("星辰往事_")
        assert result.endswith(".zip")

    def test_special_characters_replaced(self):
        """特殊字符被替换为下划线"""
        result = _sanitize_filename('星<辰>:"往/事\\|?*记', "test-id")
        assert "<" not in result
        assert '>' not in result
        assert ':' not in result
        assert '"' not in result
        assert '/' not in result
        assert '\\' not in result
        assert '|' not in result
        assert '?' not in result
        assert '*' not in result
        # 星<辰>:"往/事\|?*记 → 星_辰___往_事____记（事、记间 4 个下划线）
        assert result.startswith("星_辰___往_事____记_")

    def test_spaces_replaced_with_underscores(self):
        """空格被替换为下划线，连续空格转为连续下划线"""
        result = _sanitize_filename("  My Novel  Story  ", "nid")
        assert " " not in result
        # "  My Novel  Story  ".strip() → "My Novel  Story"
        # replace(" ", "_") → "My_Novel__Story"
        assert result.startswith("My_Novel__Story_")

    def test_truncated_when_too_long(self):
        """标题过长时截断为 80 字符"""
        long_title = "A" * 200
        result = _sanitize_filename(long_title, "nid")
        name_part = result[:result.rindex("_")]
        assert len(name_part) <= 80

    def test_fallback_when_title_empty_after_sanitize(self):
        """标题 sanitize 后仅剩下划线时回退到 novel_id"""
        result = _sanitize_filename('<>:"/\\|?*', "my-novel-id-12345")
        assert result.startswith("my-novel-id-12345_")

    def test_date_format_in_filename(self):
        """文件名包含日期 YYYYMMDD 格式"""
        result = _sanitize_filename("Test", "nid")
        parts = result.replace(".zip", "").split("_")
        date_part = parts[-1]
        assert len(date_part) == 8
        assert date_part.isdigit()


# ============================================================
#  _strip_novels_from_json 测试
# ============================================================


class TestStripNovelsFromJson:
    """测试 _strip_novels_from_json 移出 novels 表方法"""

    def test_removes_novels_from_json(self, tmp_path):
        """data.json 包含 novels 表时将其移除"""
        repo = _make_novel_repo()
        service = NovelBackupService(novel_repository=repo)

        json_path = tmp_path / "data.json"
        data = {
            "version": "1.0",
            "novel_id": "novel-1",
            "tables": {
                "novels": [{"id": "novel-1", "title": "测试"}],
                "chapters": [{"id": 1, "novel_id": "novel-1", "title": "Ch1"}],
                "story_nodes": [{"id": 2, "novel_id": "novel-1", "type": "scene"}],
            },
        }
        json_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        service._strip_novels_from_json(json_path)

        reloaded = json.loads(json_path.read_text(encoding="utf-8"))
        assert "novels" not in reloaded["tables"]
        assert "chapters" in reloaded["tables"]
        assert "story_nodes" in reloaded["tables"]

    def test_noop_when_no_novels_table(self, tmp_path):
        """data.json 中无 novels 表时不做任何修改"""
        repo = _make_novel_repo()
        service = NovelBackupService(novel_repository=repo)

        json_path = tmp_path / "data.json"
        data = {
            "version": "1.0",
            "novel_id": "novel-1",
            "tables": {
                "chapters": [{"id": 1, "novel_id": "novel-1", "title": "Ch1"}],
            },
        }
        original = json.dumps(data, ensure_ascii=False, indent=2)
        json_path.write_text(original, encoding="utf-8")

        service._strip_novels_from_json(json_path)

        reloaded = json.loads(json_path.read_text(encoding="utf-8"))
        assert "chapters" in reloaded["tables"]
        assert len(reloaded["tables"]) == 1

    def test_handles_malformed_json_gracefully(self, tmp_path):
        """JSON 格式错误时不抛异常（非致命）"""
        repo = _make_novel_repo()
        service = NovelBackupService(novel_repository=repo)

        json_path = tmp_path / "data.json"
        json_path.write_text("{invalid json!!!", encoding="utf-8")

        # 不应抛出异常
        service._strip_novels_from_json(json_path)


# ============================================================
#  _remap_novel_id_in_backup 测试
# ============================================================


class TestRemapNovelIdInBackup:
    """测试 _remap_novel_id_in_backup 全局字符串重映射方法"""

    def test_remaps_top_level_novel_id(self):
        """顶层 novel_id 被替换为新 ID"""
        repo = _make_novel_repo()
        service = NovelBackupService(novel_repository=repo)

        backup = {
            "version": "1.0",
            "novel_id": "old-novel-1",
            "tables": {"chapters": []},
        }
        service._remap_novel_id_in_backup(backup, "old-novel-1", "new-novel-2")

        assert backup["novel_id"] == "new-novel-2"

    def test_remaps_novel_id_in_table_rows(self):
        """表中每行的 novel_id 列被替换"""
        repo = _make_novel_repo()
        service = NovelBackupService(novel_repository=repo)

        backup = {
            "version": "1.0",
            "novel_id": "old-1",
            "tables": {
                "chapters": [
                    {"id": 1, "novel_id": "old-1", "title": "Ch1"},
                    {"id": 2, "novel_id": "old-1", "title": "Ch2"},
                ],
                "characters": [
                    {"id": 10, "novel_id": "old-1", "name": "Hero"},
                ],
            },
        }
        service._remap_novel_id_in_backup(backup, "old-1", "new-2")

        for row in backup["tables"]["chapters"]:
            assert row["novel_id"] == "new-2"
        for row in backup["tables"]["characters"]:
            assert row["novel_id"] == "new-2"

    def test_remaps_composite_ids_containing_old_novel_id(self):
        """复合 ID（如 chapter-{novel_id}-chapter-1）中嵌入的旧 ID 也被替换"""
        repo = _make_novel_repo()
        service = NovelBackupService(novel_repository=repo)

        backup = {
            "version": "1.0",
            "novel_id": "old-1",
            "tables": {
                "chapters": [
                    {
                        "id": "chapter-old-1-chapter-1",
                        "novel_id": "old-1",
                        "title": "Ch1",
                        "outline": "下一章引子来源于 chapter-old-1-chapter-1 的伏笔",
                    },
                ],
                "story_nodes": [
                    {
                        "id": "node-old-1-node-1",
                        "novel_id": "old-1",
                        "chapter_id": "chapter-old-1-chapter-1",
                        "type": "scene",
                    },
                ],
            },
        }
        service._remap_novel_id_in_backup(backup, "old-1", "new-2")

        ch = backup["tables"]["chapters"][0]
        assert ch["id"] == "chapter-new-2-chapter-1"
        assert ch["novel_id"] == "new-2"
        assert ch["title"] == "Ch1"  # 不含旧 ID，不变
        assert "old-1" not in ch["outline"]  # prose 中的引用也被替换

        sn = backup["tables"]["story_nodes"][0]
        assert sn["id"] == "node-new-2-node-1"
        assert sn["chapter_id"] == "chapter-new-2-chapter-1"

    def test_remaps_novels_table_id_and_slug(self):
        """novels 表的 id 和 slug 也被全局替换"""
        repo = _make_novel_repo()
        service = NovelBackupService(novel_repository=repo)

        backup = {
            "version": "1.0",
            "novel_id": "old-1",
            "tables": {
                "novels": [
                    {
                        "id": "old-1",
                        "slug": "old-1",
                        "title": "测试小说",
                        "novel_id": None,
                    },
                ],
            },
        }
        service._remap_novel_id_in_backup(backup, "old-1", "new-2")

        novel_row = backup["tables"]["novels"][0]
        assert novel_row["id"] == "new-2"
        assert novel_row["slug"] == "new-2"

    def test_noop_when_old_equals_new(self):
        """旧 ID 与新 ID 相同时不做任何修改"""
        repo = _make_novel_repo()
        service = NovelBackupService(novel_repository=repo)

        backup = {
            "version": "1.0",
            "novel_id": "same-id",
            "tables": {
                "chapters": [
                    {"id": 1, "novel_id": "same-id", "title": "Ch1"},
                ],
            },
        }
        service._remap_novel_id_in_backup(backup, "same-id", "same-id")

        # 不应有任何变化
        assert backup["novel_id"] == "same-id"
        assert backup["tables"]["chapters"][0]["novel_id"] == "same-id"

    def test_does_not_change_non_string_values(self):
        """整数 ID 列会被加前缀（转为字符串），但非 ID 列不受影响"""
        repo = _make_novel_repo()
        service = NovelBackupService(novel_repository=repo)

        backup = {
            "version": "1.0",
            "novel_id": "old-1",
            "tables": {
                "chapters": [
                    {
                        "id": 5,
                        "chapter_number": 1,
                        "novel_id": "old-1",
                        "title": "Ch1",
                    },
                ],
                "characters": [
                    {
                        "id": "char-99",
                        "novel_id": "old-1",
                        "name": "Hero",
                    },
                ],
            },
        }
        service._remap_novel_id_in_backup(backup, "old-1", "new-2")

        # 整数主键保持不变（由 DataImporter 剥离后让 SQLite 自动生成 rowid）
        assert backup["tables"]["chapters"][0]["id"] == 5
        # 非 ID 列不受影响（整数 chapter_number 不是 id 或 _id 结尾）
        assert backup["tables"]["chapters"][0]["chapter_number"] == 1
        # 字符串 ID 不含 novel_id 也被加前缀
        assert backup["tables"]["characters"][0]["id"] == "new-2_char-99"
        assert backup["tables"]["characters"][0]["novel_id"] == "new-2"

    def test_handles_rows_without_novel_id(self):
        """没有 novel_id 列的表，ID 列仍然会被加前缀防止冲突"""
        repo = _make_novel_repo()
        service = NovelBackupService(novel_repository=repo)

        backup = {
            "version": "1.0",
            "novel_id": "old-1",
            "tables": {
                "assist_messages": [
                    {"id": 1, "role": "user", "content": "hello"},
                    {"id": 2, "role": "assistant", "content": "hi"},
                ],
            },
        }
        service._remap_novel_id_in_backup(backup, "old-1", "new-2")

        # 整数 ID 保持不变（由 DataImporter 剥离后让 SQLite 自动生成新 rowid）
        assert backup["tables"]["assist_messages"][0]["id"] == 1
        assert backup["tables"]["assist_messages"][1]["id"] == 2
        assert backup["tables"]["assist_messages"][0]["content"] == "hello"

    def test_prefixes_global_ids_not_containing_novel_id(self):
        """不含 novel_id 的全局 ID（如 fact-001、整数主键）被加前缀以跨实例唯一化"""
        repo = _make_novel_repo()
        service = NovelBackupService(novel_repository=repo)

        backup = {
            "version": "1.0",
            "novel_id": "old-1",
            "tables": {
                "triples": [
                    {"id": "fact-001", "novel_id": "old-1", "subject": "玄清"},
                    {"id": "fact-002", "novel_id": "old-1", "subject": "叶无道"},
                ],
                "triple_provenance": [
                    {"id": "prov-001", "triple_id": "fact-001", "novel_id": "old-1", "rule_id": "rule-xyz"},
                ],
                "ai_trace_spans": [
                    {"id": 1, "trace_id": "t-1", "span_id": "span-100", "parent_span_id": None, "novel_id": "old-1"},
                    {"id": 2, "trace_id": "t-1", "span_id": "span-101", "parent_span_id": "span-100", "novel_id": "old-1"},
                ],
            },
        }
        service._remap_novel_id_in_backup(backup, "old-1", "new-2")

        # 字符串 ID 被加前缀
        assert backup["tables"]["triples"][0]["id"] == "new-2_fact-001"
        assert backup["tables"]["triples"][1]["id"] == "new-2_fact-002"

        # FK 引用同步更新
        prov = backup["tables"]["triple_provenance"][0]
        assert prov["triple_id"] == "new-2_fact-001"
        assert prov["rule_id"] == "new-2_rule-xyz"

        # 整数 ID 保持不变（由 DataImporter 剥离后让 SQLite 自动生成新 rowid）
        spans = backup["tables"]["ai_trace_spans"]
        assert spans[0]["id"] == 1
        assert spans[0]["span_id"] == "new-2_span-100"
        assert spans[0]["novel_id"] == "new-2"
        assert spans[1]["id"] == 2
        assert spans[1]["span_id"] == "new-2_span-101"
        assert spans[1]["parent_span_id"] == "new-2_span-100"  # FK 同步更新
        assert spans[1]["novel_id"] == "new-2"

    def test_does_not_prefix_values_without_id_suffix(self):
        """非 ID 列（不以 _id 结尾）的普通字符串不加前缀"""
        repo = _make_novel_repo()
        service = NovelBackupService(novel_repository=repo)

        backup = {
            "version": "1.0",
            "novel_id": "old-1",
            "tables": {
                "triples": [
                    {"id": "fact-001", "novel_id": "old-1", "subject": "玄清", "object": "阴阳街"},
                ],
            },
        }
        service._remap_novel_id_in_backup(backup, "old-1", "new-2")

        row = backup["tables"]["triples"][0]
        assert row["id"] == "new-2_fact-001"      # ID 列加了前缀
        assert row["novel_id"] == "new-2"          # novel_id 在第一阶段替换
        assert row["subject"] == "玄清"             # 普通字符串不变
        assert row["object"] == "阴阳街"            # 普通字符串不变


# ============================================================
#  restore_as_new_novel 测试
# ============================================================


class TestRestoreAsNewNovel:
    """测试 restore_as_new_novel 跨实例导入方法"""

    def test_creates_novel_and_returns_new_id(self):
        """从备份 ZIP 创建新小说，返回新 novel_id 和统计"""
        repo = _make_novel_repo()
        service = NovelBackupService(novel_repository=repo)

        backup_data = _make_backup_data("old-novel-1")
        # 确保 novels 表有数据
        backup_data.tables["novels"] = [
            {
                "id": "old-novel-1",
                "slug": "old-novel-1",
                "title": "测试小说",
                "author": "测试作者",
                "target_chapters": 100,
                "premise": "测试梗概",
                "generation_prefs_json": '{"locked_genre":"奇幻"}',
            }
        ]
        data_json = json.dumps(
            backup_data.to_dict(), ensure_ascii=False, default=str, indent=2
        )

        zip_bytes_io = io.BytesIO()
        with zipfile.ZipFile(zip_bytes_io, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("data.json", data_json)

        with patch(
            "application.core.services.novel_backup_service.get_database"
        ):
            with patch.object(
                service._data_importer,
                "restore_from_json",
                return_value={"tables": 3, "total_rows": 6},
            ) as mock_restore:
                with patch.object(
                    service, "_import_chromadb_vectors", return_value=0
                ):
                    result = service.restore_as_new_novel(
                        zip_bytes_io.getvalue()
                    )

        assert "novel_id" in result
        assert result["novel_id"].startswith("novel-")
        assert result["stats"]["tables"] == 3
        # 验证调用的是重映射后的 novel_id
        mock_restore.assert_called_once()
        called_novel_id = mock_restore.call_args[0][2]
        assert called_novel_id == result["novel_id"]

    def test_raises_when_data_json_missing(self):
        """ZIP 中缺少 data.json 时抛出 ValueError"""
        repo = _make_novel_repo()
        service = NovelBackupService(novel_repository=repo)

        zip_bytes_io = io.BytesIO()
        with zipfile.ZipFile(zip_bytes_io, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("other.txt", "not data.json")

        with pytest.raises(ValueError, match="缺少 data.json"):
            service.restore_as_new_novel(zip_bytes_io.getvalue())

    def test_raises_when_no_novel_in_backup(self):
        """备份数据中无 novel 记录时抛出 ValueError"""
        repo = _make_novel_repo()
        service = NovelBackupService(novel_repository=repo)

        backup_data = _make_backup_data("old-1")
        # 不添加 novels 表
        data_json = json.dumps(
            backup_data.to_dict(), ensure_ascii=False, default=str, indent=2
        )

        zip_bytes_io = io.BytesIO()
        with zipfile.ZipFile(zip_bytes_io, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("data.json", data_json)

        with pytest.raises(ValueError, match="缺少 novel 记录"):
            service.restore_as_new_novel(zip_bytes_io.getvalue())

    def test_imports_vectors_when_present(self):
        """ZIP 包含 chromadb/ 目录时导入向量"""
        repo = _make_novel_repo()
        service = NovelBackupService(novel_repository=repo)

        backup_data = _make_backup_data("old-1")
        backup_data.tables["novels"] = [
            {
                "id": "old-1",
                "slug": "old-1",
                "title": "测试",
                "author": "作者",
                "target_chapters": 50,
                "premise": "",
                "generation_prefs_json": "{}",
            }
        ]
        data_json = json.dumps(
            backup_data.to_dict(), ensure_ascii=False, default=str, indent=2
        )

        zip_bytes_io = io.BytesIO()
        with zipfile.ZipFile(zip_bytes_io, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("data.json", data_json)
            zf.writestr("chromadb/novel_old-1_chunks.json", '{"ids": ["v1"]}')

        with patch(
            "application.core.services.novel_backup_service.get_database"
        ):
            with patch.object(
                service._data_importer,
                "restore_from_json",
                return_value={"tables": 2, "total_rows": 2},
            ):
                with patch.object(
                    service, "_import_chromadb_vectors", return_value=1
                ) as mock_vectors:
                    result = service.restore_as_new_novel(
                        zip_bytes_io.getvalue()
                    )

        assert result["stats"]["vectors"] == 1
        mock_vectors.assert_called_once()
