# 灵感助手 — 多轮对话智能体设计文档

> 作者: Axelton | 日期: 2026-06-14

## 目标

在新建书目页面增加"灵感助手"入口，通过多轮对话帮助没有灵感的用户生成书名、简介、大类及写作四要素，一键填充到新建书目表单。

---

## 总体架构

独立助手模块 `assist/`，DDD 四层：

```
domain/assist/               # 领域层
  entities.py                # InspireSession, InspireMessage, InspirationStrategy
  repository.py              # InspireRepository 抽象接口

application/assist/          # 应用层
  assist_service.py          # 核心服务：会话管理 + 对话 + 字段提取
  strategies/                # 灵感策略
    base.py                  # 抽象策略基类
    brainstorm.py            # 脑洞爆破
    world_first.py           # 世界观优先
    character_driven.py      # 角色驱动
    theme_first.py           # 主题先行

infrastructure/persistence/  # 基础设施层
  assist_repository.py       # SQLite 实现

interfaces/api/v1/assist/    # 接口层
  inspire_routes.py          # SSE 流式端点
```

### 数据库表

| 表 | 关键字段 |
|---|---|
| `assist_sessions` | id, novel_id, strategy, status, created_at, updated_at |
| `assist_messages` | id, session_id, role(user/assistant), content, field_suggestions(json), created_at |

---

## API 设计

### `POST /api/v1/assist/inspire`

统一 SSE 流式端点，通过 `action` 区分行为。

**请求体：**
```json
{
  "novel_id": "novel-1718400000",
  "session_id": "sess_abc123",
  "strategy": "brainstorm",
  "action": "chat",
  "message": "我想写一个废土故事..."
}
```

- `session_id`：首次为空，后端创建并返回
- `strategy`：首次必传，后续忽略
- `action`：`"chat"` | `"generate_fields"` | `"resume"`

**SSE 事件（action=chat）：**
```
event: session_created
data: {"session_id": "sess_abc123", "strategy": "brainstorm"}

event: chat_chunk
data: {"content": "废土题材很有"}

event: chat_done
data: {"message_id": "msg_xyz", "full_content": "废土题材很有张力！..."}
```

**SSE 事件（action=generate_fields）：**
```
event: fields_done
data: {
  "title": "末日暖阳",
  "premise": "核战后百年，一个少年在废土中寻找...",
  "genre": "科幻 / 末世废土",
  "world_preset": "核战后废土世界，资源匮乏...",
  "story_structure": "英雄之旅变体...",
  "pacing_control": "每3章一个小高潮...",
  "writing_style": "冷峻写实为主，对白简洁...",
  "special_requirements": "避免落入后启示录俗套..."
}
```

**action=resume：** 加载历史会话，返回全部消息记录（非流式 JSON）。

---

## 前端组件

### 组件树

```
Home.vue
├── MarketTaxonomyPicker.vue     （现有）
└── InspirationAssistantModal.vue （新增）
    ├── 策略选择区
    ├── 对话消息列表
    ├── 消息输入区 + 发送
    └── 字段预览侧栏
```

### 弹窗布局

```
┌─────────────────────────────────────┐
│  灵感助手                    [✕]    │
│  策略: 脑洞爆破 ▾                   │
├───────────────────────┬─────────────┤
│  对话区                │  字段预览    │
│  🤖: 你好！...         │  书名: —     │
│  😀: 我想写废土...      │  大类: —     │
│  🤖: 废土题材...       │  世界观: —   │
│                       │  结构: —     │
│                       │  节奏: —     │
│                       │  风格: —     │
│                       │  要求: —     │
│                       │ [填充表单]   │
├───────────────────────┴─────────────┤
│ [输入框........................] [发送] │
│              [生成字段]              │
└─────────────────────────────────────┘
```

### 数据流

```
用户发消息
  → SSE (action=chat) → 流式渲染 AI 回复
  → 用户点"生成字段"
  → SSE (action=generate_fields) → fields_done
  → 右侧预览栏更新
  → 用户点"填充表单"
  → emit('fill-fields', fields)
  → Home.vue 写入 newBook ref
  → MarketTaxonomyPicker.syncFromGenreString() 自动选中分类
```

关闭弹窗后会话持久化，下次打开可用 `action=resume` 恢复。

---

## 四种灵感策略

| 策略 | 系统提示词核心 |
|------|---------------|
| **脑洞爆破** | 通过轻松聊天帮用户从兴趣、情绪、最近看过的作品等角度找到创作冲动，用日常语言，不问专业术语 |
| **世界观优先** | 引导描述物理规则、社会结构、历史背景、独特美学，用"如果…会怎样"展开 |
| **角色驱动** | 追问角色的欲望、恐惧、缺陷、关系，从角色出发推导故事冲突和世界观基调 |
| **主题先行** | 追问主题的切面、对立面、载体，找到具象化的故事外壳和叙事结构 |

用户开新会话时选择策略，系统提示词锁定，后续对话始终在该框架下进行。

---

## 修改清单

**新建（后端）：**
- `domain/assist/entities.py` — 领域实体
- `domain/assist/repository.py` — 仓储抽象接口
- `application/assist/strategies/base.py` — 策略基类
- `application/assist/strategies/brainstorm.py` — 脑洞爆破
- `application/assist/strategies/world_first.py` — 世界观优先
- `application/assist/strategies/character_driven.py` — 角色驱动
- `application/assist/strategies/theme_first.py` — 主题先行
- `application/assist/assist_service.py` — 核心服务
- `infrastructure/persistence/assist_repository.py` — SQLite 实现
- `interfaces/api/v1/assist/inspire_routes.py` — SSE 端点

**新建（前端）：**
- `frontend/src/components/inspiration/InspirationAssistantModal.vue` — 对话弹窗
- `frontend/src/api/assist.ts` — API 调用封装

**修改：**
- `interfaces/api/routes.py` — 注册 `/api/v1/assist` 路由
- `frontend/src/views/Home.vue` — "高级"按钮旁增加"灵感助手"入口 + 处理 fill-fields 事件
