# domain/ai/value_objects/prompt.py
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass(frozen=True)
class Prompt:
    """提示词值对象

    支持两种使用模式：
    1. 旧路径：system + user 字段，向后兼容
    2. 新路径：messages 多轮消息数组，支持 tool 角色和 assistant tool_calls
    """
    system: str
    user: str
    messages: Optional[List[Message]] = None  # 多轮消息数组，为 None 时走旧路径
    tools: Optional[List[ToolDefinition]] = None  # 工具定义列表，透传给 LLM

    def __post_init__(self):
        # 向后兼容：messages 为 None 时走旧路径，仍需校验 system 和 user
        if self.messages is None:
            if not self.user or not self.user.strip():
                raise ValueError("User message cannot be empty")
            if not self.system or not self.system.strip():
                raise ValueError("System message cannot be empty")

    def to_messages(self) -> List[Dict[str, Any]]:
        """转换为消息列表格式

        优先使用 messages 多轮数组，回退到 system + user 拼接。
        """
        if self.messages:
            result = []
            for m in self.messages:
                msg = {"role": m.role, "content": m.content}
                if m.tool_call_id:
                    msg["tool_call_id"] = m.tool_call_id
                if m.tool_calls:
                    msg["tool_calls"] = [
                        {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                        for tc in m.tool_calls
                    ]
                result.append(msg)
            return result
        # 旧路径：system + user
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
