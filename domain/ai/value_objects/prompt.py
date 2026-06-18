# domain/ai/value_objects/prompt.py
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass(frozen=True)
class Prompt:
    """提示词值对象"""
    system: str
    user: str

    def __post_init__(self):
        if not self.user or not self.user.strip():
            raise ValueError("User message cannot be empty")
        if not self.system or not self.system.strip():
            raise ValueError("System message cannot be empty")

    def to_messages(self) -> List[Dict[str, Any]]:
        """转换为消息列表格式"""
        messages = []
        if self.system:
            messages.append({"role": "system", "content": self.system})
        messages.append({"role": "user", "content": self.user})
        return messages


@dataclass(frozen=True)
class ToolCall:
    """LLM 发起的工具调用"""
    id: str
    name: str
    arguments: dict


@dataclass(frozen=True)
class ToolDefinition:
    """工具定义（传给 LLM 的 JSON Schema）"""
    name: str
    description: str
    parameters: dict


@dataclass(frozen=True)
class Message:
    """单条多轮对话消息"""
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
