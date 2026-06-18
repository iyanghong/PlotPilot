# 灵感助手 Agent 化改造设计文档

> 作者: Axelton | 日期: 2026-06-18 | 基于: 2026-06-14-inspiration-assistant-design.md

## 问题诊断

灵感助手上线后用户反馈「理解很有问题」。根因分析如下：

| # | 根因 | 位置 | 严重度 |
|---|------|------|--------|
| 1 | 多轮对话被 `_build_conversation_text()` 压成平板文本塞进单个 user prompt，模型失去角色边界和注意力锚定 | `assist_service.py:248` | 致命 |
| 2 | System prompt 中 `绝对禁止提问！` 把协作者变成瞎猜独白机器 | `brainstorm.py:21` | 致命 |
| 3 | `novel_id = "__preview__"` 硬编码，助手对用户写作上下文零感知（**保留**：灵感助手定位为纯发散空间，不绑定已有小说） | `Home.vue:455` | 有意为之 |
| 4 | 无工具调用能力，助手只能靠训练数据里的知识 | 架构缺失 | 高 |
| 5 | Prompt 类仅支持单 system + 单 user，无法表达多轮对话 | `domain/ai/value_objects/prompt.py` | 高 |
| 6 | 无 token 预算管理，对话历史无限增长 | `assist_service.py:248` | 中 |

## 改造目标

将灵感助手从「平板文本 + 禁止提问的聊天机器人」升级为「多轮消息 + 工具调用 + 协作式追问的智能体」。

- **不引入开源 Agent 框架** — 在已有 `DynamicLLMService` 抽象层上直接扩展
- **不改定位** — 灵感助手仍是纯发散创意空间，不绑定已有小说
- **保留两阶段流程** — 聊天 → 用户手动触发「生成字段」→ 提取结构化信息
- **用户主导节奏** — Agent 偶尔追问，不主动推进

---

## 架构设计

### 整体数据流（Agent 循环）

```
用户发送消息
  │
  ▼
AssistService.chat()
  │
  ├─ 1. 保存用户消息到 assist_messages
  ├─ 2. 加载完整历史，构建多轮 messages[] 数组
  │
  ▼
┌─ Agent 循环（max 5 轮）────────────┐
│                                    │
│  LLM.generate_with_tools(          │
│    messages,                       │
│    tools=[lookup_genre_templates]  │
│  )                                 │
│    │                               │
│    ├─ finish_reason = "tool_calls" │
│    │   → SSE: tool_call            │
│    │   → 执行工具                   │
│    │   → SSE: tool_result          │
│    │   → 追加 tool result 到 msg[] │
│    │   → continue（回到循环顶）     │
│    │                               │
│    └─ finish_reason = "stop"       │
│        → SSE: chat_chunk × N       │
│        → SSE: chat_done            │
│        → 保存 AI 回复到 DB          │
│        → break                     │
└────────────────────────────────────┘
```

### 跨层改动总览

```
domain/ai/
  value_objects/prompt.py          ★ 扩展 Message / ToolCall / ToolDefinition
  value_objects/generation_result.py ★ 新增
  services/llm_service.py           ☆ 扩展 generate 返回 tool_calls

infrastructure/ai/
  providers/*_provider.py           ☆ 各 Provider 透传 tools 参数
  tool_registry.py                  ★ 新增：工具注册表
  llm_client.py                     ☆ 新增 generate_with_tools()

application/assist/
  assist_service.py                 ★ chat() 重写为 Agent 循环
  strategies/base.py                ☆ 新增 build_agent_system_prompt()
  strategies/brainstorm.py          ★ 重写 prompt（去禁止提问）
  strategies/world_first.py         ★ 重写 prompt
  strategies/character_driven.py    ★ 重写 prompt
  strategies/theme_first.py         ★ 重写 prompt
  tools/                            ★ 新增：工具包
    __init__.py
    lookup_genre.py                 ★ 首个工具：查 taxonomy 模板

interfaces/api/v1/assist/
  inspire_routes.py                 ☆ SSE 事件新增 tool_call / tool_result

frontend/src/
  api/assist.ts                     ☆ 事件类型扩展
  components/inspiration/
    InspirationAssistantModal.vue    ★ 追问/建议气泡 + 工具状态条
```

★ 新建或重大重写 | ☆ 小幅修改

---

## Domain 层设计

### `Prompt` 值对象扩展

```python
# 现状：仅支持单 system + 单 user
@dataclass(frozen=True)
class Prompt:
    system: str
    user: str

# 改后：保留兼容的同时支持多轮消息 + 工具
@dataclass(frozen=True)
class Message:
    """单条消息"""
    role: str                      # "system" | "user" | "assistant" | "tool"
    content: str
    tool_call_id: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None

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
class Prompt:
    system: str
    user: str
    messages: Optional[list[Message]] = None   # 新增：多轮消息数组
    tools: Optional[list[ToolDefinition]] = None  # 新增：可用工具
```

`to_messages()` 已有，扩展为：当 `messages` 存在时直接用（`system`/`user` 可为空字符串），否则回退到 `[system, user]` 兼容路径。所有现有调用方无需修改。`Prompt` 构造增加校验：`messages` 为 None 时必须提供 `system` 和 `user`。

### `GenerationResult` 值对象（新增）

```python
@dataclass(frozen=True)
class GenerationResult:
    content: str                    # 文本回复
    tool_calls: list[ToolCall]      # 工具调用
    finish_reason: str              # "stop" | "tool_calls" | "length"
```

---

## Infrastructure 层设计

### LLM Provider 扩展

四个 Provider 均支持原生 function calling，改动为参数透传 + 结果解析：

| Provider | 原生参数 | 解析关注点 |
|----------|---------|-----------|
| AnthropicProvider | `tools=[...]` | `response.content` 中的 `tool_use` block |
| OpenAIProvider | `tools=[...]`, `tool_choice="auto"` | `response.choices[0].message.tool_calls` |
| ArkProvider (Doubao) | 同 OpenAI 协议 | 同上 |
| GeminiProvider | `tools=[...]` | `response.candidates[0].content.parts[].function_call` |

每个 Provider 的 `generate()` 方法扩展约 20 行，统一解析为 `GenerationResult`。

### 工具注册表（新增 `infrastructure/ai/tool_registry.py`）

```python
@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict           # JSON Schema
    handler: Callable          # async (args: dict) -> str

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None: ...
    def get_definitions(self) -> list[ToolDefinition]: ...
    async def execute(self, name: str, args: dict) -> str: ...
```

### LLMClient 扩展

新增 `generate_with_tools()` 方法：

```python
async def generate_with_tools(
    self, messages: list[Message], tools: list[ToolDefinition]
) -> GenerationResult: ...
```

### 首批工具：`lookup_genre_templates`（`application/assist/tools/lookup_genre.py`）

```python
async def lookup_genre_templates(genre_keyword: str) -> str:
    """搜索 builtin_cn_v1.yaml 中匹配的类型模板
    
    返回格式化的模板文本，包含：
    - 世界观基调 (world_tone)
    - 剧情结构 (story_structure)
    - 节奏把控 (pacing_control)
    - 写作风格 (writing_style)
    - 特殊要求 (special_requirements)
    
    模糊匹配：从 genre_keyword 中提取关键词，在 taxonomy 树中
    按子节点 > 根节点、长标签 > 短标签的优先级匹配。
    """
```

---

## Application 层设计

### Agent 循环核心流程

```python
class AssistService:
    async def chat(
        self, session: InspireSession, user_message: str
    ) -> AsyncIterator[SSEEvent]:
        """Agent 循环：多轮消息 + 工具调用 + 流式输出"""

        # 1. 保存用户消息
        await self._repo.add_message(InspireMessage(
            session_id=session.id, role="user", content=user_message
        ))

        # 2. 构建多轮消息数组
        history = await self._repo.get_messages(session.id)
        strategy = _get_strategy(session.strategy.value)
        messages = [Message(role="system", content=strategy.build_agent_system_prompt())]
        for m in history:
            messages.append(Message(role=m.role, content=m.content))

        # 3. Agent 循环
        tools = tool_registry.get_definitions()
        full_content = ""
        tool_call_count = 0

        for _ in range(5):  # 安全上限，防止死循环
            result = await self._llm.generate_with_tools(messages, tools)

            # 分支 A：LLM 要调工具
            if result.tool_calls:
                for tc in result.tool_calls:
                    tool_call_count += 1
                    if tool_call_count > 3:  # 防止频繁不必要的工具调用
                        break
                    yield SSEEvent("tool_call", {"name": tc.name, "args": tc.arguments})
                    tool_result = await tool_registry.execute(tc.name, tc.arguments)
                    yield SSEEvent("tool_result", {
                        "name": tc.name,
                        "summary": tool_result[:200]
                    })
                    messages.append(Message(
                        role="assistant",
                        content="",
                        tool_calls=[tc]
                    ))
                    messages.append(Message(
                        role="tool",
                        content=tool_result,
                        tool_call_id=tc.id
                    ))
                continue  # 回到循环，让 LLM 基于工具结果继续思考

            # 分支 B：LLM 给出最终文本回复
            async for chunk in self._llm.stream_generate(messages):
                full_content += chunk
                yield SSEEvent("chat_chunk", {"content": chunk})

            # 判断消息类型
            is_question = full_content.strip().endswith(("？", "?"))
            yield SSEEvent("chat_done", {
                "message_type": "question" if is_question else "suggestion"
            })
            break

        # 4. 保存 AI 回复
        if full_content:
            await self._repo.add_message(InspireMessage(
                session_id=session.id, role="assistant", content=full_content
            ))
```

### 策略 Prompt 重写原则

所有四个策略统一遵循：

1. **去掉 `绝对禁止提问`** — 改为「追问仅限一句，放在回复末尾」
2. **新增工具使用指引** — 「当用户提到具体类型时，使用 lookup_genre_templates」
3. **协作式语调** — 「用户引领方向，你跟随展开」「像两个作家朋友在咖啡馆聊灵感」
4. **追问判断标准** — 仅在方向性分歧大时追问（如「废土是病毒还是核战？」），细节留白不做追问

以 Brainstorm 策略为例：

```
你是一个创意写作伙伴，擅长根据用户的碎片想法展开联想、
构建完整的故事框架。

对话节奏：
- 用户引领方向，你跟随并展开联想分析
- 如果用户信息很少，大胆推测并给出完整方案
- 每次回复末尾最多追问一句来澄清关键方向
- 语言轻松日常，像作家朋友在咖啡馆聊灵感

工具使用：
- 当用户提到具体类型时（如「末世」「玄幻」「悬疑」），
  调用 lookup_genre_templates 获取该类型的写作模板，
  让建议更具体有据

用中文回复。
```

### `generate_fields()` — 保持不变

两阶段流程照旧：用户手动触发 → LLM 提取 title/premise/genre → 匹配 taxonomy → 定制化 → `fields_done`。不动。

---

## Interface 层设计

### SSE 事件扩展

在现有事件基础上新增两个：

```
# Agent 决定调用工具
event: tool_call
data: {"name": "lookup_genre_templates", "args": {"genre_keyword": "末世"}}

# 工具执行完成
event: tool_result
data: {"name": "lookup_genre_templates", "summary": "末世类型模板：世界观基调为..."}
```

### 事件时序

```
session_created           ← 首次聊天
  ↓
chat_chunk × N            ← 流式 token
  ↓
chat_done                 ← 末尾带 message_type: "question" | "suggestion"
  ↓
（用户手动触发生成字段）
  ↓
fields_done               ← 结构化字段提取完成
```

工具调用事件插在 `chat_chunk` 之前（Agent 先查资料再回复），跨工具多轮调用时交替出现：

```
tool_call → tool_result → tool_call → tool_result → chat_chunk... → chat_done
```

### `message_type` 判断逻辑

依赖 prompt 中「追问仅限一句，放在回复末尾」的约定，用末尾字符判断：

```python
content = full_content.strip()
is_question = content.endswith("？") or content.endswith("?")
```

**边界说明：** 若模型未遵守「追问在末尾」的约定，问号在回复中间会被归类为 suggestion。这不影响体验——混合回复仍然有信息量，只是气泡样式差异。若后续发现误判率高，可升级为「正文+末尾问句」的正则匹配。

---

## 前端设计

### 追问 vs 建议气泡

```
┌──────────────────────────────────┐
│  用户气泡（右对齐，主题色）        │
│  "我想写一个末世废土的故事"        │
└──────────────────────────────────┘

     ┌──────────────────────────────────┐
     │  💡 建议                         │
     │  "末世文的核心张力是「秩序崩溃    │
     │   后的人性重建」，你可以从..."     │
     └──────────────────────────────────┘
     ← 左侧，灰底，普通气泡

     ┌──────────────────────────────────┐
     │  🤔 追问                         │
     │  "废土是因为核战、病毒还是气候    │
     │   灾难？不同灾难类型带来完全不同  │
     │   的社会结构和美学。"             │
     └──────────────────────────────────┘
     ← 左侧，琥珀/浅黄底，? 图标
```

**CSS 类：**
- `.bubble-suggestion` — 标准 `var(--n-color-modal)` 底色
- `.bubble-question` — `rgba(245, 158, 11, 0.08)` 底色，左边框 `3px solid #f59e0b`

**实现：**`chat_done` 事件携带 `message_type`，Vue 模板中用 `:class` 切换。

### 工具调用状态条

```
┌──────────────────────────────────────────┐
│  🔍 正在查找「末世」类型写作模板...       │  ← tool_call 时滑入
└──────────────────────────────────────────┘
  ↓ 1-2 秒
┌──────────────────────────────────────────┐
│  ✅ 已参考「末世」类型模板                │  ← tool_result 时替换文本
└──────────────────────────────────────────┘
  ↓ 1.5 秒后滑出消失
```

**实现：**
- Naive UI `<n-alert>` + Vue `<Transition name="slide-fade">`
- `tool_call` 事件 → `toolStatus.show = true`, `toolStatus.text = "正在查找..."`, `toolStatus.type = "info"`
- `tool_result` 事件 → `toolStatus.text = "已参考...模板"`, `toolStatus.type = "success"`，1.5 秒后 `show = false`

**动画 CSS：**
```css
.slide-fade-enter-active { transition: all 0.3s ease; }
.slide-fade-leave-active { transition: all 0.3s ease; }
.slide-fade-enter-from,
.slide-fade-leave-to { transform: translateY(-10px); opacity: 0; }
```

### `assist.ts` 接口扩展

```typescript
// 新增事件类型
type AssistEventType = 'session_created' | 'chat_chunk' | 'chat_done'
  | 'fields_done' | 'tool_call' | 'tool_result';

// chat_done 的 data 扩展
interface ChatDoneData {
  message_type: 'question' | 'suggestion';
}

// 新增回调
interface AssistCallbacks {
  onSessionCreated?: (data: ...) => void;
  onChatChunk?: (data: ...) => void;
  onChatDone?: (data: ChatDoneData) => void;
  onFieldsDone?: (data: ...) => void;
  onToolCall?: (data: { name: string; args: Record<string, any> }) => void;
  onToolResult?: (data: { name: string; summary: string }) => void;
}
```

### 不改的部分

- 策略选择器（顶栏下拉）— 保持
- 「生成字段」按钮 — 保持
- 「填充到表单」流程 — 保持
- 右侧字段预览侧栏 — 保持
- 聊天输入框、Enter 发送 — 保持
- 弹窗布局：左侧对话 + 右侧字段预览 — 保持

---

## 改动清单

### 新建文件

| 文件 | 说明 |
|------|------|
| `domain/ai/value_objects/generation_result.py` | `GenerationResult` 值对象 |
| `infrastructure/ai/tool_registry.py` | 工具注册表 |
| `application/assist/tools/__init__.py` | 工具包入口 |
| `application/assist/tools/lookup_genre.py` | 首个工具：查 genre 模板 |

### 修改文件

| 文件 | 改动 | 估计行数 |
|------|------|---------|
| `domain/ai/value_objects/prompt.py` | 新增 `Message`、`ToolCall`、`ToolDefinition`，`Prompt` 扩展 `messages` 和 `tools` 字段 | +60 |
| `domain/ai/services/llm_service.py` | `GenerationResult` 支持 `tool_calls` 字段 | +15 |
| `infrastructure/ai/providers/anthropic_provider.py` | `generate()` 透传 tools，解析 tool_use | +20 |
| `infrastructure/ai/providers/openai_provider.py` | `generate()` 透传 tools，解析 tool_calls | +20 |
| `infrastructure/ai/providers/ark_provider.py` | 同 OpenAI | +20 |
| `infrastructure/ai/providers/gemini_provider.py` | `generate()` 透传 tools，解析 function_call | +20 |
| `infrastructure/ai/llm_client.py` | 新增 `generate_with_tools()` | +20 |
| `application/assist/assist_service.py` | `chat()` 重写为 Agent 循环 | +80/-30 |
| `application/assist/strategies/base.py` | 新增 `build_agent_system_prompt()` 抽象方法 | +5 |
| `application/assist/strategies/brainstorm.py` | 重写 prompt | +15/-10 |
| `application/assist/strategies/world_first.py` | 重写 prompt | +15/-10 |
| `application/assist/strategies/character_driven.py` | 重写 prompt | +15/-10 |
| `application/assist/strategies/theme_first.py` | 重写 prompt | +15/-10 |
| `interfaces/api/v1/assist/inspire_routes.py` | SSE 事件新增 `tool_call` / `tool_result`，`chat_done` 新增 `message_type` | +20 |
| `frontend/src/api/assist.ts` | 事件类型 + 回调扩展 | +20 |
| `frontend/src/components/inspiration/InspirationAssistantModal.vue` | 追问/建议气泡 + 工具状态条 | +80 |

**总计：4 新建 + 16 修改，净增约 420 行，删除约 70 行。**

---

## 测试策略

| 测试类型 | 测试内容 |
|---------|---------|
| 单元测试 | `ToolRegistry` 注册/查找/执行；`Message`/`ToolCall` 值对象序列化；`_build_conversation_text` → 多轮 messages 转换 |
| 集成测试 | Agent 循环：无工具调用路径（纯文本回复）；有工具调用路径（mock LLM 返回 tool_calls）；工具执行失败降级 |
| 前端测试 | `chat_done` 事件 `message_type` 切换气泡样式；`tool_call` → `tool_result` 状态条动画 |
| 回归测试 | `generate_fields()` 两阶段流程不受影响；现有 8 个恢复策略测试保持通过 |

---

## 风险与缓解

| 风险 | 概率 | 缓解 |
|------|------|------|
| LLM 频繁不必要的工具调用 | 中 | Prompt 明确「仅在提到具体类型时调用」，降级：工具调用超 3 次直接 break 输出 |
| 追问过多打断用户 | 低 | Prompt「追问仅限一句」，前端不强制回复，用户可忽略追问继续聊 |
| Provider 不支持 tool calling | 低 | `generate_with_tools()` 内检测：若 tools 为空直接走普通 `stream_generate` |
| 向后兼容 | — | `Prompt` 保留 `system`/`user` 字段，`messages=None` 时走旧路径 |
