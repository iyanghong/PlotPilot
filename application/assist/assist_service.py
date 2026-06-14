# application/assist/assist_service.py
"""灵感助手核心服务 — 会话管理 + 对话 + 字段提取 — 作者：Axelton"""
from __future__ import annotations

import json
import uuid
from typing import AsyncIterator, List, Optional

from domain.ai.value_objects.prompt import Prompt
from domain.assist.entities import (
    InspireSession,
    InspireMessage,
    InspirationStrategy,
    SessionStatus,
    InspireFieldData,
)
from domain.assist.repository import InspireRepository
from infrastructure.ai.llm_client import LLMClient

from application.assist.strategies.base import BaseInspirationStrategy
from application.assist.strategies.brainstorm import BrainstormStrategy
from application.assist.strategies.world_first import WorldFirstStrategy
from application.assist.strategies.character_driven import CharacterDrivenStrategy
from application.assist.strategies.theme_first import ThemeFirstStrategy


def _get_strategy(strategy_name: str) -> BaseInspirationStrategy:
    """根据策略名获取策略实例"""
    mapping = {
        "brainstorm": BrainstormStrategy(),
        "world_first": WorldFirstStrategy(),
        "character_driven": CharacterDrivenStrategy(),
        "theme_first": ThemeFirstStrategy(),
    }
    if strategy_name not in mapping:
        raise ValueError(f"未知策略: {strategy_name}")
    return mapping[strategy_name]


def _build_conversation_text(messages: List[InspireMessage]) -> str:
    """将消息列表拼接为对话文本"""
    lines = []
    for m in messages:
        role_label = "用户" if m.role == "user" else "助手"
        lines.append(f"{role_label}: {m.content}")
    return "\n".join(lines)


class AssistService:
    """灵感助手核心服务 — 管理灵感对话会话的全生命周期"""

    def __init__(self, repository: InspireRepository, llm_client: LLMClient = None):
        """
        初始化服务

        Args:
            repository: 灵感助手仓储实现
            llm_client: LLM 客户端（可选，默认创建新实例）
        """
        self._repo = repository
        self._llm = llm_client or LLMClient()

    # ---- session management ----

    async def create_session(
        self, novel_id: str, strategy_name: str
    ) -> InspireSession:
        """创建新会话"""
        strategy = InspirationStrategy(strategy_name)
        session = InspireSession(
            id=f"sess_{uuid.uuid4().hex[:12]}",
            novel_id=novel_id,
            strategy=strategy,
        )
        return await self._repo.create_session(session)

    async def get_or_create_session(
        self, novel_id: str, strategy_name: str
    ) -> InspireSession:
        """获取最近活跃会话，若无则创建"""
        existing = await self._repo.get_latest_session(novel_id)
        if existing and existing.strategy.value == strategy_name:
            return existing
        return await self.create_session(novel_id, strategy_name)

    async def get_session(self, session_id: str) -> Optional[InspireSession]:
        """按 ID 获取会话"""
        return await self._repo.get_session(session_id)

    async def get_messages(self, session_id: str) -> List[InspireMessage]:
        """获取会话的全部消息"""
        return await self._repo.get_messages(session_id)

    # ---- chat ----

    async def chat(
        self,
        session: InspireSession,
        user_message: str,
    ) -> AsyncIterator[str]:
        """流式对话 — 返回 AI 回复的逐块文本

        Args:
            session: 当前灵感和会话
            user_message: 用户输入的消息文本

        Yields:
            AI 回复的文本片段（逐 token 输出）
        """
        # 1. 保存用户消息
        user_msg = InspireMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            session_id=session.id,
            role="user",
            content=user_message,
        )
        await self._repo.add_message(user_msg)

        # 2. 构建上下文
        history = await self._repo.get_messages(session.id)
        strategy = _get_strategy(session.strategy.value)

        # 构建带历史的多轮对话 prompt
        conversation = _build_conversation_text(history)
        full_prompt = (
            f"以下是对话历史：\n\n{conversation}\n\n"
            f"请根据对话历史，继续引导用户深入探索。用中文回复。"
        )
        prompt = Prompt(system=strategy.build_system_prompt(), user=full_prompt)

        # 3. 流式生成
        full_content = ""
        async for chunk in self._llm.stream_generate(prompt):
            full_content += chunk
            yield chunk

        # 4. 保存 AI 回复
        ai_msg = InspireMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            session_id=session.id,
            role="assistant",
            content=full_content,
        )
        await self._repo.add_message(ai_msg)

    # ---- field extraction ----

    async def generate_fields(self, session: InspireSession) -> InspireFieldData:
        """从对话历史中提取结构化字段

        调用 LLM 分析完整对话历史，提取作品标题、前提、类型、
        世界观预设、故事结构、节奏控制、写作风格、特殊需求等字段，
        并将灵感会话标记为已完成。

        Args:
            session: 灵感助手对话会话

        Returns:
            结构化的 InspireFieldData 值对象
        """
        history = await self._repo.get_messages(session.id)
        strategy = _get_strategy(session.strategy.value)
        conversation = _build_conversation_text(history)

        # 使用 stream_generate 收集完整结果，以确保策略的系统提示词生效
        extraction_prompt = strategy.build_field_extraction_prompt(conversation)
        prompt = Prompt(
            system=strategy.build_system_prompt(),
            user=extraction_prompt,
        )
        raw = ""
        async for chunk in self._llm.stream_generate(prompt):
            raw += chunk

        # 解析 JSON（清洗可能的 markdown 代码块包裹）
        raw = raw.strip()
        if raw.startswith("```"):
            # 移除 markdown 代码块标记
            raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        data = json.loads(raw)

        fields = InspireFieldData(
            title=data.get("title", ""),
            premise=data.get("premise", ""),
            genre=data.get("genre", ""),
            world_preset=data.get("worldPreset", ""),
            story_structure=data.get("storyStructure", ""),
            pacing_control=data.get("pacingControl", ""),
            writing_style=data.get("writingStyle", ""),
            special_requirements=data.get("specialRequirements", ""),
        )

        # 将会话标记为完成
        session.complete()
        await self._repo.update_session(session)

        return fields

    # ---- resume ----

    async def resume_session(self, session_id: str) -> dict:
        """恢复历史会话 — 返回全部消息及会话元数据

        Args:
            session_id: 灵感助手会话 ID

        Returns:
            包含 session_id、strategy、status、messages 的字典

        Raises:
            ValueError: 当会话不存在时抛出
        """
        session = await self._repo.get_session(session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")
        messages = await self._repo.get_messages(session_id)
        return {
            "session_id": session.id,
            "strategy": session.strategy.value,
            "status": session.status.value,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "field_suggestions": m.field_suggestions,
                    "created_at": m.created_at.isoformat(),
                }
                for m in messages
            ],
        }
