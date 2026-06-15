"""小说数据导出/导入应用服务 — 作者：Axelton

编排底层工具（DataExporter / DataImporter / ChromaDBExporter）完成
小说全部数据的 ZIP 打包与还原，包含：
  - SQLite 表数据 → data.json
  - FAISS 向量数据 → chromadb/*.json
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from domain.novel.value_objects.novel_id import NovelId
from infrastructure.ai.chromadb_vector_store import ChromaDBVectorStore
from infrastructure.persistence.backup.chromadb_exporter import ChromaDBExporter
from infrastructure.persistence.backup.data_exporter import DataExporter
from infrastructure.persistence.backup.data_importer import DataImporter
from infrastructure.persistence.database.connection import get_database

logger = logging.getLogger(__name__)


class NovelBackupService:
    """小说数据导出/导入核心服务 — 编排底层工具完成 ZIP 打包与还原"""

    def __init__(
        self,
        novel_repository,
        chromadb_persist_dir: str = "./data/chromadb",
    ):
        self._novel_repository = novel_repository
        self._chromadb_persist_dir = chromadb_persist_dir
        self._data_exporter = DataExporter()
        self._data_importer = DataImporter()
        self._chromadb_exporter = ChromaDBExporter(chromadb_persist_dir)

    # ===========================================================
    #  导出
    # ===========================================================

    def export_to_zip(self, novel_id: str) -> Tuple[bytes, str]:
        """导出指定小说的全部数据到 ZIP 字节流（小文件场景，一次性读入内存）。

        Returns:
            (zip_bytes, filename)
        Raises:
            ValueError: novel not found
        """
        novel = self._validate_novel(novel_id)
        title = getattr(novel, 'title', None) or novel_id
        filename = _sanitize_filename(title, novel_id)

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            zip_path = tmp / filename
            self._build_backup_zip(novel_id, str(zip_path))
            return zip_path.read_bytes(), filename

    def export_to_zip_path(self, novel_id: str, output_dir: str) -> Tuple[str, str]:
        """导出小说备份 ZIP 到指定目录，返回文件路径供流式传输。

        适用于大部头小说场景：ZIP 构建到磁盘后由调用方分块流式读取，
        避免将整个 ZIP 载入内存导致 OOM 或超时。

        Args:
            novel_id: 小说 ID
            output_dir: 输出目录（调用方负责生命周期管理）

        Returns:
            (zip_path, filename)
        Raises:
            ValueError: novel not found
        """
        novel = self._validate_novel(novel_id)
        title = getattr(novel, 'title', None) or novel_id
        filename = _sanitize_filename(title, novel_id)

        zip_path = Path(output_dir) / filename
        self._build_backup_zip(novel_id, str(zip_path))
        return str(zip_path), filename

    def _build_backup_zip(self, novel_id: str, zip_path: str) -> None:
        """构建 ZIP: data.json + chromadb/ 目录"""
        db = get_database()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)

            # 1. 导出 SQL 数据
            data = self._data_exporter.export_novel_data(db, novel_id)
            json_path = tmp / "data.json"
            self._data_exporter.write_to_json(data, str(json_path))

            # 2. 导出 ChromaDB 向量
            chromadb_dir = tmp / "chromadb"
            chromadb_dir.mkdir()
            self._export_chromadb_vectors(novel_id, str(chromadb_dir))

            # 3. 打包 ZIP
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(str(json_path), "data.json")
                for f in chromadb_dir.iterdir():
                    zf.write(str(f), f"chromadb/{f.name}")

    def _export_chromadb_vectors(self, novel_id: str, output_dir: str) -> bool:
        """导出该小说的所有向量 collection。

        通过列出 persist_dir 下匹配 novel_{novel_id}_ 的目录来发现 collection。
        无向量时正常返回 True（chromadb 目录可能为空）。
        """
        try:
            collections = self._list_novel_collections(novel_id)
            for coll_name in collections:
                self._chromadb_exporter.export_collection_to_json(
                    coll_name, output_dir
                )
            return len(collections) > 0
        except Exception as e:
            logger.warning("向量导出失败（非致命）: %s", e)
            return False

    def _list_novel_collections(self, novel_id: str) -> List[str]:
        """列出持久化目录中匹配 novel_{novel_id}_ 的 collection 目录"""
        persist = Path(self._chromadb_persist_dir)
        if not persist.exists():
            return []
        prefix = f"novel_{novel_id}_"
        return [
            d.name for d in persist.iterdir()
            if d.is_dir() and d.name.startswith(prefix)
        ]

    # ===========================================================
    #  导入
    # ===========================================================

    def restore_from_zip(self, zip_bytes: bytes, novel_id: str) -> Dict[str, int]:
        """从 ZIP 字节流还原数据（覆盖模式）。

        Returns:
            {"tables": 60, "total_rows": 1234, "vectors": 50}
        Raises:
            ValueError: novel not found or invalid ZIP format
        """
        self._validate_novel(novel_id)

        with tempfile.TemporaryDirectory() as tmp_dir:
            return self._restore_from_zip(zip_bytes, novel_id, Path(tmp_dir))

    def _restore_from_zip(
        self, zip_bytes: bytes, novel_id: str, tmp_path: Path
    ) -> Dict[str, int]:
        """解压并执行还原"""
        # 1. 写入 ZIP 并解压
        zip_file = tmp_path / "backup.zip"
        zip_file.write_bytes(zip_bytes)
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        with zipfile.ZipFile(str(zip_file), "r") as zf:
            zf.extractall(str(extract_dir))

        # 2. 校验 data.json
        json_path = extract_dir / "data.json"
        if not json_path.exists():
            raise ValueError("ZIP 包缺少 data.json")

        # 2.5 覆盖导入时移除 novels 表（novels 以 id 为主键无 novel_id 列，
        #     导入会导致主键冲突；novels 表由 create_novel 创建，无需从备份覆盖）
        self._strip_novels_from_json(json_path)

        # 3. 导入 SQL 数据
        db = get_database()
        stats = self._data_importer.restore_from_json(db, str(json_path), novel_id)

        # 4. 导入 ChromaDB 向量
        chromadb_dir = extract_dir / "chromadb"
        if chromadb_dir.exists() and any(chromadb_dir.iterdir()):
            vector_count = self._import_chromadb_vectors(str(chromadb_dir))
            stats["vectors"] = vector_count

        return stats

    def _import_chromadb_vectors(self, input_dir: str) -> int:
        """从 chromadb/ 目录导入所有 collection 的向量。

        通过 asyncio.run() 执行异步导入，若当前已有运行中的事件循环
        则在新线程中创建独立事件循环以避免冲突。
        """
        input_path = Path(input_dir)
        json_files = list(input_path.glob("*.json"))
        if not json_files:
            return 0

        store = ChromaDBVectorStore(persist_directory=self._chromadb_persist_dir)

        async def _import_all() -> int:
            total = 0
            for json_file in json_files:
                coll_name = json_file.stem  # 文件名去 .json 后缀即为 collection 名
                count = await self._chromadb_exporter.import_from_json(
                    store, coll_name, input_dir
                )
                total += count
            return total

        try:
            _ = asyncio.get_running_loop()
            # 已有运行中的事件循环，在新线程中执行以避免冲突
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as exc:
                return exc.submit(asyncio.run, _import_all()).result()
        except RuntimeError:
            # 当前线程无运行中的事件循环，直接用 asyncio.run()
            return asyncio.run(_import_all())

    # ===========================================================
    #  内部辅助方法
    # ===========================================================

    # ===========================================================
    #  跨实例导入（小说不存在时）
    # ===========================================================

    def restore_as_new_novel(
        self, zip_bytes: bytes, user_id: str = None
    ) -> Dict:
        """从备份 ZIP 创建新小说（跨实例导入）。

        从 ZIP 中提取小说元信息，生成新 novel_id，
        将备份数据中的 novel_id 全部重映射后导入。

        Returns:
            {"novel_id": str, "stats": {...}}
        Raises:
            ValueError: ZIP 格式无效或无 novel 数据
        """
        import json as _json
        import time as _time

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)

            # 1. 解压 ZIP
            zip_file = tmp / "backup.zip"
            zip_file.write_bytes(zip_bytes)
            extract_dir = tmp / "extracted"
            extract_dir.mkdir()

            with zipfile.ZipFile(str(zip_file), "r") as zf:
                zf.extractall(str(extract_dir))

            # 2. 读取 data.json
            json_path = extract_dir / "data.json"
            if not json_path.exists():
                raise ValueError("ZIP 包缺少 data.json")

            with open(json_path, "r", encoding="utf-8") as f:
                backup_data = _json.load(f)

            # 3. 读取小说元信息
            novel_rows = backup_data.get("tables", {}).get("novels", [])
            if not novel_rows:
                raise ValueError("备份数据中缺少 novel 记录")

            old_novel_id = backup_data.get("novel_id", "")
            new_novel_id = f"novel-{int(_time.time() * 1000)}"

            # 4. 重映射所有 novel_id → 新 ID
            self._remap_novel_id_in_backup(backup_data, old_novel_id, new_novel_id)

            # 5. 写回 data.json
            with open(json_path, "w", encoding="utf-8") as f:
                _json.dump(backup_data, f, ensure_ascii=False, indent=2)

            # 6. 导入 SQL 数据
            db = get_database()
            stats = self._data_importer.restore_from_json(
                db, str(json_path), new_novel_id
            )

            # 7. 导入 ChromaDB 向量
            chromadb_dir = extract_dir / "chromadb"
            if chromadb_dir.exists() and any(chromadb_dir.iterdir()):
                vector_count = self._import_chromadb_vectors(str(chromadb_dir))
                stats["vectors"] = vector_count

            logger.info(
                "跨实例导入完成: old_id=%s → new_id=%s, stats=%s",
                old_novel_id,
                new_novel_id,
                stats,
            )
            return {"novel_id": new_novel_id, "stats": stats}

    def _remap_novel_id_in_backup(
        self, backup_data: Dict, old_novel_id: str, new_novel_id: str
    ) -> None:
        """将备份数据中所有旧 novel_id 替换为新 ID（两阶段全局重映射）。

        阶段一：全局字符串替换 — 处理含旧 ID 的复合主键和外键
        （如 chapter-{novel_id}-chapter-1）。

        阶段二：非含 novel_id 的字符串 ID 列加前缀 — 处理全局唯一 ID
        （如 fact-001 → {new_novel_id}_fact-001），防止与原小说数据主键冲突。
        整数值跳过（INTEGER PK 由 DataImporter 自动剥离后让 SQLite 生成新 rowid）。
        """
        if not old_novel_id or old_novel_id == new_novel_id:
            return

        backup_data["novel_id"] = new_novel_id

        for table_name, rows in backup_data.get("tables", {}).items():
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                for key, value in list(row.items()):
                    if isinstance(value, str) and old_novel_id in value:
                        row[key] = value.replace(old_novel_id, new_novel_id)

        # 阶段二：对不含新 novel_id 的字符串 ID 列加前缀，保证跨实例唯一
        # 跳过整数值 — INTEGER PK 列由 DataImporter 自动剥离后让 SQLite 生成新 rowid
        for table_name, rows in backup_data.get("tables", {}).items():
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                for key, value in list(row.items()):
                    if key == "id" or key.endswith("_id") or key == "slug":
                        if isinstance(value, str) and new_novel_id not in value:
                            row[key] = f"{new_novel_id}_{value}"

    def _strip_novels_from_json(self, json_path: Path) -> None:
        """从 data.json 中移除 novels 表数据。

        覆盖导入已有小说时 novels 表已存在且以 id 为主键（无 novel_id 列），
        导入会导致主键冲突。这里原地修改 JSON 文件将其移除。
        """
        import json as _json_module
        try:
            raw = json_path.read_text(encoding="utf-8")
            data = _json_module.loads(raw)
            if "novels" in data.get("tables", {}):
                del data["tables"]["novels"]
                json_path.write_text(
                    _json_module.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                logger.debug("已从 data.json 移除 novels 表（覆盖模式）")
        except Exception as e:
            logger.debug("移除 novels 表失败（非致命）: %s", e)

    def _validate_novel(self, novel_id: str):
        """校验小说存在，返回 Novel 对象。不存在则抛出 ValueError。"""
        novel = self._novel_repository.get_by_id(NovelId(novel_id))
        if novel is None:
            raise ValueError(f"小说不存在: {novel_id}")
        return novel


def _sanitize_filename(title: str, novel_id: str) -> str:
    """生成安全的 ZIP 文件名: {title}_{date}.zip"""
    invalid = '<>:"/\\|?*'
    safe = title.strip()
    for ch in invalid:
        safe = safe.replace(ch, "_")
    safe = safe.strip().replace(" ", "_")[:80]
    # 如果 sanitize 后只剩空字符串或仅由下划线组成，回退到 novel_id
    if not safe or safe.strip("_") == "":
        safe = novel_id[:20]
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{safe}_{date_str}.zip"
