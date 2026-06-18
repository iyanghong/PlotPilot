from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Optional
from domain.ai.value_objects.prompt import Prompt
from domain.ai.value_objects.token_usage import TokenUsage


DEFAULT_MAX_OUTPUT_TOKENS = 120000


class GenerationConfig:
    """生成配置"""
    def __init__(
        self,
        model: str = "",
        max_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
        temperature: float = 1.0,
        response_format: Optional[Dict] = None,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.response_format = response_format
        self.__post_init__()

    def __post_init__(self):
        """验证配置参数"""
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError("Temperature must be between 0.0 and 2.0")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be greater than 0")
        self.max_tokens = max(int(self.max_tokens), DEFAULT_MAX_OUTPUT_TOKENS)


class GenerationResult:
    """生成结果 — 支持文本回复和工具调用"""
    def __init__(
        self,
        content: str,
        token_usage: TokenUsage,
        tool_calls: list = None,
        finish_reason: str = "stop",
    ):
        self.content = content or ""
        self.token_usage = token_usage
        self.tool_calls = tool_calls or []
        self.finish_reason = finish_reason
        self.__post_init__()

    def __post_init__(self):
        """验证结果参数 — tool_calls 与空 content 同时存在时跳过 content 检查"""
        has_tool_calls = bool(self.tool_calls)
        if not has_tool_calls and (not self.content or not self.content.strip()):
            raise ValueError("Content cannot be empty when no tool calls present")


class LLMService(ABC):
    """LLM 服务接口（领域服务）"""

    @abstractmethod
    async def generate(
        self,
        prompt: Prompt,
        config: GenerationConfig
    ) -> GenerationResult:
        """生成内容"""
        pass

    @abstractmethod
    async def stream_generate(
        self,
        prompt: Prompt,
        config: GenerationConfig
    ) -> AsyncIterator[str]:
        """流式生成内容"""
        pass
