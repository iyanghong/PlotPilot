"""主题先行策略 — 作者：Axelton"""
from __future__ import annotations

from application.assist.strategies.base import BaseInspirationStrategy


class ThemeFirstStrategy(BaseInspirationStrategy):
    """主题先行 — 追问主题的切面、对立面、载体，找到具象化的故事外壳"""

    @property
    def name(self) -> str:
        return "theme_first"

    @property
    def description(self) -> str:
        return "主题先行 — 从一个你想探讨的主题出发，找到最适合承载它的故事"

    def build_system_prompt(self) -> str:
        return (
            "你是一个主题驱动的故事开发助手，擅长帮助用户将抽象主题具象化为故事。\n\n"
            "你的对话风格：\n"
            "- 从用户感兴趣的主题/议题切入（如「自由」「复仇」「成长」「爱」）\n"
            "- 追问主题的不同切面和对立面（例如「正义」vs「复仇」的边界）\n"
            "- 帮助用户找到承载主题的具体人物和情境\n"
            "- 推导最适合这个主题的叙事结构\n"
            "- 每次深入一个切面，逐步构建完整的故事框架\n\n"
            "对话维度顺序建议：主题确认 → 切面展开 → 对立面引入 → 人物载体 → 故事结构\n"
            "用中文回复。"
        )

    def build_field_extraction_prompt(self, conversation_history: str) -> str:
        return (
            f"根据以下对话历史，提取主题信息及由此衍生的故事结构化信息。\n\n"
            f"对话历史：\n{conversation_history}\n\n"
            f"请以 JSON 格式输出，包含以下字段：\n"
            f'{{"title": "建议的书名", "premise": "200字以内的核心梗概（表现主题）", '
            f'"genre": "大类/细分主题", '
            f'"worldPreset": "世界观基调描述（服务于主题）", '
            f'"storyStructure": "建议的剧情结构（匹配主题展开节奏）", '
            f'"pacingControl": "节奏把控建议", '
            f'"writingStyle": "建议的写作风格", '
            f'"specialRequirements": "特殊要求或注意事项"}}\n\n'
            f"只输出 JSON，不要任何额外文字。"
        )
