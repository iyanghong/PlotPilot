"""数据库表数据动态发现 + JSON 导出 — 作者：Axelton"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ============================================================
#  平台级全局表 — 永远不导出（不属于任何小说）
# ============================================================
_GLOBAL_TABLES = {
    "users",
    "llm_configs",
    "prompt_templates",
    "prompt_packages",
    "migrations_applied",
    "sqlite_sequence",
    "ai_invocation_sessions",
    "ai_invocation_attempts",
    "ai_invocation_variables",
    "ai_invocation_contracts",
    "ai_invocation_policies",
    "dag_definitions",
    "system_settings",
}

# ============================================================
#  间接关联表 — 没有 novel_id 列，通过 JOIN 关联
#  格式: 表名 → (SQL 模板, 参数工厂函数)
# ============================================================
_INDIRECT_TABLES: Dict[str, tuple] = {
    "assist_messages": (
        "SELECT am.* FROM {table} am "
        "JOIN assist_sessions s ON am.session_id = s.id "
        "WHERE s.novel_id = ?",
        lambda novel_id: (novel_id,),
    ),
}


@dataclass
class BackupData:
    """单部小说的完整备份数据"""

    novel_id: str
    tables: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    source_db_type: str = "sqlite"
    version: str = "1.0"
    exported_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化的字典"""
        return {
            "version": self.version,
            "novel_id": self.novel_id,
            "exported_at": self.exported_at,
            "source_db_type": self.source_db_type,
            "tables": self.tables,
        }


class DataExporter:
    """从 SQLite 中导出指定小说的所有关联表数据"""

    def export_novel_data(self, db, novel_id: str) -> BackupData:
        """发现所有含 novel_id 的表并导出其数据行，同时处理间接关联表。

        Args:
            db: DatabaseConnection 实例（具有 fetch_all 方法）
            novel_id: 小说 ID 字符串

        Returns:
            BackupData 包含所有表数据行
        """
        data = BackupData(novel_id=novel_id)

        # 1. 发现所有直接关联表（有 novel_id 列）
        direct_tables = self._discover_novel_tables(db)
        logger.info(
            "发现 %d 个直接关联表用于小说 %s: %s",
            len(direct_tables),
            novel_id,
            direct_tables,
        )

        # 2. 导出 novels 表（使用 id 列而非 novel_id 列）
        novel_rows = self._export_table_by_id(db, "novels", novel_id)
        if novel_rows:
            data.tables["novels"] = novel_rows
            logger.info("导出表 novels: %d 行 (id=%s)", len(novel_rows), novel_id)
        else:
            logger.debug("未找到 novels 记录 (id=%s)", novel_id)

        # 3. 导出直接关联表数据
        for table_name in direct_tables:
            rows = self._export_table_rows(db, table_name, novel_id)
            if rows:
                data.tables[table_name] = rows
                logger.info(
                    "导出表 %s: %d 行 (novel_id=%s)", table_name, len(rows), novel_id
                )
            else:
                logger.debug("跳过空表 %s (novel_id=%s)", table_name, novel_id)

        # 4. 导出间接关联表数据
        for table_name, (join_sql, params_fn) in _INDIRECT_TABLES.items():
            rows = self._export_indirect_table(
                db, table_name, join_sql, params_fn, novel_id
            )
            if rows:
                data.tables[table_name] = rows
                logger.info(
                    "导出间接表 %s: %d 行 (novel_id=%s)",
                    table_name,
                    len(rows),
                    novel_id,
                )
            else:
                logger.debug(
                    "跳过空间接表 %s (novel_id=%s)", table_name, novel_id
                )

        logger.info(
            "小说 %s 导出完成: %d 个表, %d 总行数",
            novel_id,
            len(data.tables),
            sum(len(rows) for rows in data.tables.values()),
        )
        return data

    def _discover_novel_tables(self, db) -> List[str]:
        """查询 sqlite_master 获取所有用户表，通过 PRAGMA 检查是否存在 novel_id 列。

        排除 _GLOBAL_TABLES 中定义的平台级全局表。

        Args:
            db: DatabaseConnection 实例

        Returns:
            包含 novel_id 列的表名列表
        """
        # 查询所有用户表（排除 sqlite_ 内部表）
        rows = db.fetch_all(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        all_tables = [row["name"] for row in rows]

        novel_tables = []
        for table_name in all_tables:
            # 跳过平台级全局表
            if table_name in _GLOBAL_TABLES:
                logger.debug("跳过全局表: %s", table_name)
                continue

            # 检查是否有 novel_id 列
            if self._has_column(db, table_name, "novel_id"):
                novel_tables.append(table_name)
            else:
                logger.debug("表 %s 无 novel_id 列，跳过", table_name)

        return novel_tables

    def _has_column(self, db, table_name: str, column_name: str) -> bool:
        """通过 PRAGMA table_info 检查表是否包含指定列。

        Args:
            db: DatabaseConnection 实例
            table_name: 表名
            column_name: 列名

        Returns:
            True 如果列存在
        """
        try:
            columns = db.fetch_all(f"PRAGMA table_info('{table_name}')")
            return any(col["name"] == column_name for col in columns)
        except Exception as e:
            logger.warning("PRAGMA table_info 失败 table=%s err=%s", table_name, e)
            return False

    def _export_table_rows(
        self, db, table_name: str, novel_id: str
    ) -> List[Dict[str, Any]]:
        """SELECT * FROM {table} WHERE novel_id = ? 并返回字典列表。

        Args:
            db: DatabaseConnection 实例
            table_name: 表名
            novel_id: 小说 ID

        Returns:
            数据行字典列表，出错时返回空列表
        """
        try:
            # 使用双引号转义表名以防 SQL 关键字冲突
            sql = f'SELECT * FROM "{table_name}" WHERE novel_id = ?'
            return db.fetch_all(sql, (novel_id,))
        except Exception as e:
            logger.warning(
                "导出表 %s 失败 (novel_id=%s): %s", table_name, novel_id, e
            )
            return []

    def _export_table_by_id(
        self, db, table_name: str, row_id: str
    ) -> List[Dict[str, Any]]:
        """SELECT * FROM {table} WHERE id = ? 并返回字典列表。

        用于导出以 id 为主键、没有 novel_id 列的表（如 novels）。
        """
        try:
            sql = f'SELECT * FROM "{table_name}" WHERE id = ?'
            return db.fetch_all(sql, (row_id,))
        except Exception as e:
            logger.warning(
                "导出表 %s 失败 (id=%s): %s", table_name, row_id, e
            )
            return []

    def _export_indirect_table(
        self,
        db,
        table_name: str,
        join_sql: str,
        params_fn,
        novel_id: str,
    ) -> List[Dict[str, Any]]:
        """执行 JOIN SQL 查询并返回结果行。

        Args:
            db: DatabaseConnection 实例
            table_name: 表名（用于日志）
            join_sql: SQL 模板字符串，包含 {table} 占位符
            params_fn: 可调用对象，接收 novel_id 返回参数元组
            novel_id: 小说 ID

        Returns:
            数据行字典列表，出错时返回空列表
        """
        try:
            sql = join_sql.format(table=table_name)
            params = params_fn(novel_id)
            return db.fetch_all(sql, params)
        except Exception as e:
            logger.warning(
                "导出间接表 %s 失败 (novel_id=%s): %s", table_name, novel_id, e
            )
            return []

    def write_to_json(self, data: BackupData, output_path: str) -> int:
        """将 BackupData 写入 JSON 文件。

        Args:
            data: BackupData 实例
            output_path: 输出文件路径

        Returns:
            写入的字节数
        """
        json_str = json.dumps(
            data.to_dict(),
            ensure_ascii=False,
            default=str,
            indent=2,
        )
        Path(output_path).write_text(json_str, encoding="utf-8")
        byte_count = len(json_str.encode("utf-8"))
        logger.info("备份数据已写入 %s (%d 字节)", output_path, byte_count)
        return byte_count
