"""灵感策略抽象基类 — 作者：Axelton"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

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

    def build_agent_system_prompt(self) -> str:
        """构建 Agent 系统提示词 — 用于多轮对话 + 工具调用场景

        默认委托给 build_system_prompt()，子类可覆写以区分 Agent 和非 Agent 场景。
        """
        return self.build_system_prompt()

    @abstractmethod
    def build_agent_system_prompt(self) -> str:
        """构建 Agent 系统提示词 — 多轮协作式对话框架"""
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

    def build_field_customization_prompt(
        self,
        conversation_history: str,
        title: str,
        premise: str,
        genre: str,
        tax_writing_profile: Dict[str, str],
        tax_world_tone: str,
    ) -> str:
        """构建字段定制化提示词 — 根据内置模板格式为具体故事定制四个写作原则字段

        内置模板提供结构和规则框架，LLM 需要将其适配到用户具体的故事中来，
        而不是原封不动照抄模板。
        """
        return (
            f"你是一个写作规则定制专家。你的任务是根据内置模板的结构和规则框架，"
            f"为下面这部具体作品定制专属的写作原则。\n\n"
            f"---\n"
            f"作品信息：\n"
            f"书名：{title}\n"
            f"梗概：{premise}\n"
            f"大类：{genre}\n\n"
            f"对话历史（供参考）：\n{conversation_history}\n\n"
            f"---\n"
            f"以下是该大类「{genre}」的内置写作模板，请将它们定制化改写，使其贴合这部具体作品：\n\n"
            f"【世界观基调 — 内置模板】\n{tax_world_tone}\n\n"
            f"【剧情结构 — 内置模板】\n{tax_writing_profile.get('story_structure', '')}\n\n"
            f"【节奏把控 — 内置模板】\n{tax_writing_profile.get('pacing_control', '')}\n\n"
            f"【写作风格 — 内置模板】\n{tax_writing_profile.get('writing_style', '')}\n\n"
            f"【特殊要求 — 内置模板】\n{tax_writing_profile.get('special_requirements', '')}\n\n"
            f"---\n"
            f"定制化要求：\n"
            f"1. 保留模板的结构框架（如开篇/发展/高潮/结尾、小爽点/中爽点/大爽点、叙事/环境/对话等分项结构）\n"
            f"2. 将模板中的通用描述替换为这部具体作品的世界观、人物、冲突特征\n"
            f"3. 不要照抄模板原文，根据对话历史和梗概写出有针对性的内容\n"
            f"4. 世界观基调要贴合对话中讨论的具体设定\n\n"
            f"请以 JSON 格式输出，包含以下 4 个字段（每个字段都是多行文本）：\n"
            f'{{"worldPreset": "定制化的世界观基调", '
            f'"storyStructure": "定制化的剧情结构", '
            f'"pacingControl": "定制化的节奏把控", '
            f'"writingStyle": "定制化的写作风格", '
            f'"specialRequirements": "定制化的特殊要求"}}\n\n'
            f"只输出 JSON，不要任何额外文字。"
        )
