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
            "**绝对禁止提问！** 永远不要在回复中使用问号或以疑问句结尾。\n\n"
            "你的工作方式：\n"
            "- 从用户提到的任何角色特征出发，立刻塑造一个立体的主角形象\n"
            "- 分析角色的欲望、恐惧、缺陷、关系网，全部基于你的推测给出具体设定\n"
            "- 从角色的内在矛盾直接推导故事冲突和世界观\n"
            "- 每次回复末尾用一句话总结当前已明确的角色核心\n\n"
            "分析维度顺序建议：角色初印象 → 欲望与恐惧 → 缺陷与成长弧 → 关系网 → 由此衍生的世界与冲突\n"
            "用中文回复。"
        )

    def build_field_extraction_prompt(self, conversation_history: str) -> str:
        return (
            f"根据以下对话历史，提取角色信息及由此衍生的故事核心信息。\n\n"
            f"对话历史：\n{conversation_history}\n\n"
            f"请以 JSON 格式输出，包含以下字段：\n"
            f'{{"title": "建议的书名", "premise": "200字以内的核心梗概（从角色出发推导）", '
            f'"genre": "大类/细分主题"}}\n\n'
            f"genre 请从以下大类中优先匹配：玄幻、奇幻、武侠、仙侠、都市、历史、游戏、网游、科幻、末世、体育、种田、悬疑、灵异、"
            f"军事、轻小说、同人、综合言情。可附加细分主题（如：科幻/星际文明、都市/商战职场、玄幻/东方玄幻）。\n\n"
            f"剧情结构、节奏把控、写作风格、特殊要求这四个字段不需要你生成，系统会按 genre 自动匹配内置模板。\n\n"
            f"只输出 JSON，不要任何额外文字。"
        )
