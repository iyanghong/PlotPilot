"""ChromaDB 向量导出/导入工具 — 作者：Axelton"""
from __future__ import annotations

import dataclasses
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from infrastructure.ai.chromadb_vector_store import (
    _get_vector_index_backend,
    ChromaDBVectorStore,
)

logger = logging.getLogger(__name__)


@dataclass
class BackupVectorData:
    """单 collection 的导出向量数据"""
    collection_name: str
    ids: List[str] = field(default_factory=list)
    embeddings: Optional[List[List[float]]] = None
    metadatas: Optional[List[Dict[str, Any]]] = None
    documents: Optional[List[str]] = None


class ChromaDBExporter:
    """ChromaDB(FAISS) 向量数据导出/导入

    直接操作 FAISS 索引文件 + JSON 元数据，不依赖 ChromaDB 客户端。
    """

    def __init__(self, persist_dir: str = "./data/chromadb"):
        self._persist_dir = persist_dir

    # --------------------------------------------------------
    #  导出
    # --------------------------------------------------------

    def _extract_document(self, payload: Dict[str, Any]) -> Optional[str]:
        """从 payload 中提取文档文本。

        优先查找 'document' 键，其次查找 'text' 键，
        都找不到则返回 None。
        """
        if "document" in payload:
            return payload["document"]
        if "text" in payload:
            return payload["text"]
        return None

    def export_collection_from_disk(
        self, collection_name: str
    ) -> Optional[BackupVectorData]:
        """从磁盘读取 collection 的 FAISS 索引 + 元数据并导出。

        步骤：
        1. 读取 {persist_dir}/{collection_name}/index.faiss
        2. 读取 {persist_dir}/{collection_name}/metadata.json
        3. 遍历索引中每个向量，通过 idx→id 反向映射配对元数据
        4. 返回 BackupVectorData

        Returns:
            BackupVectorData，如果集合不存在或无向量则返回 None
        """
        coll_dir = Path(self._persist_dir) / collection_name
        if not coll_dir.is_dir():
            logger.debug("导出跳过：collection 目录不存在 path=%s", coll_dir)
            return None

        index_path = coll_dir / "index.faiss"
        metadata_path = coll_dir / "metadata.json"

        if not index_path.exists() or not metadata_path.exists():
            logger.debug(
                "导出跳过：缺少索引或元数据文件 collection=%s", collection_name
            )
            return None

        # 读取索引
        index_backend = _get_vector_index_backend()
        index = index_backend.read_index(str(index_path))

        if index.ntotal == 0:
            logger.debug("导出跳过：索引为空 collection=%s", collection_name)
            return None

        # 读取元数据
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata: Dict[str, Dict[str, Any]] = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("导出失败：元数据 JSON 损坏 collection=%s err=%s", collection_name, e)
            return None

        if not metadata:
            logger.debug("导出跳过：元数据为空 collection=%s", collection_name)
            return None

        # 构建 idx → id 反向映射
        idx_to_id: Dict[int, str] = {}
        for id_str, entry in metadata.items():
            idx_to_id[int(entry["idx"])] = id_str

        # 按 FAISS 索引顺序遍历，构建导出数据
        ids: List[str] = []
        embeddings: List[List[float]] = []
        metadatas: List[Dict[str, Any]] = []
        documents: List[str] = []
        doc_count = 0

        for i in range(index.ntotal):
            # 重建向量
            vector = index.reconstruct(i)

            # 查找对应 id
            vec_id = idx_to_id.get(i)
            if vec_id is None:
                # FAISS 索引中存在但元数据中已删除的"僵尸"向量，跳过
                logger.debug(
                    "导出跳过 idx=%d：元数据中无对应 id collection=%s",
                    i, collection_name,
                )
                continue

            entry = metadata.get(vec_id)
            payload = entry.get("payload", {}) if entry else {}

            ids.append(vec_id)
            embeddings.append(vector)
            metadatas.append(payload)

            doc = self._extract_document(payload)
            if doc is not None:
                documents.append(doc)
                doc_count += 1

        if not ids:
            return None

        return BackupVectorData(
            collection_name=collection_name,
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents if doc_count > 0 else None,
        )

    def export_collection_to_json(
        self, collection_name: str, output_dir: str
    ) -> Optional[str]:
        """导出 collection 到 JSON 文件。

        Args:
            collection_name: 集合名称
            output_dir: 输出目录

        Returns:
            JSON 文件路径，空 collection 返回 None
        """
        data = self.export_collection_from_disk(collection_name)
        if data is None:
            return None

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        json_path = out_dir / f"{collection_name}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                dataclasses.asdict(data),
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.info(
            "导出完成 collection=%s ids=%d path=%s",
            collection_name,
            len(data.ids),
            json_path,
        )
        return str(json_path)

    # --------------------------------------------------------
    #  导入
    # --------------------------------------------------------

    async def import_from_json(
        self, store: ChromaDBVectorStore, collection_name: str, input_dir: str
    ) -> int:
        """从 JSON 文件导入向量到 ChromaDBVectorStore。

        步骤：
        1. 读取 {input_dir}/{collection_name}.json
        2. 通过 store.create_collection() 创建集合
        3. 通过 store.insert() 逐条插入向量
        4. 返回插入条数

        Args:
            store: ChromaDBVectorStore 实例
            collection_name: 集合名称
            input_dir: JSON 文件所在目录

        Returns:
            插入的向量条数，文件不存在时返回 0
        """
        json_path = Path(input_dir) / f"{collection_name}.json"
        if not json_path.exists():
            logger.debug("导入跳过：JSON 文件不存在 path=%s", json_path)
            return 0

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("导入失败：JSON 损坏 collection=%s err=%s", collection_name, e)
            return 0

        ids = raw.get("ids") or []
        embeddings = raw.get("embeddings") or []
        metadatas = raw.get("metadatas") or []

        if not ids or not embeddings:
            logger.debug("导入跳过：JSON 中无向量数据 collection=%s", collection_name)
            return 0

        # 根据第一向量的维度创建集合
        dim = len(embeddings[0])
        await store.create_collection(collection_name, dim)

        count = 0
        for i, vec_id in enumerate(ids):
            vector = embeddings[i]
            payload = metadatas[i] if i < len(metadatas) else {}
            await store.insert(
                collection=collection_name,
                id=vec_id,
                vector=vector,
                payload=payload,
            )
            count += 1

        logger.info(
            "导入完成 collection=%s count=%d",
            collection_name,
            count,
        )
        return count
