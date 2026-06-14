"""灵感策略抽象基类 — 作者：Axelton"""
from __future__ import annotations

from abc import ABC, abstractmethod

from domain.ai.value_objects.prompt import Prompt


class BaseInspirationStrategy(ABC):
    """灵感策略抽象基类 — 每个策略定义系统提示词和字段提取提示词"""

    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """策略描述（给用户看的）"""
        ...

    @abstractmethod
    def build_system_prompt(self) -> str:
        """构建系统提示词 — 锁定对话框架"""
        ...

    @abstractmethod
    def build_field_extraction_prompt(self, conversation_history: str) -> str:
        """构建字段提取提示词 — 从对话历史中提取结构化字段"""
        ...

    def make_prompt(self, user_message: str) -> Prompt:
        """根据用户消息创建 Prompt 对象"""
        return Prompt(
            system=self.build_system_prompt(),
            user=user_message,
        )

    def make_field_extraction_prompt_obj(self, conversation_history: str) -> Prompt:
        """创建字段提取 Prompt 对象"""
        return Prompt(
            system=self.build_system_prompt(),
            user=self.build_field_extraction_prompt(conversation_history),
        )
