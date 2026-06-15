"""JSON 数据解析 + 事务性导入 — 作者：Axelton"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from infrastructure.persistence.backup.data_exporter import BackupData, _GLOBAL_TABLES

logger = logging.getLogger(__name__)


class DataImporter:
    """将备份 JSON 数据导入数据库，提供事务性保障"""

    # ============================================================
    #  公开方法
    # ============================================================

    def load_from_json(self, json_path: str, expected_novel_id: str) -> BackupData:
        """从 JSON 文件加载备份数据。

        Args:
            json_path: JSON 文件路径
            expected_novel_id: 期望的小说 ID

        Returns:
            BackupData 实例

        Raises:
            ValueError: JSON 中的 novel_id 与 expected_novel_id 不匹配
        """
        raw = Path(json_path).read_text(encoding="utf-8")
        payload: Dict[str, Any] = json.loads(raw)

        novel_id = payload.get("novel_id", "")
        if novel_id != expected_novel_id:
            raise ValueError(
                f"novel_id 不匹配: JSON 中为 '{novel_id}', 期望为 '{expected_novel_id}'"
            )

        data = BackupData(
            novel_id=novel_id,
            tables=payload.get("tables", {}),
            source_db_type=payload.get("source_db_type", "sqlite"),
            version=payload.get("version", "1.0"),
            exported_at=payload.get("exported_at", ""),
        )
        logger.info(
            "已加载备份数据: novel_id=%s, %d 个表, %d 总行数",
            novel_id,
            len(data.tables),
            sum(len(rows) for rows in data.tables.values()),
        )
        return data

    def restore_from_json(
        self, db, json_path: str, novel_id: str
    ) -> Dict[str, int]:
        """从 JSON 文件恢复数据。返回统计信息。

        流程:
        1. 通过 load_from_json 加载 JSON
        2. 开启事务
        3. 遍历每个表: DELETE WHERE novel_id = ?, 然后 INSERT 行
        4. 成功时提交，任何错误时回滚

        Args:
            db: DatabaseConnection 实例（具有 execute 方法）
            json_path: JSON 文件路径
            novel_id: 小说 ID

        Returns:
            统计字典: {'tables': N, 'total_rows': N}

        Raises:
            ValueError: novel_id 不匹配
            Exception: 导入失败时回滚并重新抛出
        """
        data = self.load_from_json(json_path, novel_id)

        try:
            self._begin_transaction(db)

            total_rows = 0
            for table_name, rows in data.tables.items():
                imported = self._import_table(db, table_name, rows, novel_id)
                total_rows += imported

            self._commit(db)
            stats = {"tables": len(data.tables), "total_rows": total_rows}
            logger.info(
                "小说 %s 恢复完成: %d 个表, %d 总行数",
                novel_id,
                stats["tables"],
                stats["total_rows"],
            )
            return stats
        except Exception:
            self._rollback(db)
            logger.exception("小说 %s 恢复失败，已回滚", novel_id)
            raise

    # ============================================================
    #  内部方法
    # ============================================================

    def _import_table(
        self,
        db,
        table_name: str,
        rows: List[Dict[str, Any]],
        novel_id: str,
    ) -> int:
        """导入单个表: 先 DELETE 现有行（按 novel_id），再 INSERT 所有行。

        - 跳过 _GLOBAL_TABLES 中的全局表（防御性检查）
        - 跳过空行列表
        - DELETE: 使用双引号包裹表名，失败时仅记录 debug 日志（间接表可能无 novel_id 列）
        - INSERT: 从 rows[0].keys() 动态构建列名和占位符

        Args:
            db: DatabaseConnection 实例
            table_name: 表名
            rows: 数据行字典列表
            novel_id: 小说 ID

        Returns:
            实际导入的行数（跳过的表返回 0）
        """
        # 防御性检查：跳过全局表
        if table_name in _GLOBAL_TABLES:
            logger.debug("跳过全局表: %s", table_name)
            return 0

        # 跳过空行列表
        if not rows:
            logger.debug("表 %s 无数据行，跳过", table_name)
            return 0

        # DELETE 现有行 — 部分表可能没有 novel_id 列（间接关联表），失败时仅记录日志
        try:
            db.execute(f'DELETE FROM "{table_name}" WHERE novel_id = ?', (novel_id,))
            logger.debug("表 %s: 已删除 novel_id=%s 的现有行", table_name, novel_id)
        except Exception as e:
            logger.debug(
                "表 %s 无法执行 DELETE (可能无 novel_id 列): %s", table_name, e
            )

        # 检测 INTEGER PK 的 id 列 — 剥离后让 SQLite 自动生成 rowid，防止跨小说主键冲突
        stripped_pk = self._detect_integer_pk_id(db, table_name)

        # 构建 INSERT SQL
        cols = list(rows[0].keys())
        if stripped_pk and "id" in cols:
            cols.remove("id")
        col_names = ", ".join(f'"{c}"' for c in cols)
        placeholders = ", ".join(["?"] * len(cols))
        insert_sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'

        for row in rows:
            values = tuple(row[col] for col in cols)
            db.execute(insert_sql, values)

        logger.info("表 %s: 已导入 %d 行", table_name, len(rows))
        return len(rows)

    def _detect_integer_pk_id(self, db, table_name: str) -> bool:
        """检测表是否以 INTEGER 类型列作为主键 id。

        SQLite 中 INTEGER PRIMARY KEY 是 rowid 的别名，插入字符串值会
        触发 datatype mismatch（STRICT 模式下）或静默转换。剥离后让
        SQLite 自动生成新 rowid，避免跨小说导入时的主键冲突。
        """
        try:
            info = db.fetch_all(f"PRAGMA table_info(\"{table_name}\")")
            for col in info:
                if col["name"] == "id" and col["pk"] > 0:
                    col_type = (col.get("type") or "").upper()
                    return "INT" in col_type
        except Exception:
            pass
        return False

    # ============================================================
    #  事务辅助方法
    # ============================================================

    def _begin_transaction(self, db) -> None:
        """开启事务"""
        db.execute("BEGIN TRANSACTION")

    def _commit(self, db) -> None:
        """提交事务"""
        db.execute("COMMIT")

    def _rollback(self, db) -> None:
        """回滚事务"""
        db.execute("ROLLBACK")
