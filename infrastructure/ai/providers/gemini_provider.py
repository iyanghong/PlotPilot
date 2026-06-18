"""Gemini LLM 提供商实现（官方 generateContent / streamGenerateContent 协议，支持多轮 messages 和工具调用）"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, AsyncIterator

import httpx

from domain.ai.services.llm_service import GenerationConfig, GenerationResult
from domain.ai.value_objects.prompt import Prompt, ToolCall
from domain.ai.value_objects.token_usage import TokenUsage
from infrastructure.ai.config.settings import Settings
from infrastructure.ai.http_timeout import build_httpx_timeout
from .base import BaseProvider
from .model_resolution import require_resolved_model_id

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta'


class GeminiProvider(BaseProvider):
    def __init__(self, settings: Settings):
        super().__init__(settings)
        if not settings.api_key:
            raise ValueError('API key is required for GeminiProvider')
        self.base_url = (settings.base_url or DEFAULT_BASE_URL).rstrip('/')
        # 长生命周期 httpx client（跨请求复用连接池）
        self._http_client = httpx.AsyncClient(
            timeout=build_httpx_timeout(settings.http_timeout_settings),
            trust_env=False,
        )

    async def generate(self, prompt: Prompt, config: GenerationConfig) -> GenerationResult:
        model_id = require_resolved_model_id(
            config.model,
            self.settings.default_model,
            provider_label="Gemini",
        )
        payload = self._build_payload(prompt, config)
        query = self._build_query()
        url = self._build_url(model_id, 'generateContent')

        response = await self._http_client.post(
            url,
            params=query,
            headers=self._build_headers(stream=False),
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        content, tool_calls = self._extract_response(data)
        if not content.strip() and not tool_calls:
            raise RuntimeError('Gemini returned empty content and no tool calls')

        usage = data.get('usageMetadata') or {}
        token_usage = TokenUsage(
            input_tokens=int(usage.get('promptTokenCount') or 0),
            output_tokens=int(usage.get('candidatesTokenCount') or 0),
        )
        return GenerationResult(
            content=content,
            token_usage=token_usage,
            tool_calls=tool_calls,
            finish_reason="tool_calls" if tool_calls else "stop",
        )

    async def stream_generate(self, prompt: Prompt, config: GenerationConfig) -> AsyncIterator[str]:
        model_id = require_resolved_model_id(
            config.model,
            self.settings.default_model,
            provider_label="Gemini",
        )
        payload = self._build_payload(prompt, config)
        query = self._build_query({'alt': 'sse'})
        url = self._build_url(model_id, 'streamGenerateContent')

        async with self._http_client.stream(
            'POST',
            url,
            params=query,
            headers=self._build_headers(stream=True),
            json=payload,
        ) as response:
            response.raise_for_status()
            buffer = ''
            async for chunk in response.aiter_text():
                buffer += chunk.replace('\r\n', '\n')
                while '\n\n' in buffer:
                    event_text, buffer = buffer.split('\n\n', 1)
                    text = self._parse_sse_event(event_text)
                    if text:
                        yield text

    def _build_url(self, model: str, action: str) -> str:
        model_name = model.strip()
        if not model_name:
            raise ValueError('Gemini: 构建请求 URL 时模型名为空')
        return f'{self.base_url}/models/{model_name}:{action}'

    def _build_query(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        query: dict[str, Any] = {'key': self.settings.api_key}
        query.update(self.settings.extra_query or {})
        if extra:
            query.update(extra)
        return query

    def _build_headers(self, *, stream: bool) -> dict[str, str]:
        headers = {'Content-Type': 'application/json'}
        if stream:
            headers['Accept'] = 'text/event-stream'
        headers.update(self.settings.extra_headers or {})
        return headers

    def _build_payload(self, prompt: Prompt, config: GenerationConfig) -> dict[str, Any]:
        generation_config = {
            'temperature': config.temperature,
            'maxOutputTokens': config.max_tokens,
        }
        # 🔥 response_format 自适应：
        # Gemini 支持 responseMimeType 但不支持 json_schema 结构定义
        # OpenAI 的 json_object → Gemini 的 responseMimeType: application/json
        # OpenAI 的 json_schema → Gemini 的 responseMimeType + responseSchema
        if config.response_format:
            fmt = config.response_format
            if fmt.get("type") == "json_object":
                generation_config["responseMimeType"] = "application/json"
            elif fmt.get("type") == "json_schema":
                generation_config["responseMimeType"] = "application/json"
                # 如果 json_schema 中有 schema 定义，传递给 Gemini
                schema = fmt.get("json_schema", {}).get("schema")
                if schema:
                    generation_config["responseSchema"] = schema

        # 构建 contents — 优先多轮 messages 数组，回退到 prompt.user
        if prompt.messages:
            contents = []
            for m in prompt.messages:
                entry: dict[str, Any] = {"role": m.role, "parts": [{"text": m.content}]}
                # 将 assistant 的 tool_calls 转为 Gemini functionCall 格式
                if m.tool_calls:
                    entry["parts"] = [
                        {"functionCall": {"name": tc.name, "args": tc.arguments}}
                        for tc in m.tool_calls
                    ]
                # 将 tool 角色的回复转为 Gemini functionResponse 格式
                if m.role == "tool" and m.tool_call_id:
                    entry["parts"] = [{
                        "functionResponse": {
                            "name": m.tool_call_id.split("_")[0] if "_" in (m.tool_call_id or "") else "",
                            "response": {"result": m.content},
                        }
                    }]
                contents.append(entry)
        else:
            contents = [{"role": "user", "parts": [{"text": prompt.user}]}]

        payload: dict[str, Any] = {
            'contents': contents,
            'generationConfig': generation_config,
        }

        # 透传 tools 参数（Gemini functionDeclarations 格式）
        if prompt.tools:
            payload["tools"] = [{
                "functionDeclarations": [
                    {"name": t.name, "description": t.description, "parameters": t.parameters}
                    for t in prompt.tools
                ]
            }]
        if prompt.system.strip():
            payload['systemInstruction'] = {
                'parts': [{'text': prompt.system}],
            }
        extra_body = dict(self.settings.extra_body or {})
        generation_override = extra_body.pop('generationConfig', None)
        if isinstance(generation_override, dict):
            payload['generationConfig'].update(generation_override)
        payload.update(extra_body)
        return payload

    def _extract_response(self, data: dict[str, Any]) -> tuple[str, list[ToolCall]]:
        """从 Gemini 响应中提取文本和工具调用"""
        pieces: list[str] = []
        tool_calls: list[ToolCall] = []
        for candidate in data.get('candidates') or []:
            content = candidate.get('content') or {}
            for part in content.get('parts') or []:
                if part.get('thought') is True:
                    continue
                # functionCall → 统一 ToolCall 格式
                fc = part.get('functionCall')
                if fc:
                    tool_calls.append(ToolCall(
                        id=f"{fc.get('name', 'unknown')}_{uuid.uuid4().hex[:8]}",
                        name=fc.get('name', ''),
                        arguments=dict(fc.get('args') or {}),
                    ))
                    continue
                text = part.get('text')
                if text:
                    pieces.append(str(text))
        return ''.join(pieces), tool_calls

    def _extract_text(self, data: dict[str, Any]) -> str:
        """从 Gemini 响应中提取纯文本（向后兼容流式路径）"""
        text, _ = self._extract_response(data)
        return text

    def _parse_sse_event(self, event_text: str) -> str:
        data_lines: list[str] = []
        for line in event_text.splitlines():
            if line.startswith('data:'):
                data_lines.append(line[5:].strip())

        if not data_lines:
            return ''

        raw_payload = ''.join(data_lines).strip()
        if not raw_payload or raw_payload == '[DONE]':
            return ''

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            logger.debug('Gemini SSE parse skip: %s', raw_payload[:120])
            return ''

        if isinstance(payload, list):
            return ''.join(self._extract_text(item) for item in payload if isinstance(item, dict))
        if isinstance(payload, dict):
            return self._extract_text(payload)
        return ''
