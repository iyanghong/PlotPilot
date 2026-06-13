"""内存版小说仓储实现（用于测试守护进程）

注意：这是临时实现，生产环境需要替换为真正的数据库实现
"""
from typing import List, Optional, Dict
from domain.novel.entities.novel import Novel, AutopilotStatus
from domain.novel.value_objects.novel_id import NovelId
from domain.novel.repositories.novel_repository import NovelRepository


class InMemoryNovelRepository(NovelRepository):
    """内存版小说仓储（用于测试）"""

    def __init__(self):
        self._storage: Dict[str, Novel] = {}

    def save(self, novel: Novel) -> None:
        """保存小说"""
        self._storage[novel.novel_id.value] = novel

    async def async_save(self, novel: Novel) -> None:
        """异步保存小说"""
        self.save(novel)

    def get_by_id(self, novel_id: NovelId) -> Optional[Novel]:
        """根据 ID 获取小说"""
        return self._storage.get(novel_id.value)

    def list_all(self) -> List[Novel]:
        """列出所有小说"""
        return list(self._storage.values())

    def find_by_autopilot_status(self, status: AutopilotStatus) -> List[Novel]:
        """根据自动驾驶状态查询小说"""
        return [
            novel for novel in self._storage.values()
            if novel.autopilot_status == status
        ]

    def delete(self, novel_id: NovelId) -> None:
        """删除小说"""
        if novel_id.value in self._storage:
            del self._storage[novel_id.value]

    def list_by_user(self, user_id: str) -> List[Novel]:
        """列出指定用户的全部小说"""
        return [
            novel for novel in self._storage.values()
            if getattr(novel, "user_id", None) == user_id
        ]

    def get_by_id_and_user(self, novel_id: NovelId, user_id: str) -> Optional[Novel]:
        """根据 ID 和用户 ID 获取小说"""
        novel = self._storage.get(novel_id.value)
        if novel and getattr(novel, "user_id", None) == user_id:
            return novel
        return None

    def patch(self, novel_id: NovelId, **fields) -> None:
        """增量更新小说字段"""
        novel = self._storage.get(novel_id.value)
        if novel is None:
            return
        for key, value in fields.items():
            setattr(novel, key, value)

    def exists(self, novel_id: NovelId) -> bool:
        """检查小说是否存在"""
        return novel_id.value in self._storage
