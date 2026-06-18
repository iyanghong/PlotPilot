# domain/assist/repository.py
"""灵感助手仓储抽象接口 — 作者：Axelton"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from domain.assist.entities import InspireSession, InspireMessage


class InspireRepository(ABC):
    """灵感助手仓储抽象接口"""

    @abstractmethod
    async def create_session(self, session: InspireSession) -> InspireSession:
        """创建会话"""
        ...

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[InspireSession]:
        """获取会话"""
        ...

    @abstractmethod
    async def update_session(self, session: InspireSession) -> InspireSession:
        """更新会话"""
        ...

    @abstractmethod
    async def add_message(self, message: InspireMessage) -> InspireMessage:
        """添加消息"""
        ...

    @abstractmethod
    async def get_messages(self, session_id: str) -> List[InspireMessage]:
        """获取会话的全部消息（按时间正序）"""
        ...

    @abstractmethod
    async def get_latest_session(self, novel_id: str) -> Optional[InspireSession]:
        """获取某书目最近一次活跃会话"""
        ...

    @abstractmethod
    async def list_sessions_by_novel(self, novel_id: str) -> List[InspireSession]:
        """获取某书目的全部会话（按创建时间倒序）"""
        ...

    @abstractmethod
    async def save_field_data(self, session_id: str, field_data: dict) -> None:
        """保存字段提取结果到会话"""
        ...
