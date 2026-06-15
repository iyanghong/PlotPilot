"""ChromaDB 向量导出/导入工具单元测试 — 作者：Axelton"""
import json
import pytest
from pathlib import Path

from infrastructure.ai.chromadb_vector_store import (
    _SimpleFlatL2Index,
    _SimpleVectorIndexBackend,
    ChromaDBVectorStore,
)
from infrastructure.persistence.backup.chromadb_exporter import (
    BackupVectorData,
    ChromaDBExporter,
)


# ============================================================
#  辅助函数：在磁盘上创建一个 FAISS collection
# ============================================================
def _create_collection_on_disk(base_dir: Path, collection_name: str, entries: list) -> None:
    """在磁盘上创建一个 FAISS collection。

    Args:
        base_dir: 持久化根目录（如 tmp_path）
        collection_name: 集合名称
        entries: [(id_str, vector_list, payload_dict), ...] 三元组列表
    """
    coll_dir = base_dir / collection_name
    coll_dir.mkdir(parents=True, exist_ok=True)

    if not entries:
        # 空集合：创建最小文件
        index = _SimpleFlatL2Index(3)
        _SimpleVectorIndexBackend.write_index(index, str(coll_dir / "index.faiss"))
        with open(coll_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump({}, f)
        return

    dim = len(entries[0][1])
    index = _SimpleFlatL2Index(dim)
    metadata = {}
    vectors = []

    for vid, vec, payload in entries:
        vectors.append(vec)
        idx = len(vectors) - 1
        metadata[vid] = {"idx": idx, "payload": payload}

    index.add(vectors)
    _SimpleVectorIndexBackend.write_index(index, str(coll_dir / "index.faiss"))
    with open(coll_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


# ============================================================
#  测试：export_collection_from_disk
# ============================================================
class TestExportCollectionFromDisk:
    """测试从磁盘导出 collection 的向量和元数据"""

    def test_basic_export(self, tmp_path):
        """正常导出：有向量的 collection"""
        entries = [
            ("id1", [1.0, 0.0, 0.0], {"text": "hello", "chapter": 1}),
            ("id2", [0.0, 1.0, 0.0], {"text": "world", "chapter": 2}),
            ("id3", [0.0, 0.0, 1.0], {"text": "foo", "chapter": 1}),
        ]
        _create_collection_on_disk(tmp_path, "novel_abc_chunks", entries)

        exporter = ChromaDBExporter(persist_dir=str(tmp_path))
        result = exporter.export_collection_from_disk("novel_abc_chunks")

        assert result is not None
        assert result.collection_name == "novel_abc_chunks"
        assert len(result.ids) == 3
        assert result.ids == ["id1", "id2", "id3"]
        assert result.embeddings is not None
        assert len(result.embeddings) == 3
        assert result.embeddings[0] == [1.0, 0.0, 0.0]
        assert result.embeddings[1] == [0.0, 1.0, 0.0]
        assert result.embeddings[2] == [0.0, 0.0, 1.0]
        assert result.metadatas is not None
        assert result.metadatas[0] == {"text": "hello", "chapter": 1}
        assert result.metadatas[1] == {"text": "world", "chapter": 2}
        assert result.metadatas[2] == {"text": "foo", "chapter": 1}
        assert result.documents == ["hello", "world", "foo"]

    def test_documents_from_payload_document_key(self, tmp_path):
        """documents 字段优先使用 payload 中的 'document' 键"""
        entries = [
            ("id1", [1.0, 0.0], {"document": "content from document key"}),
        ]
        _create_collection_on_disk(tmp_path, "test_coll", entries)

        exporter = ChromaDBExporter(persist_dir=str(tmp_path))
        result = exporter.export_collection_from_disk("test_coll")

        assert result is not None
        assert result.documents == ["content from document key"]

    def test_documents_fallback_to_text_key(self, tmp_path):
        """documents 字段在没有 'document' 键时使用 'text' 键"""
        entries = [
            ("id1", [1.0, 0.0], {"text": "fallback text"}),
        ]
        _create_collection_on_disk(tmp_path, "test_coll", entries)

        exporter = ChromaDBExporter(persist_dir=str(tmp_path))
        result = exporter.export_collection_from_disk("test_coll")

        assert result is not None
        assert result.documents == ["fallback text"]

    def test_documents_none_when_no_text_keys(self, tmp_path):
        """documents 字段在 payload 无文本键时返回 None"""
        entries = [
            ("id1", [1.0, 0.0], {"chapter": 1, "kind": "summary"}),
        ]
        _create_collection_on_disk(tmp_path, "test_coll", entries)

        exporter = ChromaDBExporter(persist_dir=str(tmp_path))
        result = exporter.export_collection_from_disk("test_coll")

        assert result is not None
        assert result.documents is None

    def test_returns_none_when_dir_missing(self, tmp_path):
        """导出不存在的 collection 时返回 None"""
        exporter = ChromaDBExporter(persist_dir=str(tmp_path))
        result = exporter.export_collection_from_disk("nonexistent_coll")
        assert result is None

    def test_returns_none_when_empty(self, tmp_path):
        """导出 0 向量的 collection 时返回 None"""
        _create_collection_on_disk(tmp_path, "empty_coll", [])
        exporter = ChromaDBExporter(persist_dir=str(tmp_path))
        result = exporter.export_collection_from_disk("empty_coll")
        assert result is None

    def test_single_vector_collection(self, tmp_path):
        """单个向量的 collection 也能正确导出"""
        entries = [("only", [1.0, 2.0, 3.0, 4.0], {"text": "single"})]
        _create_collection_on_disk(tmp_path, "novel_xyz_triples", entries)

        exporter = ChromaDBExporter(persist_dir=str(tmp_path))
        result = exporter.export_collection_from_disk("novel_xyz_triples")

        assert result is not None
        assert len(result.ids) == 1
        assert result.ids == ["only"]
        assert result.embeddings == [[1.0, 2.0, 3.0, 4.0]]
        assert result.documents == ["single"]

    def test_correct_vector_order_matches_faiss_index(self, tmp_path):
        """验证导出顺序与 FAISS 索引顺序一致（idx 0, 1, 2...）"""
        entries = [
            ("z", [0.0, 0.0, 1.0], {"text": "z"}),
            ("a", [1.0, 0.0, 0.0], {"text": "a"}),
            ("m", [0.0, 1.0, 0.0], {"text": "m"}),
        ]
        _create_collection_on_disk(tmp_path, "test_coll", entries)

        exporter = ChromaDBExporter(persist_dir=str(tmp_path))
        result = exporter.export_collection_from_disk("test_coll")

        assert result is not None
        # 添加顺序 = 索引顺序，idx 0→z, idx 1→a, idx 2→m
        assert result.ids == ["z", "a", "m"]
        assert result.embeddings == [
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ]
        assert result.documents == ["z", "a", "m"]


# ============================================================
#  测试：export_collection_to_json
# ============================================================
class TestExportCollectionToJson:
    """测试将 collection 导出为 JSON 文件"""

    def test_creates_valid_json_file(self, tmp_path):
        """导出的 JSON 文件内容有效，可以被还原为 BackupVectorData"""
        entries = [
            ("id1", [1.0, 0.0], {"text": "hello"}),
            ("id2", [0.0, 1.0], {"text": "world"}),
        ]
        _create_collection_on_disk(tmp_path, "my_coll", entries)

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        exporter = ChromaDBExporter(persist_dir=str(tmp_path))
        result_path = exporter.export_collection_to_json("my_coll", str(output_dir))

        assert result_path is not None
        json_file = Path(result_path)
        assert json_file.exists()
        assert json_file.name == "my_coll.json"

        # 验证 JSON 内容
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["collection_name"] == "my_coll"
        assert data["ids"] == ["id1", "id2"]
        assert data["embeddings"] == [[1.0, 0.0], [0.0, 1.0]]
        assert data["documents"] == ["hello", "world"]

    def test_returns_none_for_empty_collection(self, tmp_path):
        """空 collection 导出时返回 None"""
        _create_collection_on_disk(tmp_path, "empty_coll", [])
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        exporter = ChromaDBExporter(persist_dir=str(tmp_path))
        result = exporter.export_collection_to_json("empty_coll", str(output_dir))
        assert result is None

    def test_output_dir_auto_created(self, tmp_path):
        """输出目录不存在时自动创建"""
        entries = [("id1", [1.0, 0.0], {"text": "test"})]
        _create_collection_on_disk(tmp_path, "test_coll", entries)

        output_dir = tmp_path / "auto_created"
        # 目录不存在

        exporter = ChromaDBExporter(persist_dir=str(tmp_path))
        result_path = exporter.export_collection_to_json("test_coll", str(output_dir))

        assert result_path is not None
        assert Path(result_path).exists()
        assert output_dir.exists()


# ============================================================
#  测试：import_from_json（异步）
# ============================================================
class TestImportFromJson:
    """测试从 JSON 文件导入向量到 ChromaDBVectorStore"""

    @pytest.mark.asyncio
    async def test_import_creates_collection_and_inserts_vectors(self, tmp_path):
        """从 JSON 导入后，store 中应存在对应 collection 和向量"""
        # 准备：创建 JSON 文件
        entries = [
            ("id_a", [1.0, 0.0, 0.0], {"text": "alpha", "chapter": 1}),
            ("id_b", [0.0, 1.0, 0.0], {"text": "beta", "chapter": 2}),
        ]
        _create_collection_on_disk(tmp_path, "src_coll", entries)

        exporter = ChromaDBExporter(persist_dir=str(tmp_path))
        input_dir = tmp_path / "input"
        json_path = exporter.export_collection_to_json("src_coll", str(input_dir))
        assert json_path is not None

        # 导入到新的 store
        store_dir = tmp_path / "store"
        store_dir.mkdir()
        store = ChromaDBVectorStore(persist_directory=str(store_dir))

        imported = await exporter.import_from_json(store, "src_coll", str(input_dir))
        assert imported == 2

        # 验证 collection 存在
        collections = await store.list_collections()
        assert "src_coll" in collections

        # 验证向量可检索
        results = await store.search(
            collection="src_coll",
            query_vector=[1.0, 0.0, 0.0],
            limit=2,
        )
        assert len(results) == 2
        ids = {r["id"] for r in results}
        assert ids == {"id_a", "id_b"}

    @pytest.mark.asyncio
    async def test_import_skips_missing_json_returns_zero(self, tmp_path):
        """JSON 文件不存在时返回 0"""
        store_dir = tmp_path / "store"
        store_dir.mkdir()
        store = ChromaDBVectorStore(persist_directory=str(store_dir))

        exporter = ChromaDBExporter(persist_dir=str(tmp_path))
        result = await exporter.import_from_json(store, "nonexistent", str(tmp_path))
        assert result == 0

    @pytest.mark.asyncio
    async def test_import_preserves_payload(self, tmp_path):
        """导入后 payload 完整保留"""
        entries = [
            ("id_x", [1.0, 0.0], {"text": "test", "chapter": 5, "kind": "summary"}),
        ]
        _create_collection_on_disk(tmp_path, "payload_test", entries)

        exporter = ChromaDBExporter(persist_dir=str(tmp_path))
        input_dir = tmp_path / "input"
        exporter.export_collection_to_json("payload_test", str(input_dir))

        store_dir = tmp_path / "store"
        store_dir.mkdir()
        store = ChromaDBVectorStore(persist_directory=str(store_dir))

        await exporter.import_from_json(store, "payload_test", str(input_dir))

        results = await store.search("payload_test", [1.0, 0.0], limit=1)
        assert len(results) == 1
        assert results[0]["payload"]["text"] == "test"
        assert results[0]["payload"]["chapter"] == 5
        assert results[0]["payload"]["kind"] == "summary"

    @pytest.mark.asyncio
    async def test_import_handles_empty_documents(self, tmp_path):
        """导入 documents 为 None 的数据不报错"""
        entries = [
            ("id_nodoc", [1.0, 0.0], {"chapter": 1, "kind": "bible_snippet"}),
        ]
        _create_collection_on_disk(tmp_path, "nodoc_coll", entries)

        exporter = ChromaDBExporter(persist_dir=str(tmp_path))
        input_dir = tmp_path / "input"
        exporter.export_collection_to_json("nodoc_coll", str(input_dir))

        store_dir = tmp_path / "store"
        store_dir.mkdir()
        store = ChromaDBVectorStore(persist_directory=str(store_dir))

        imported = await exporter.import_from_json(store, "nodoc_coll", str(input_dir))
        assert imported == 1

    @pytest.mark.asyncio
    async def test_import_respects_vector_dimension(self, tmp_path):
        """导入时根据第一向量的维度创建 collection"""
        entries = [
            ("id1", [1.0, 2.0, 3.0, 4.0, 5.0], {"text": "high_dim"}),
        ]
        _create_collection_on_disk(tmp_path, "high_dim_coll", entries)

        exporter = ChromaDBExporter(persist_dir=str(tmp_path))
        input_dir = tmp_path / "input"
        exporter.export_collection_to_json("high_dim_coll", str(input_dir))

        store_dir = tmp_path / "store"
        store_dir.mkdir()
        store = ChromaDBVectorStore(persist_directory=str(store_dir))

        await exporter.import_from_json(store, "high_dim_coll", str(input_dir))

        results = await store.search("high_dim_coll", [1.0, 2.0, 3.0, 4.0, 5.0], limit=1)
        assert len(results) == 1
        assert results[0]["id"] == "id1"


# ============================================================
#  测试：BackupVectorData 数据类
# ============================================================
class TestBackupVectorData:
    """BackupVectorData 数据类的基本属性测试"""

    def test_default_values(self):
        """验证默认字段值"""
        data = BackupVectorData(collection_name="test")
        assert data.collection_name == "test"
        assert data.ids == []
        assert data.embeddings is None
        assert data.metadatas is None
        assert data.documents is None

    def test_full_construction(self):
        """验证完整构造"""
        data = BackupVectorData(
            collection_name="full",
            ids=["a", "b"],
            embeddings=[[1.0], [2.0]],
            metadatas=[{"x": 1}, {"x": 2}],
            documents=["doc a", "doc b"],
        )
        assert data.ids == ["a", "b"]
        assert data.embeddings == [[1.0], [2.0]]
        assert data.documents == ["doc a", "doc b"]
