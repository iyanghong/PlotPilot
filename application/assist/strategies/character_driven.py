"""角色驱动策略 — 作者：Axelton"""
from __future__ import annotations

from application.assist.strategies.base import BaseInspirationStrategy


class CharacterDrivenStrategy(BaseInspirationStrategy):
    """角色驱动 — 追问角色的欲望、恐惧、缺陷、关系，从角色推导故事"""

    @property
    def name(self) -> str:
        return "character_driven"

    @property
    def description(self) -> str:
        return "角色驱动 — 从一个鲜活的人物出发，让故事围绕他/她展开"

    def build_system_prompt(self) -> str:
        return (
            "你是一个角色驱动的故事开发助手，相信「好故事从好角色开始」。\n\n"
            "你的对话风格：\n"
            "- 先帮助用户发现/塑造一个有意思的主角\n"
            "- 追问角色的欲望（想要什么）、恐惧（害怕什么）、缺陷（有什么毛病）、关系（身边有谁）\n"
            "- 从角色的内在矛盾推导故事冲突\n"
            "- 从角色的世界观推导故事世界设定\n"
            "- 每次聚焦角色的一两个方面，逐步丰富\n\n"
            "对话维度顺序建议：角色初印象 → 欲望与恐惧 → 缺陷与成长弧 → 关系网 → 由此衍生的世界与冲突\n"
            "用中文回复。"
        )

    def build_field_extraction_prompt(self, conversation_history: str) -> str:
        return (
            f"根据以下对话历史，提取角色信息及由此衍生的故事结构化信息。\n\n"
            f"对话历史：\n{conversation_history}\n\n"
            f"请以 JSON 格式输出，包含以下字段：\n"
            f'{{"title": "建议的书名", "premise": "200字以内的核心梗概（从角色出发推导）", '
            f'"genre": "大类/细分主题", '
            f'"worldPreset": "世界观基调描述（与角色匹配）", '
            f'"storyStructure": "建议的剧情结构（适配角色成长弧）", '
            f'"pacingControl": "节奏把控建议", '
            f'"writingStyle": "建议的写作风格", '
            f'"specialRequirements": "特殊要求或注意事项"}}\n\n'
            f"只输出 JSON，不要任何额外文字。"
        )
