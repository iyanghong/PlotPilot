# 灵感助手 Agent 化改造实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将灵感助手从平板文本+禁止提问的聊天机器人升级为多轮消息+工具调用+协作追问的智能体

**Architecture:** 在已有 DynamicLLMService 抽象层上直接扩展，不引入开源框架。DDD 从内向外：Domain 值对象 → Infrastructure 工具注册表 + Provider 扩展 → Application Agent 循环 + 策略重写 → Interface SSE 事件 → Frontend 气泡样式

**Tech Stack:** Python 3.14, FastAPI, Vue 3 + Naive UI, TypeScript, SQLite, Anthropic/OpenAI/Ark/Gemini SDK

## Global Constraints

- 不引入任何新的开源 Agent 框架（LangGraph、CrewAI 等）
- 灵感助手保持纯发散创意空间定位，`novel_id` 保持 `__preview__` 不绑定已有小说
- 保留两阶段流程：聊天 → 手动触发「生成字段」
- 用户主导节奏（C 类策略），Agent 偶尔追问
- `Prompt` 类向后兼容：`messages=None` 时走旧路径
- 所有代码注释使用中文

---

### Task 1: Domain — GenerationResult 扩展 + ToolCall/ToolDefinition 值对象

**Files:**
- Modify: `domain/ai/services/llm_service.py:34-43`
- Modify: `domain/ai/value_objects/prompt.py`（追加新类）

**Interfaces:**
- Produces: `ToolCall(id, name, arguments)`, `ToolDefinition(name, description, parameters)`, `GenerationResult(content, token_usage, tool_calls=[], finish_reason="stop")`

- [ ] **Step 1: 扩展 GenerationResult 支持 tool_calls**

在 `domain/ai/services/llm_service.py` 中修改 `GenerationResult.__init__`：

```python
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
```

- [ ] **Step 2: 在 prompt.py 追加 Message/ToolCall/ToolDefinition 值对象**

在 `domain/ai/value_objects/prompt.py` 末尾追加：

```python
from dataclasses import dataclass, field
from typing import Optional


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
    tool_calls: Optional[list[ToolCall]] = None
```

- [ ] **Step 3: 运行现有测试确认向后兼容**

Run: `pytest tests/unit/domain/ai/ -v -k "prompt or generation" 2>&1 | head -30`

- [ ] **Step 4: 提交**

```bash
git add domain/ai/services/llm_service.py domain/ai/value_objects/prompt.py
git commit -m "feat(domain): GenerationResult 支持 tool_calls，新增 Message/ToolCall/ToolDefinition 值对象"
```

---

### Task 2: Infrastructure — ToolRegistry 工具注册表

**Files:**
- Create: `infrastructure/ai/tool_registry.py`

**Interfaces:**
- Produces: `ToolRegistry.register(tool)`, `ToolRegistry.get_definitions() -> list[ToolDefinition]`, `ToolRegistry.execute(name, args) -> str`
- Consumes: `ToolDefinition` from Task 1

- [ ] **Step 1: 创建 ToolRegistry**

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add infrastructure/ai/tool_registry.py
git commit -m "feat(infra): 新增 ToolRegistry 工具注册表"
```

---

### Task 3: Infrastructure — AnthropicProvider 扩展 tool calling

**Files:**
- Modify: `infrastructure/ai/providers/anthropic_provider.py:132-195`

**Interfaces:**
- Consumes: `Prompt` with `messages` and `tools` fields from Task 1
- Produces: `GenerationResult` with `tool_calls` when LLM returns `tool_use` blocks

- [ ] **Step 1: 修改 AnthropicProvider.generate() 支持 messages + tools**

替换 `generate()` 方法中的请求构建部分（行 155-195）：

```python
async def generate(
    self, prompt: Prompt, config: GenerationConfig
) -> GenerationResult:
    try:
        model_id = require_resolved_model_id(
            config.model, self.settings.default_model,
            provider_label="Anthropic / Claude",
        )
        # 构建 messages — 优先使用多轮 messages 数组
        if prompt.messages:
            messages = [
                {"role": m.role, "content": m.content}
                for m in prompt.messages
            ]
        else:
            messages = [{"role": "user", "content": prompt.user}]

        create_kwargs = {
            "model": model_id,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "system": prompt.system,
            "messages": messages,
        }

        # 透传 tools 参数
        if prompt.tools:
            create_kwargs["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.parameters,
                }
                for t in prompt.tools
            ]

        if config.response_format:
            fmt = config.response_format
            instruction = _json_response_instruction(fmt)
            if instruction:
                create_kwargs["system"] = create_kwargs["system"] + instruction

        response = await self.async_client.messages.create(**create_kwargs)

        if not response.content:
            raise RuntimeError("API returned empty content")

        # 解析 content blocks — 区分 text 和 tool_use
        parts = []
        tool_calls = []
        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                tool_calls.append(ToolCall(
                    id=getattr(block, "id", ""),
                    name=getattr(block, "name", ""),
                    arguments=getattr(block, "input", {}),
                ))
            else:
                text = _extract_text_from_content_block(block)
                if text:
                    parts.append(text)

        content = "\n".join(p.strip() for p in parts if p and p.strip()).strip()

        if not content and not tool_calls:
            raise RuntimeError("API returned no text content and no tool calls")

        token_usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        return GenerationResult(
            content=content,
            token_usage=token_usage,
            tool_calls=tool_calls,
            finish_reason="tool_calls" if tool_calls else "stop",
        )

    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to generate text: {str(e)}") from e
```

- [ ] **Step 2: 添加缺少的 import**

在文件顶部添加 `ToolCall` 导入：

```python
from domain.ai.value_objects.prompt import Prompt, ToolCall
```

- [ ] **Step 3: 运行现有测试确认不破坏**

Run: `pytest tests/unit/infrastructure/ai/ -v -k "anthropic" 2>&1 | tail -15`

- [ ] **Step 4: 提交**

```bash
git add infrastructure/ai/providers/anthropic_provider.py
git commit -m "feat(infra): AnthropicProvider 支持多轮 messages + tools 参数透传"
```

---

### Task 4: Infrastructure — OpenAIProvider 扩展 tool calling

**Files:**
- Modify: `infrastructure/ai/providers/openai_provider.py`

**Interfaces:**
- Consumes: `Prompt` with `messages` and `tools` from Task 1
- Produces: `GenerationResult` with `tool_calls`

- [ ] **Step 1: 创建 `_build_messages` 辅助方法（兼容 messages + tools）**

在 `OpenAIProvider` 类中找到 `_build_messages` 方法，修改为：

```python
def _build_messages(self, prompt: Prompt) -> list[dict]:
    """构建 messages — 优先 Prompt.messages 数组，回退到 system + user"""
    if prompt.messages:
        msgs = []
        for m in prompt.messages:
            msg = {"role": m.role, "content": m.content}
            if m.tool_call_id:
                msg["tool_call_id"] = m.tool_call_id
            if m.tool_calls:
                msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments, ensure_ascii=False)},
                    }
                    for tc in m.tool_calls
                ]
            msgs.append(msg)
        return msgs
    return [{"role": "user", "content": prompt.user}]
```

- [ ] **Step 2: 修改 `_generate_via_chat()` 透传 tools 并解析 tool_calls**

在 `_generate_via_chat()` 的 `create_kwargs` 构建处追加：

```python
# 透传 tools（在 messages 构建之后）
if prompt.tools:
    create_kwargs["tools"] = [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in prompt.tools
    ]
    create_kwargs["tool_choice"] = "auto"
```

在解析 response 处追加 tool_calls 提取：

```python
# 提取 tool_calls
tool_calls = []
if hasattr(response.choices[0].message, "tool_calls") and response.choices[0].message.tool_calls:
    import json
    for tc in response.choices[0].message.tool_calls:
        try:
            args = json.loads(tc.function.arguments)
        except json.JSONDecodeError:
            args = {}
        tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))
```

最终 `GenerationResult` 构建改为：

```python
return GenerationResult(
    content=content,
    token_usage=token_usage,
    tool_calls=tool_calls,
    finish_reason="tool_calls" if tool_calls else "stop",
)
```

- [ ] **Step 3: 添加 ToolCall import**

```python
from domain.ai.value_objects.prompt import Prompt, ToolCall
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/unit/infrastructure/ai/ -v -k "openai" 2>&1 | tail -15`

- [ ] **Step 5: 提交**

```bash
git add infrastructure/ai/providers/openai_provider.py
git commit -m "feat(infra): OpenAIProvider 支持多轮 messages + tools 透传和 tool_calls 解析"
```

---

### Task 5: Infrastructure — ArkProvider + GeminiProvider tool calling

**Files:**
- Modify: `infrastructure/ai/providers/ark_provider.py`
- Modify: `infrastructure/ai/providers/gemini_provider.py`

**Interfaces:**
- Consumes: `Prompt.messages` and `Prompt.tools` from Task 1
- Produces: `GenerationResult.tool_calls`

- [ ] **Step 1: ArkProvider — openai 兼容协议，复用 OpenAIProvider 的 tools 透传逻辑**

ArkProvider 继承或内联了 openai SDK。参照 Task 4 的改动，在 `_build_messages` 和 `generate()` 中透传 tools：

1. `_build_messages` 修改为优先 `prompt.messages` 数组，回退 `prompt.user`
2. `create_kwargs` 追加 `tools` 和 `tool_choice`
3. response 解析追加 `tool_calls` 提取
4. `GenerationResult` 追加 `tool_calls` 和 `finish_reason`

- [ ] **Step 2: GeminiProvider — tools 参数透传**

Gemini SDK 使用 `tools` 参数，格式不同：

```python
if prompt.tools:
    create_kwargs["tools"] = [
        {
            "function_declarations": [
                {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                }
                for t in prompt.tools
            ]
        }
    ]
```

解析 `function_call` 为统一 `ToolCall`：

```python
tool_calls = []
for part in response.candidates[0].content.parts:
    if hasattr(part, "function_call") and part.function_call:
        fc = part.function_call
        tool_calls.append(ToolCall(
            id=f"{fc.name}_{uuid.uuid4().hex[:8]}",
            name=fc.name,
            arguments=dict(fc.args) if fc.args else {},
        ))
```

- [ ] **Step 3: 提交**

```bash
git add infrastructure/ai/providers/ark_provider.py infrastructure/ai/providers/gemini_provider.py
git commit -m "feat(infra): ArkProvider + GeminiProvider 支持 tools 参数透传"
```

---

### Task 6: Infrastructure — LLMClient.generate_with_tools()

**Files:**
- Modify: `infrastructure/ai/llm_client.py`

**Interfaces:**
- Produces: `LLMClient.generate_with_tools(messages, tools) -> GenerationResult`
- Consumes: `Message`, `ToolDefinition` from Task 1, Provider tool calling from Tasks 3-5

- [ ] **Step 1: 在 LLMClient 新增 generate_with_tools 方法**

```python
from domain.ai.value_objects.prompt import Prompt, Message, ToolDefinition
from domain.ai.services.llm_service import GenerationResult


class LLMClient:
    # ... existing methods ...

    async def generate_with_tools(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] = None,
        **kwargs,
    ) -> GenerationResult:
        """使用工具调用生成 — Agent 循环的核心入口

        Args:
            messages: 完整的多轮消息数组（含 system prompt）
            tools: 可用工具定义列表
            **kwargs: model, max_tokens, temperature

        Returns:
            GenerationResult（content 为空且 tool_calls 非空表示 LLM 要调工具）
        """
        config = self._build_config(**kwargs)
        system = ""
        # 从 messages 中提取 system 消息
        if messages and messages[0].role == "system":
            system = messages[0].content

        prompt = Prompt(
            system=system,
            user="",
            messages=messages,
            tools=tools or [],
        )
        return await self.provider.generate(prompt, config)
```

- [ ] **Step 2: 运行快速验证**

Run: `python -c "from infrastructure.ai.llm_client import LLMClient; print('OK')"`

- [ ] **Step 3: 提交**

```bash
git add infrastructure/ai/llm_client.py
git commit -m "feat(infra): LLMClient 新增 generate_with_tools() Agent 入口"
```

---

### Task 7: Application — lookup_genre 工具

**Files:**
- Create: `application/assist/tools/__init__.py`
- Create: `application/assist/tools/lookup_genre.py`

**Interfaces:**
- Produces: `register_assist_tools(registry)` — 注册到 ToolRegistry
- Consumes: `_load_taxonomy_lookup()` from `assist_service.py`

- [ ] **Step 1: 创建 lookup_genre.py**

```python
"""根据关键词搜索类型模板 — 灵感助手首批工具 — 作者：Axelton"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from functools import lru_cache

import yaml

logger = logging.getLogger(__name__)

_TAXONOMY_YAML_PATH = (
    Path(__file__).resolve().parents[4] / "shared" / "taxonomy" / "builtin_cn_v1.yaml"
)


@lru_cache(maxsize=1)
def _load_lookup() -> dict[str, dict[str, str]]:
    """加载 taxonomy 并构建扁平查找表（模块级缓存）"""
    if not _TAXONOMY_YAML_PATH.is_file():
        logger.warning("taxonomy 文件不存在: %s", _TAXONOMY_YAML_PATH)
        return {}

    raw = yaml.safe_load(_TAXONOMY_YAML_PATH.read_text(encoding="utf-8"))
    lookup: dict[str, dict[str, str]] = {}

    for root in raw.get("roots", []):
        root_label = root.get("labels", {}).get("zh-CN", "").strip()
        facets = root.get("facets", {})
        root_wt = facets.get("world_tone", "")
        wp = facets.get("writing_profile", {})
        entry = {
            "world_tone": root_wt,
            "story_structure": wp.get("story_structure", ""),
            "pacing_control": wp.get("pacing_control", ""),
            "writing_style": wp.get("writing_style", ""),
            "special_requirements": wp.get("special_requirements", ""),
        }
        if root_label:
            lookup[root_label] = entry

        for child in root.get("children", []):
            child_label = child.get("labels", {}).get("zh-CN", "").strip()
            child_facets = child.get("facets", {})
            child_wt = child_facets.get("world_tone", "") or root_wt
            child_wp = child_facets.get("writing_profile", {})
            child_entry = {
                "world_tone": child_wt,
                "story_structure": child_wp.get("story_structure", "") or wp.get("story_structure", ""),
                "pacing_control": child_wp.get("pacing_control", "") or wp.get("pacing_control", ""),
                "writing_style": child_wp.get("writing_style", "") or wp.get("writing_style", ""),
                "special_requirements": child_wp.get("special_requirements", "") or wp.get("special_requirements", ""),
            }
            if child_label:
                lookup[child_label] = child_entry

    logger.info("lookup_genre: 已加载 %d 个类型模板", len(lookup))
    return lookup


async def lookup_genre_templates(genre_keyword: str) -> str:
    """搜索 builtin_cn_v1.yaml 中匹配的类型写作模板

    返回该类型的世界观基调和四个写作画像字段，
    作为 Agent 展开创意建议的参考框架。
    """
    lookup = _load_lookup()
    if not lookup:
        return "未找到类型模板数据，请基于通用的写作知识给出建议。"

    keyword = genre_keyword.strip()

    # 精确匹配
    if keyword in lookup:
        entry = lookup[keyword]
        return _format_entry(keyword, entry)

    # 模糊匹配：关键词包含在标签中，或标签包含关键词
    candidates = []
    for label in lookup:
        if keyword in label or label in keyword:
            candidates.append((len(label), label))

    if not candidates:
        return (
            f"未找到「{keyword}」的精确类型模板。"
            f"可用的类型包括：{', '.join(sorted(lookup.keys())[:20])}..."
        )

    # 取最长匹配（最具体）的标签
    candidates.sort(reverse=True)
    label = candidates[0][1]
    entry = lookup[label]
    return _format_entry(label, entry)


def _format_entry(label: str, entry: dict[str, str]) -> str:
    """格式化模板为文本"""
    lines = [f"【{label}】类型写作模板："]
    if entry.get("world_tone"):
        lines.append(f"世界观基调：{entry['world_tone']}")
    if entry.get("story_structure"):
        lines.append(f"剧情结构：{entry['story_structure']}")
    if entry.get("pacing_control"):
        lines.append(f"节奏把控：{entry['pacing_control']}")
    if entry.get("writing_style"):
        lines.append(f"写作风格：{entry['writing_style']}")
    if entry.get("special_requirements"):
        lines.append(f"特殊要求：{entry['special_requirements']}")
    return "\n".join(lines)
```

- [ ] **Step 2: 创建 tools/__init__.py**

```python
"""灵感助手工具包 — 作者：Axelton"""
from infrastructure.ai.tool_registry import ToolRegistry, Tool

from .lookup_genre import lookup_genre_templates


def register_assist_tools(registry: ToolRegistry) -> None:
    """将灵感助手工具注册到全局注册表"""
    registry.register(Tool(
        name="lookup_genre_templates",
        description="搜索小说类型的写作模板。当用户提到具体类型（末世、玄幻、悬疑、科幻等）时调用，获取该类型的世界观基调和写作画像作为建议参考。",
        parameters={
            "type": "object",
            "properties": {
                "genre_keyword": {
                    "type": "string",
                    "description": "用户提到的类型关键词，如「末世」「玄幻」「悬疑」「科幻」",
                },
            },
            "required": ["genre_keyword"],
        },
        handler=lambda args: lookup_genre_templates(args["genre_keyword"]),
    ))
```

- [ ] **Step 3: 提交**

```bash
git add application/assist/tools/
git commit -m "feat(assist): 新增 lookup_genre_templates 工具（首批 Agent 工具）"
```

---

### Task 8: Application — 策略 Prompt 重写

**Files:**
- Modify: `application/assist/strategies/base.py`
- Modify: `application/assist/strategies/brainstorm.py`
- Modify: `application/assist/strategies/world_first.py`
- Modify: `application/assist/strategies/character_driven.py`
- Modify: `application/assist/strategies/theme_first.py`

**Interfaces:**
- Produces: `BaseInspirationStrategy.build_agent_system_prompt()` — 新增抽象方法
- Removes: 所有「绝对禁止提问」相关指令

- [ ] **Step 1: base.py 新增抽象方法**

```python
@abstractmethod
def build_agent_system_prompt(self) -> str:
    """构建 Agent 系统提示词 — 多轮协作式对话框架"""
    ...
```

- [ ] **Step 2: brainstorm.py 重写 prompt**

```python
def build_system_prompt(self) -> str:
    # 保留旧接口兼容性，委托给 agent prompt
    return self.build_agent_system_prompt()

def build_agent_system_prompt(self) -> str:
    return (
        "你是一个创意写作伙伴，擅长根据用户的碎片想法展开联想、"
        "构建完整的故事框架。\n\n"
        "对话节奏：\n"
        "- 用户引领方向，你跟随并展开联想分析，给出具体的世界观、人物、冲突建议\n"
        "- 如果用户信息很少，大胆推测并给出完整方案\n"
        "- 每次回复末尾最多追问一句来澄清关键方向，但仅限一句\n"
        "- 语言轻松日常，像作家朋友在咖啡馆聊灵感\n\n"
        "工具使用：\n"
        "- 当用户提到具体类型时（如「末世」「玄幻」「悬疑」），"
        "调用 lookup_genre_templates 获取该类型的写作模板作为参考\n\n"
        "用中文回复。"
    )
```

- [ ] **Step 3: world_first.py 重写 prompt**

```python
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
```

- [ ] **Step 4: character_driven.py 重写 prompt**

```python
def build_agent_system_prompt(self) -> str:
    return (
        "你是一个角色驱动的故事开发助手，擅长从人物出发构建故事。\n\n"
        "对话节奏：\n"
        "- 分析角色的欲望、恐惧、缺陷、关系网\n"
        "- 从角色推导出故事冲突和世界观基调\n"
        "- 每次回复末尾最多追问一句来澄清关键方向\n\n"
        "工具使用：\n"
        "- 当用户提到具体类型时，调用 lookup_genre_templates 获取模板\n\n"
        "用中文回复。"
    )
```

- [ ] **Step 5: theme_first.py 重写 prompt**

```python
def build_agent_system_prompt(self) -> str:
    return (
        "你是一个主题驱动的故事开发助手，擅长将抽象主题具象化为故事框架。\n\n"
        "对话节奏：\n"
        "- 分析主题的切面、对立面和载体\n"
        "- 找到具象化的故事外壳和叙事结构\n"
        "- 每次回复末尾最多追问一句来澄清关键方向\n\n"
        "工具使用：\n"
        "- 当用户提到具体类型时，调用 lookup_genre_templates 获取模板\n\n"
        "用中文回复。"
    )
```

- [ ] **Step 6: 提交**

```bash
git add application/assist/strategies/
git commit -m "feat(assist): 策略 prompt 重写为 Agent 协作式（去禁止提问，加工具指引）"
```

---

### Task 9: Application — AssistService.chat() 重写为 Agent 循环

**Files:**
- Modify: `application/assist/assist_service.py`

**Interfaces:**
- Consumes: `Message` from Task 1, `ToolRegistry` from Task 2, `LLMClient.generate_with_tools()` from Task 6, strategies from Task 8, `register_assist_tools` from Task 7
- Produces: Agent 循环 SSE 事件流

- [ ] **Step 1: 修改 AssistService 初始化，注册工具**

在 `__init__` 末尾追加：

```python
# 注册灵感助手工具到全局注册表
from infrastructure.ai.tool_registry import get_tool_registry
from application.assist.tools import register_assist_tools
register_assist_tools(get_tool_registry())
```

- [ ] **Step 2: 重写 chat() 为 Agent 循环**

替换现有的 `chat()` 方法（行 220-275）：

```python
async def chat(
    self, session: InspireSession, user_message: str,
) -> AsyncIterator[dict]:
    """Agent 循环 — 多轮消息 + 工具调用 + 流式输出

    Yields:
        dict: {"type": "chat_chunk", "content": "..."}
              {"type": "tool_call", "name": "...", "args": {...}}
              {"type": "tool_result", "name": "...", "summary": "..."}
              {"type": "chat_done", "message_type": "question"|"suggestion"}
    """
    from infrastructure.ai.tool_registry import get_tool_registry

    # 1. 保存用户消息
    user_msg = InspireMessage(
        id=f"msg_{uuid.uuid4().hex[:12]}",
        session_id=session.id,
        role="user",
        content=user_message,
    )
    await self._repo.add_message(user_msg)

    # 2. 构建多轮消息数组
    history = await self._repo.get_messages(session.id)
    strategy = _get_strategy(session.strategy.value)
    tool_registry = get_tool_registry()
    tool_defs = tool_registry.get_definitions()

    messages = [Message(role="system", content=strategy.build_agent_system_prompt())]
    for m in history:
        messages.append(Message(role=m.role, content=m.content))

    # 3. Agent 循环
    full_content = ""
    tool_call_count = 0

    for _ in range(5):
        result = await self._llm.generate_with_tools(messages, tool_defs)

        # 分支 A：LLM 要调工具
        if result.tool_calls:
            for tc in result.tool_calls:
                tool_call_count += 1
                if tool_call_count > 3:
                    break

                yield {"type": "tool_call", "name": tc.name, "args": tc.arguments}

                tool_result = await tool_registry.execute(tc.name, tc.arguments)
                summary = tool_result[:200]

                yield {"type": "tool_result", "name": tc.name, "summary": summary}

                # 追加 assistant tool_call 消息
                messages.append(Message(
                    role="assistant", content="",
                    tool_calls=[tc],
                ))
                # 追加 tool result 消息
                messages.append(Message(
                    role="tool", content=tool_result,
                    tool_call_id=tc.id,
                ))
            if tool_call_count > 3:
                # 超出工具调用上限，将剩余 token 留给纯文本回复
                continue
            continue

        # 分支 B：LLM 给出文本回复 — 流式输出
        # 构建不含 tools 的 prompt 用于流式
        stream_prompt = Prompt(
            system="", user="", messages=messages, tools=None,
        )
        async for chunk in self._llm.stream_generate(stream_prompt):
            full_content += chunk
            yield {"type": "chat_chunk", "content": chunk}

        break

    # 4. 保存 AI 回复
    if full_content:
        ai_msg = InspireMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            session_id=session.id,
            role="assistant",
            content=full_content,
        )
        await self._repo.add_message(ai_msg)

    # 5. 判断消息类型
    is_question = full_content.strip().endswith("？") or full_content.strip().endswith("?")
    yield {"type": "chat_done", "message_type": "question" if is_question else "suggestion"}
```

- [ ] **Step 3: 添加 Message import**

```python
from domain.ai.value_objects.prompt import Prompt, Message
```

- [ ] **Step 4: 运行现有测试**

Run: `pytest tests/unit/application/assist/ -v 2>&1 | tail -15`

- [ ] **Step 5: 提交**

```bash
git add application/assist/assist_service.py
git commit -m "feat(assist): chat() 重写为 Agent 循环（多轮消息 + 工具调用 + 流式输出）"
```

---

### Task 10: Interface — inspire_routes.py SSE 事件扩展

**Files:**
- Modify: `interfaces/api/v1/assist/inspire_routes.py`

**Interfaces:**
- Consumes: `AssistService.chat()` 新的 dict 事件流（从 Task 9）
- Produces: SSE 事件 `tool_call`, `tool_result`, `chat_done` 带 `message_type`

- [ ] **Step 1: 修改 _event_gen 中 action="chat" 的处理**

替换行 68-80：

```python
if req.action == "chat":
    if not req.message:
        yield f"data: {json.dumps({'error': 'message 不能为空'})}\n\n"
        return

    async for event in service.chat(session, req.message):
        if await request.is_disconnected():
            break

        event_type = event["type"]

        if event_type == "chat_chunk":
            yield f"event: chat_chunk\ndata: {json.dumps({'content': event['content']})}\n\n"

        elif event_type == "tool_call":
            yield f"event: tool_call\ndata: {json.dumps({'name': event['name'], 'args': event['args']}, ensure_ascii=False)}\n\n"

        elif event_type == "tool_result":
            yield f"event: tool_result\ndata: {json.dumps({'name': event['name'], 'summary': event['summary']}, ensure_ascii=False)}\n\n"

        elif event_type == "chat_done":
            yield f"event: chat_done\ndata: {json.dumps({'message_type': event['message_type']})}\n\n"
```

- [ ] **Step 2: 运行快速语法检查**

Run: `python -c "from interfaces.api.v1.assist.inspire_routes import router; print('OK')"`

- [ ] **Step 3: 提交**

```bash
git add interfaces/api/v1/assist/inspire_routes.py
git commit -m "feat(interface): SSE 新增 tool_call/tool_result 事件，chat_done 带 message_type"
```

---

### Task 11: Frontend — assist.ts 接口扩展

**Files:**
- Modify: `frontend/src/api/assist.ts`

- [ ] **Step 1: 扩展 AssistChatHandlers 接口 + SSE 事件解析**

```typescript
/** 灵感助手 API 封装 — Agent 版 SSE 流式消费 — 作者：Axelton */
import { resolveHttpUrl } from './config'

// ... 保留现有 interface 定义 ...

export interface AssistChatHandlers {
  onSessionCreated?: (info: AssistSessionInfo) => void
  onChatChunk?: (content: string) => void
  onChatDone?: (messageType: 'question' | 'suggestion') => void
  onFieldsDone?: (fields: AssistFieldData) => void
  onResumeDone?: (data: AssistResumeData) => void
  onToolCall?: (name: string, args: Record<string, unknown>) => void
  onToolResult?: (name: string, summary: string) => void
  onConnected?: () => void
  onDisconnected?: () => void
  onStreamEnd?: () => void
  onError?: (error: string) => void
}
```

- [ ] **Step 2: 在 flushBlocks 中新增 event 处理**

在 `switch (eventType)` 块中追加：

```typescript
case 'tool_call':
  handlers.onToolCall?.(payload.name || '', payload.args || {})
  break
case 'tool_result':
  handlers.onToolResult?.(payload.name || '', payload.summary || '')
  break
```

修改 `chat_done` 的处理：

```typescript
case 'chat_done':
  handlers.onChatDone?.(payload.message_type || 'suggestion')
  break
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/api/assist.ts
git commit -m "feat(frontend): assist.ts 扩展 tool_call/tool_result 事件和 message_type 回调"
```

---

### Task 12: Frontend — InspirationAssistantModal.vue 气泡 + 工具状态条

**Files:**
- Modify: `frontend/src/components/inspiration/InspirationAssistantModal.vue`

- [ ] **Step 1: 在 template 中添加工具状态条**

在 `assist-chat` div 顶部（空状态指南上方）加入：

```html
<!-- 工具调用状态条 -->
<Transition name="slide-fade">
  <div v-if="toolStatus.show" class="tool-status-bar" :class="`tool-status-${toolStatus.type}`">
    <span class="tool-status-icon">{{ toolStatus.type === 'info' ? '🔍' : '✅' }}</span>
    <span class="tool-status-text">{{ toolStatus.text }}</span>
  </div>
</Transition>
```

- [ ] **Step 2: 气泡样式区分追问 vs 建议**

修改 `.chat-bubble` 模板部分，按 message_type 设置 CSS 类：

```html
<div
  v-for="msg in messages"
  :key="msg.id"
  class="chat-message"
  :class="`chat-${msg.role}`"
>
  <div class="chat-avatar">
    {{ msg.role === 'user' ? '😀' : msg.messageType === 'question' ? '🤔' : '💡' }}
  </div>
  <div
    class="chat-bubble"
    :class="msg.role === 'assistant' && msg.messageType === 'question' ? 'bubble-question' : 'bubble-suggestion'"
  >
    {{ msg.content }}
  </div>
</div>
```

- [ ] **Step 3: 扩展 script 中的消息处理逻辑**

在 script setup 中新增：

```typescript
// 工具状态
const toolStatus = reactive({
  show: false,
  text: '',
  type: 'info' as 'info' | 'success',
})

let toolTimer: ReturnType<typeof setTimeout> | null = null

function showToolCall(name: string, args: Record<string, unknown>) {
  if (toolTimer) clearTimeout(toolTimer)
  const keyword = (args.genre_keyword as string) || ''
  toolStatus.show = true
  toolStatus.text = keyword ? `正在查找「${keyword}」类型写作模板…` : `正在查找灵感素材…`
  toolStatus.type = 'info'
}

function showToolResult(name: string, summary: string) {
  if (toolTimer) clearTimeout(toolTimer)
  toolStatus.text = `已参考类型模板`
  toolStatus.type = 'success'
  toolTimer = setTimeout(() => {
    toolStatus.show = false
  }, 1500)
}
```

- [ ] **Step 4: 扩展 AssistMessage 本地类型**

```typescript
// 扩展本地消息类型
interface LocalMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  messageType?: 'question' | 'suggestion'
  created_at: string
}
```

- [ ] **Step 5: 修改 handleSend 中的回调**

```typescript
onChatDone(messageType) {
  if (streamingContent.value) {
    messages.value.push({
      id: `ai_${Date.now()}`,
      role: 'assistant',
      content: streamingContent.value,
      messageType: messageType,
      created_at: new Date().toISOString(),
    })
  }
  streamingContent.value = ''
  sending.value = false
  autoGenerateFields()
},
onToolCall(name, args) {
  showToolCall(name, args)
},
onToolResult(name, summary) {
  showToolResult(name, summary)
},
```

- [ ] **Step 6: 添加 CSS**

在 `<style scoped>` 末尾追加：

```css
/* 追问气泡 — 琥珀/浅黄底 */
.bubble-question {
  background: rgba(245, 158, 11, 0.08) !important;
  border-left: 3px solid #f59e0b;
}

/* 建议气泡 — 默认灰底（无需额外样式） */
.bubble-suggestion {
  /* 继承 chat-bubble 默认样式 */
}

/* 工具状态条 */
.tool-status-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
  margin-bottom: 4px;
}
.tool-status-info {
  background: rgba(59, 130, 246, 0.08);
  color: var(--app-text-secondary);
}
.tool-status-success {
  background: rgba(34, 197, 94, 0.08);
  color: var(--app-text-secondary);
}
.tool-status-icon {
  flex-shrink: 0;
}

/* 滑入/滑出动画 */
.slide-fade-enter-active {
  transition: all 0.3s ease;
}
.slide-fade-leave-active {
  transition: all 0.3s ease;
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateY(-10px);
  opacity: 0;
}
```

- [ ] **Step 7: 运行前端类型检查**

Run: `cd frontend && npx vue-tsc --noEmit 2>&1 | tail -10`

- [ ] **Step 8: 提交**

```bash
git add frontend/src/components/inspiration/InspirationAssistantModal.vue
git commit -m "feat(frontend): 灵感助手区分追问/建议气泡 + 工具调用状态条动画"
```

---

### Task 13: 集成验证

- [ ] **Step 1: 运行完整后端测试套件**

Run: `pytest tests/unit/ -v --ignore=tests/integration 2>&1 | tail -20`
Expected: 所有测试通过（与改造前相同数量）

- [ ] **Step 2: 运行 Python import 完整性检查**

Run: `python -c "
from domain.ai.value_objects.prompt import Prompt, Message, ToolCall, ToolDefinition
from domain.ai.services.llm_service import GenerationResult
from infrastructure.ai.tool_registry import ToolRegistry, get_tool_registry
from infrastructure.ai.llm_client import LLMClient
from application.assist.tools import register_assist_tools
from application.assist.assist_service import AssistService
print('All imports OK')
"`

- [ ] **Step 3: 启动后端服务验证启动无报错**

Run: `timeout 5 python cli.py serve 2>&1 || true`
Expected: 服务正常启动，无 import error 或 500 error

- [ ] **Step 4: 提交最终状态**

```bash
git add -A
git status
git diff --cached --stat
git commit -m "chore: 灵感助手 Agent 化改造 — 集成验证通过"
```
