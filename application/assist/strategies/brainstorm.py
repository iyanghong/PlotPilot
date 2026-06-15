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
            "你是一个创意写作灵感助手，擅长根据用户的只言片语直接帮他们构建完整的故事框架。\n\n"
            "**绝对禁止提问！** 永远不要在回复中使用问号或以疑问句结尾。\n\n"
            "你的工作方式：\n"
            "- 用户说出任何碎片想法，你立刻展开联想分析，给出具体的世界观、人物、冲突、结构建议\n"
            "- 如果用户信息很少，不要追问，而是基于已有信息大胆推测并给出完整的创作方案\n"
            "- 每次回复末尾用一句话总结当前已明确的核心方向，但不要问「你觉得呢」\n"
            "- 语言轻松日常，像朋友在分享想法，不是在采访\n\n"
            "用中文回复。"
        )

    def build_field_extraction_prompt(self, conversation_history: str) -> str:
        return (
            f"根据以下对话历史，提取用户想要创作的小说的核心信息。\n\n"
            f"对话历史：\n{conversation_history}\n\n"
            f"请以 JSON 格式输出，包含以下字段（如果对话中未明确提及，根据上下文合理推断）：\n"
            f'{{"title": "建议的书名", "premise": "200字以内的核心梗概", '
            f'"genre": "大类/细分主题"}}\n\n'
            f"genre 请从以下大类中优先匹配：玄幻、奇幻、武侠、仙侠、都市、历史、游戏、网游、科幻、末世、体育、种田、悬疑、灵异、"
            f"军事、轻小说、同人、综合言情。可附加细分主题（如：科幻/星际文明、都市/商战职场、玄幻/东方玄幻）。\n\n"
            f"剧情结构、节奏把控、写作风格、特殊要求这四个字段不需要你生成，系统会按 genre 自动匹配内置模板。\n\n"
            f"只输出 JSON，不要任何额外文字。"
        )
