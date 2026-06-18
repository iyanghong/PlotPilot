"""LLM 客户端包装器"""
from typing import AsyncIterator

from domain.ai.services.llm_service import DEFAULT_MAX_OUTPUT_TOKENS, GenerationConfig, GenerationResult
from domain.ai.value_objects.prompt import Prompt, Message, ToolDefinition
from infrastructure.ai.provider_factory import DynamicLLMService


class LLMClient:
    """LLM 客户端包装器，自动选择当前激活的提供者。"""

    def __init__(self, provider=None):
        """初始化 LLM 客户端

        Args:
            provider: 可选的 LLM 提供者实例。如果未提供，将自动创建。
        """
        self.provider = provider or DynamicLLMService()

    def _build_config(self, **kwargs) -> GenerationConfig:
        settings = getattr(self.provider, "settings", None)
        return GenerationConfig(
            model=kwargs.get("model", getattr(settings, "default_model", None)),
            max_tokens=kwargs.get("max_tokens", getattr(settings, "default_max_tokens", DEFAULT_MAX_OUTPUT_TOKENS)),
            temperature=kwargs.get("temperature", getattr(settings, "default_temperature", 1.0)),
        )

    async def generate(self, prompt: str, **kwargs) -> str:
        """生成文本

        Args:
            prompt: 提示词字符串
            **kwargs: 其他参数（model, max_tokens, temperature等）

        Returns:
            生成的文本
        """
        # 创建 Prompt 对象
        prompt_obj = Prompt(
            system="你是一个专业的小说创作助手。",
            user=prompt
        )

        config = self._build_config(**kwargs)

        # 调用 provider
        result = await self.provider.generate(prompt_obj, config)
        return result.content

    async def stream_generate(
        self,
        prompt,          # Prompt 对象或 str
        config=None,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式生成，代理到底层 provider"""
        # 如果是字符串，转换为 Prompt 对象
        if isinstance(prompt, str):
            prompt_obj = Prompt(
                system="你是一个专业的小说创作助手。",
                user=prompt
            )
        else:
            prompt_obj = prompt

        # 如果没有提供 config，创建默认配置
        if config is None:
            config = self._build_config(**kwargs)

        # 流式生成
        async for chunk in self.provider.stream_generate(prompt_obj, config):
            yield chunk

    async def generate_with_tools(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] = None,
        **kwargs,
    ) -> GenerationResult:
        """使用工具调用生成 — Agent 循环的核心入口

        Args:
            messages: 完整的多轮消息数组（第一应为 system 消息）
            tools: 可用工具定义列表
            **kwargs: model, max_tokens, temperature

        Returns:
            GenerationResult（content 为空且 tool_calls 非空表示 LLM 要调用工具）
        """
        config = self._build_config(**kwargs)
        # 从 messages 中提取 system 消息
        system = ""
        if messages and messages[0].role == "system":
            system = messages[0].content

        prompt = Prompt(
            system=system,
            user="",
            messages=messages,
            tools=tools or [],
        )
        return await self.provider.generate(prompt, config)
