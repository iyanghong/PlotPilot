# application/assist/assist_service.py
"""灵感助手核心服务 — 会话管理 + 对话 + 字段提取 — 作者：Axelton"""
from __future__ import annotations

import json
import logging
import re
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)

from domain.ai.value_objects.prompt import Prompt
from domain.assist.entities import (
    InspireSession,
    InspireMessage,
    InspirationStrategy,
    InspireFieldData,
)
from domain.assist.repository import InspireRepository
from infrastructure.ai.llm_client import LLMClient

from application.assist.strategies.base import BaseInspirationStrategy
from application.assist.strategies.brainstorm import BrainstormStrategy
from application.assist.strategies.world_first import WorldFirstStrategy
from application.assist.strategies.character_driven import CharacterDrivenStrategy
from application.assist.strategies.theme_first import ThemeFirstStrategy


# ---- taxonomy template 匹配 ----

_TAXONOMY_YAML_PATH = (
    Path(__file__).resolve().parents[2] / "shared" / "taxonomy" / "builtin_cn_v1.yaml"
)


@lru_cache(maxsize=1)
def _load_taxonomy_lookup() -> Dict[str, Dict[str, Any]]:
    """加载 taxonomy 并构建 genre label → {world_tone, writing_profile} 查找表

    同时索引根节点和子节点标签，子节点优先匹配。
    """
    if not _TAXONOMY_YAML_PATH.is_file():
        logger.warning("taxonomy 文件不存在: %s", _TAXONOMY_YAML_PATH)
        return {}

    raw = yaml.safe_load(_TAXONOMY_YAML_PATH.read_text(encoding="utf-8"))
    lookup: Dict[str, Dict[str, Any]] = {}

    for root in raw.get("roots", []):
        root_label = root.get("labels", {}).get("zh-CN", "").strip()
        root_wp = _normalize_writing_profile(root.get("facets", {}).get("writing_profile", {}))
        root_wt = root.get("facets", {}).get("world_tone", "")

        # 根节点
        if root_label:
            lookup[root_label] = {
                "world_tone": root_wt,
                "writing_profile": root_wp,
            }
        # 子节点（优先覆盖）
        for child in root.get("children", []):
            child_label = child.get("labels", {}).get("zh-CN", "").strip()
            child_facets = child.get("facets", {})
            child_wp = _normalize_writing_profile(child_facets.get("writing_profile", {}))
            child_wt = child_facets.get("world_tone", "") or root_wt
            if child_label:
                lookup[child_label] = {
                    "world_tone": child_wt,
                    "writing_profile": child_wp if any(child_wp.values()) else root_wp,
                }

    logger.debug("taxonomy lookup 已加载 %d 个条目", len(lookup))
    return lookup


def _normalize_writing_profile(wp: dict) -> Dict[str, str]:
    """将 YAML 里的 writing_profile 对象转为统一字符串键"""
    return {
        "story_structure": (wp.get("story_structure") or "").strip(),
        "pacing_control": (wp.get("pacing_control") or "").strip(),
        "writing_style": (wp.get("writing_style") or "").strip(),
        "special_requirements": (wp.get("special_requirements") or "").strip(),
    }


def _resolve_taxonomy_fields(genre_str: str) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    """根据 LLM 提取的 genre 字符串匹配 taxonomy 内置模板

    genre_str 格式示例：'科幻/社会人际'、'科幻 / 星际文明'、'玄幻'

    Returns:
        (world_tone, writing_profile_dict) 或 (None, None)
    """
    if not genre_str or not genre_str.strip():
        return None, None

    lookup = _load_taxonomy_lookup()
    if not lookup:
        return None, None

    # 分割 genre 字符串
    parts = [p.strip() for p in re.split(r"\s*/\s*", genre_str.strip()) if p.strip()]

    # 优先匹配最具体的部分（子节点），再回退到根
    for part in reversed(parts):
        if part in lookup:
            entry = lookup[part]
            return entry["world_tone"], entry["writing_profile"]

    # 模糊匹配：子串包含在 label 中（同样优先更长的 label）
    for part in reversed(parts):
        for label, entry in sorted(lookup.items(), key=lambda x: len(x[0]), reverse=True):
            if part in label or label in part:
                return entry["world_tone"], entry["writing_profile"]

    return None, None


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

    # ---- helpers ----

    @staticmethod
    def _parse_json_response(raw: str) -> dict:
        """从 LLM 原始输出中提取 JSON，容忍 markdown 代码块包裹"""
        text = raw.strip()
        # 移除 markdown 代码块标记（```json 或 ```）
        if text.startswith("```"):
            # 去掉首行 ```json 或 ```
            text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
            # 去掉尾部 ```
            if text.rstrip().endswith("```"):
                text = text.rstrip()[:-3]
            text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试用正则提取 JSON 对象
            match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            logger.warning("无法解析 LLM JSON 输出: %.200s...", raw)
            return {}

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
        # 1. 保存用户消息（确保在构建上下文之前持久化）
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

        # 构建带历史的多轮对话 prompt — system prompt 包含全部行为指令，user prompt 只放对话文本
        conversation = _build_conversation_text(history)
        prompt = Prompt(
            system=(
                f"{strategy.build_system_prompt()}\n\n"
                f"请根据对话历史给出回复，用中文回复。"
            ),
            user=f"{conversation}\n\n助手：",
        )

        # 3. 流式生成
        full_content = ""
        try:
            async for chunk in self._llm.stream_generate(prompt):
                full_content += chunk
                yield chunk
        except Exception:
            logger.exception("chat 流式生成失败 session=%s", session.id)
            raise

        # 4. 保存 AI 回复（仅在流式成功完成后）
        if full_content:
            ai_msg = InspireMessage(
                id=f"msg_{uuid.uuid4().hex[:12]}",
                session_id=session.id,
                role="assistant",
                content=full_content,
            )
            await self._repo.add_message(ai_msg)

    # ---- field extraction ----

    async def generate_fields(self, session: InspireSession) -> InspireFieldData:
        """从对话历史中提取结构化字段 — 两步流程

        Step 1: LLM 提取 title / premise / genre
        Step 2: 匹配 taxonomy 内置模板后，再调 LLM 根据模板框架为具体故事定制 world_preset +
                story_structure / pacing_control / writing_style / special_requirements
        并将灵感会话标记为已完成。
        """
        history = await self._repo.get_messages(session.id)
        strategy = _get_strategy(session.strategy.value)
        conversation = _build_conversation_text(history)

        # ---- Step 1: 提取 title / premise / genre ----
        extraction_prompt = strategy.build_field_extraction_prompt(conversation)
        prompt = Prompt(
            system=strategy.build_system_prompt(),
            user=extraction_prompt,
        )
        raw = ""
        async for chunk in self._llm.stream_generate(prompt):
            raw += chunk

        data = self._parse_json_response(raw)
        genre_str = data.get("genre", "")
        title = data.get("title", "")
        premise = data.get("premise", "")

        # ---- Step 2: 匹配 taxonomy 模板并调 LLM 定制化 ----
        tax_world_tone, tax_wp = _resolve_taxonomy_fields(genre_str)

        if tax_wp:
            # 用内置模板作为框架，让 LLM 为这部具体作品定制
            cust_prompt = strategy.build_field_customization_prompt(
                conversation_history=conversation,
                title=title,
                premise=premise,
                genre=genre_str,
                tax_writing_profile=tax_wp,
                tax_world_tone=tax_world_tone or "",
            )
            cust_raw = ""
            async for chunk in self._llm.stream_generate(Prompt(
                system=(
                    "你是一个写作规则定制专家，擅长将通用写作模板适配到具体作品。"
                    "严格遵循模板的结构框架，但将内容替换为贴合作品的定制化描述。"
                    "用中文回复。"
                ),
                user=cust_prompt,
            )):
                cust_raw += chunk

            cust_data = self._parse_json_response(cust_raw)
            fields = InspireFieldData(
                title=title,
                premise=premise,
                genre=genre_str,
                world_preset=cust_data.get("worldPreset", tax_world_tone or ""),
                story_structure=cust_data.get("storyStructure", tax_wp.get("story_structure", "")),
                pacing_control=cust_data.get("pacingControl", tax_wp.get("pacing_control", "")),
                writing_style=cust_data.get("writingStyle", tax_wp.get("writing_style", "")),
                special_requirements=cust_data.get("specialRequirements", tax_wp.get("special_requirements", "")),
            )
        else:
            # 未匹配到 taxonomy 模板时，由 LLM 自由生成全部字段
            fields = InspireFieldData(
                title=title,
                premise=premise,
                genre=genre_str,
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
