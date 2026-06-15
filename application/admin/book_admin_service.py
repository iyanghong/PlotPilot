"""书籍管理应用服务 — 作者：Axelton"""
from __future__ import annotations
import logging
from typing import Any, Dict

from domain.novel.value_objects.novel_id import NovelId
from domain.novel.repositories.novel_repository import NovelRepository
from infrastructure.persistence.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class BookAdminService:
    """书籍管理编排 — 组合 NovelRepository 和 DatabaseConnection 完成聚合查询"""

    def __init__(self, novel_repository: NovelRepository, db: DatabaseConnection):
        self._novel_repo = novel_repository
        self._db = db

    def list_books(
        self, page: int = 1, page_size: int = 20,
        search: str = "", user_id: str = "", stage: str = ""
    ) -> Dict[str, Any]:
        """列出书籍（分页 + 过滤）

        Args:
            page: 页码（从 1 开始）
            page_size: 每页数量
            search: 搜索关键词（匹配标题或 ID）
            user_id: 按所属用户过滤
            stage: 按当前阶段过滤（planning / writing / completed 等）

        Returns:
            包含 data / total / page / page_size 的字典
        """
        novels = self._novel_repo.list_all()

        # 过滤
        if search:
            search_lower = search.lower()
            novels = [
                n for n in novels
                if search_lower in n.title.lower() or search_lower in n.novel_id.value
            ]
        if user_id:
            novels = [n for n in novels if n.user_id == user_id]
        if stage:
            # 注意：从 DB 加载时 Novel 实体的 current_stage 才反映实际阶段，
            # stage 属性是旧版兼容字段，在 _row_to_novel 中未传入，默认为 PLANNING
            novels = [n for n in novels if n.current_stage.value == stage]

        total = len(novels)
        start = (page - 1) * page_size
        page_novels = novels[start:start + page_size]

        # 批量加载 slug（Novel 实体不持有 slug，直接从表读取）
        novel_ids = [n.novel_id.value for n in page_novels]
        slug_map = {}
        if novel_ids:
            placeholders = ",".join(["?" for _ in novel_ids])
            slug_rows = self._db.fetch_all(
                f"SELECT id, slug FROM novels WHERE id IN ({placeholders})",
                tuple(novel_ids),
            )
            slug_map = {r["id"]: r["slug"] for r in slug_rows}

        data = []
        for n in page_novels:
            stats = self._db.fetch_one(
                """SELECT COALESCE(SUM(LENGTH(content)), 0) as word_count,
                          COUNT(*) as chapter_count
                   FROM chapters WHERE novel_id = ?""",
                (n.novel_id.value,),
            )
            data.append({
                "id": n.novel_id.value,
                "title": n.title,
                "slug": slug_map.get(n.novel_id.value, n.novel_id.value),
                "author": n.author,
                "stage": n.current_stage.value,
                "autopilot_status": n.autopilot_status.value if n.autopilot_status else "stopped",
                "user_id": n.user_id,
                "word_count": stats["word_count"] if stats else 0,
                "chapter_count": stats["chapter_count"] if stats else 0,
            })

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "data": data,
        }

    def delete_book(self, novel_id: str) -> None:
        """删除书籍（级联删除所有关联数据）

        Args:
            novel_id: 书籍 ID
        """
        self._novel_repo.delete(NovelId(novel_id))
        logger.info("管理员删除书籍: %s", novel_id)

    def transfer_owner(self, novel_id: str, new_user_id: str) -> None:
        """转移书籍归属

        Args:
            novel_id: 书籍 ID
            new_user_id: 新拥有者的用户 ID
        """
        self._novel_repo.patch(NovelId(novel_id), user_id=new_user_id)
        logger.info("管理员转移书籍归属: %s → %s", novel_id, new_user_id)
