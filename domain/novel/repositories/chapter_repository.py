from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from domain.novel.entities.chapter import Chapter
from domain.novel.value_objects.novel_id import NovelId
from domain.novel.value_objects.chapter_id import ChapterId


class ChapterRepository(ABC):
    """章节仓储接口"""

    @abstractmethod
    def save(self, chapter: Chapter) -> None:
        """保存章节"""
        pass

    @abstractmethod
    def get_by_id(self, chapter_id: ChapterId) -> Optional[Chapter]:
        """根据 ID 获取章节"""
        pass

    @abstractmethod
    def list_by_novel(self, novel_id: NovelId) -> List[Chapter]:
        """
        列出小说的所有章节（含正文）

        返回的章节列表按章节序号升序排序
        """
        pass

    def list_chapters_meta_for_novels(self, novel_ids: List[str]) -> Dict[str, List[Chapter]]:
        """批量获取多个小说的章节元数据（不含正文 content/outline），按 novel_id 分组

        默认实现回退到逐本调用 list_by_novel；SQLite 实现应覆写为单条 IN 查询。
        """
        result: Dict[str, List[Chapter]] = {}
        for nid in novel_ids:
            try:
                result[nid] = self.list_by_novel(NovelId(nid))
            except Exception:
                result[nid] = []
        return result

    @abstractmethod
    def exists(self, chapter_id: ChapterId) -> bool:
        """检查章节是否存在"""
        pass

    @abstractmethod
    def delete(self, chapter_id: ChapterId) -> None:
        """
        删除章节

        如果章节不存在，此操作不会引发错误
        """
        pass
