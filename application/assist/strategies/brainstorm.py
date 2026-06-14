"""脑洞爆破策略 — 作者：Axelton"""
from __future__ import annotations

from application.assist.strategies.base import BaseInspirationStrategy


class BrainstormStrategy(BaseInspirationStrategy):
    """脑洞爆破 — 通过轻松聊天帮用户从兴趣、情绪、最近看过的作品等角度找到创作冲动"""

    @property
    def name(self) -> str:
        return "brainstorm"

    @property
    def description(self) -> str:
        return "脑洞爆破 — 从你的兴趣和情绪出发，轻松聊出创作火花"

    def build_system_prompt(self) -> str:
        return (
            "你是一个创意写作灵感助手，擅长通过轻松自然的对话帮助用户发现想写的故事。\n\n"
            "你的对话风格：\n"
            "- 使用日常语言，不问专业术语\n"
            "- 从用户的兴趣、情绪、最近看过的作品、梦、记忆等角度切入\n"
            "- 像朋友聊天一样，引导用户说出心中模糊的故事种子\n"
            "- 每次只问一个问题，耐心引导\n"
            "- 当用户提到一个具体想法时，帮他/她展开并具象化\n\n"
            "不要直接问「你想写什么类型的小说」，而是通过侧面引导让用户自己发现。\n"
            "用中文回复。"
        )

    def build_field_extraction_prompt(self, conversation_history: str) -> str:
        return (
            f"根据以下对话历史，提取用户想要创作的小说的结构化信息。\n\n"
            f"对话历史：\n{conversation_history}\n\n"
            f"请以 JSON 格式输出，包含以下字段（如果对话中未明确提及，根据上下文合理推断）：\n"
            f'{{"title": "建议的书名", "premise": "200字以内的核心梗概", '
            f'"genre": "大类/细分主题（如：科幻/末世废土）", '
            f'"worldPreset": "世界观基调描述", '
            f'"storyStructure": "建议的剧情结构", '
            f'"pacingControl": "节奏把控建议", '
            f'"writingStyle": "建议的写作风格", '
            f'"specialRequirements": "特殊要求或注意事项"}}\n\n'
            f"只输出 JSON，不要任何额外文字。"
        )
