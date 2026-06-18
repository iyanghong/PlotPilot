"""世界观优先策略 — 作者：Axelton"""
from __future__ import annotations

from application.assist.strategies.base import BaseInspirationStrategy


class WorldFirstStrategy(BaseInspirationStrategy):
    """世界观优先 — 引导描述物理规则、社会结构、历史背景、独特美学"""

    @property
    def name(self) -> str:
        return "world_first"

    @property
    def description(self) -> str:
        return "世界观优先 — 先构建世界，再让故事从中自然生长"

    def build_system_prompt(self) -> str:
        return (
            "你是一个世界观架构师，擅长根据用户的只言片语直接构建独特的世界设定。\n\n"
            "**绝对禁止提问！** 永远不要在回复中使用问号或以疑问句结尾。\n\n"
            "你的工作方式：\n"
            "- 从用户的任何描述中提炼世界观轮廓，立刻展开物理规则、社会结构、历史背景、独特美学的分析\n"
            "- 从宏观到微观逐步细化，每个维度都给出具体建议\n"
            "- 用「如果…会怎样」的方式展开想象，但不要问用户，直接给出你的推测和建议\n"
            "- 指出世界中蕴含的天然冲突和故事可能性\n"
            "- 每次回复末尾用一句话总结当前已构建的世界观核心\n\n"
            "分析维度顺序建议：基础规则 → 社会结构 → 历史事件 → 美学风格 → 冲突发现\n"
            "用中文回复。"
        )

    def build_agent_system_prompt(self) -> str:
        return (
            "你是一个世界观架构师，擅长帮作者构建独特且有深度的虚构世界。\n\n"
            "对话节奏：\n"
            "- 从物理规则、社会结构、历史背景、独特美学四个维度展开分析\n"
            "- 用「如果…会怎样」的句式激发想象\n"
            "- 每次回复末尾最多追问一句来澄清关键方向\n\n"
            "工具使用：\n"
            "- 当用户提到具体类型时（如「末世」「玄幻」「悬疑」），"
            "调用 lookup_genre_templates 获取该类型的写作模板\n\n"
            "用中文回复。"
        )

    def build_field_extraction_prompt(self, conversation_history: str) -> str:
        return (
            f"根据以下对话历史，提取用户构建的世界观及由此衍生的故事核心信息。\n\n"
            f"对话历史：\n{conversation_history}\n\n"
            f"请以 JSON 格式输出，包含以下字段（如果对话中未明确提及，根据上下文合理推断）：\n"
            f'{{"title": "建议的书名", "premise": "200字以内的核心梗概（基于世界观推导）", '
            f'"genre": "大类（仅一个）", "sub_genre": "网文主题/细分主题"}}\n\n'
            f"genre 请从以下大类中仅选择一个：玄幻、奇幻、武侠、仙侠、都市、历史、游戏、网游、科幻、末世、体育、种田、悬疑、灵异、"
            f"军事、轻小说、同人、综合言情。\n"
            f"sub_genre 选填，为二级网文主题（如：星际文明、东方玄幻、商战职场、末日生存、悬疑推理等），若对话中未明确则留空。\n\n"
            f"剧情结构、节奏把控、写作风格、特殊要求这四个字段不需要你生成，系统会按 genre 自动匹配内置模板。\n\n"
            f"只输出 JSON，不要任何额外文字。"
        )
