# domain/assist/entities.py
"""灵感助手领域实体 — 作者：Axelton"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from domain.shared.base_entity import BaseEntity


class InspirationStrategy(str, Enum):
    """灵感策略枚举"""
    BRAINSTORM = "brainstorm"          # 脑洞爆破
    WORLD_FIRST = "world_first"        # 世界观优先
    CHARACTER_DRIVEN = "character_driven"  # 角色驱动
    THEME_FIRST = "theme_first"        # 主题先行


class SessionStatus(str, Enum):
    """会话状态"""
    ACTIVE = "active"
    COMPLETED = "completed"


class InspireSession(BaseEntity):
    """灵感对话会话"""

    def __init__(
        self,
        id: str,
        novel_id: str,
        strategy: InspirationStrategy,
        status: SessionStatus = SessionStatus.ACTIVE,
        field_data: Optional[dict] = None,
    ):
        super().__init__(id)
        self.novel_id = novel_id
        self.strategy = strategy
        self.status = status
        self.field_data = field_data or {}  # 保存的字段提取结果

    def complete(self) -> None:
        """标记会话完成"""
        self.status = SessionStatus.COMPLETED
        self.updated_at = datetime.now(timezone.utc)

    def set_field_data(self, data: dict) -> None:
        """保存字段提取结果"""
        self.field_data = data
        self.updated_at = datetime.now(timezone.utc)


class InspireMessage(BaseEntity):
    """对话消息"""

    def __init__(
        self,
        id: str,
        session_id: str,
        role: str,  # "user" | "assistant"
        content: str,
        field_suggestions: Optional[dict] = None,
    ):
        super().__init__(id)
        self.session_id = session_id
        self.role = role
        self.content = content
        self.field_suggestions = field_suggestions or {}


@dataclass(frozen=True)
class InspireFieldData:
    """字段提取结果 — 不可变值对象，由 generate_fields action 产出"""
    title: str = ""
    premise: str = ""
    genre: str = ""
    sub_genre: str = ""  # 二级分类/网文主题（如「星际文明」「东方玄幻」）
    world_preset: str = ""
    story_structure: str = ""
    pacing_control: str = ""
    writing_style: str = ""
    special_requirements: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "premise": self.premise,
            "genre": self.genre,
            "sub_genre": self.sub_genre,
            "world_preset": self.world_preset,
            "story_structure": self.story_structure,
            "pacing_control": self.pacing_control,
            "writing_style": self.writing_style,
            "special_requirements": self.special_requirements,
        }
