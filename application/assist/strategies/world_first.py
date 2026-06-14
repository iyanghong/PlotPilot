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
            "你是一个世界观架构师，擅长通过「如果……会怎样」的假设性问题，"
            "帮助用户构建独特的世界设定。\n\n"
            "你的对话风格：\n"
            "- 从宏观到微观，逐步细化世界设定\n"
            "- 引导用户思考物理规则、社会结构、历史背景、独特美学\n"
            "- 用「如果…会怎样」的方式展开想象\n"
            "- 每次聚焦一个维度，不要一次问太多\n"
            "- 帮助用户发现世界中蕴含的天然冲突和故事可能性\n\n"
            "对话维度顺序建议：基础规则 → 社会结构 → 历史事件 → 美学风格 → 冲突发现\n"
            "用中文回复。"
        )

    def build_field_extraction_prompt(self, conversation_history: str) -> str:
        return (
            f"根据以下对话历史，提取用户构建的世界观及由此衍生的故事信息。\n\n"
            f"对话历史：\n{conversation_history}\n\n"
            f"请以 JSON 格式输出，包含以下字段：\n"
            f'{{"title": "建议的书名", "premise": "200字以内的核心梗概（基于世界观推导）", '
            f'"genre": "大类/细分主题", '
            f'"worldPreset": "世界观基调描述（基于对话提炼）", '
            f'"storyStructure": "建议的剧情结构（与世界观匹配）", '
            f'"pacingControl": "节奏把控建议", '
            f'"writingStyle": "建议的写作风格", '
            f'"specialRequirements": "特殊要求或注意事项"}}\n\n'
            f"只输出 JSON，不要任何额外文字。"
        )
