"""工具注册表 — Agent 工具的统一注册和执行入口 — 作者：Axelton"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from domain.ai.value_objects.prompt import ToolDefinition

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Tool:
    """工具描述 — 绑定名称、定义和执行函数"""
    name: str
    description: str
    parameters: dict  # JSON Schema
    handler: Callable  # async (args: dict) -> str


class ToolRegistry:
    """工具注册表 — 灵感助手和未来 Agent 场景的统一工具入口"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool

    def get_definitions(self) -> list[ToolDefinition]:
        """获取所有工具定义（传给 LLM）"""
        return [
            ToolDefinition(name=t.name, description=t.description, parameters=t.parameters)
            for t in self._tools.values()
        ]

    async def execute(self, name: str, args: dict) -> str:
        """执行工具并返回文本结果"""
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"未知工具: {name}")
        try:
            return await tool.handler(args)
        except Exception as e:
            logger.error("工具执行失败 tool=%s args=%s: %s", name, args, e)
            return f"工具执行失败: {e}"


# 全局单例
_tool_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册表单例"""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
