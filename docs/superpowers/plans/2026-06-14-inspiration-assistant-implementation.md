# 灵感助手 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 在新建书目页面增加"灵感助手"按钮，通过 SSE 流式多轮对话帮助无灵感的用户生成书名、简介、大类及写作四要素，一键填充到表单。

**架构：** 独立 `assist/` 模块，后端 DDD 四层（domain → application → infrastructure → interfaces），前端 `InspirationAssistantModal.vue` 弹窗组件。四种灵感策略（脑洞爆破/世界观优先/角色驱动/主题先行），单一 SSE 端点通过 `action` 参数区分行为。

**技术栈：** Python FastAPI + SQLite + Vue 3 + TypeScript + Naive UI

---

## 文件结构

```
# 后端 — 新建
domain/assist/
  entities.py                  # InspireSession, InspireMessage, InspirationStrategy
  repository.py                # InspireRepository 抽象接口

application/assist/
  assist_service.py            # 核心服务：会话管理 + 对话 + 字段提取
  strategies/
    __init__.py
    base.py                    # 抽象策略基类
    brainstorm.py              # 脑洞爆破
    world_first.py             # 世界观优先
    character_driven.py        # 角色驱动
    theme_first.py             # 主题先行

infrastructure/persistence/
  assist_repository.py         # SQLite 实现 + 建表迁移

interfaces/api/v1/assist/
  __init__.py
  inspire_routes.py            # POST /api/v1/assist/inspire SSE 端点

# 后端 — 修改
interfaces/api/routes.py       # 注册 assist 路由

# 前端 — 新建
frontend/src/api/assist.ts     # SSE 消费 + API 封装
frontend/src/components/inspiration/
  InspirationAssistantModal.vue  # 对话弹窗

# 前端 — 修改
frontend/src/views/Home.vue    # 增加"灵感助手"按钮 + fill-fields 事件处理
```

---

### Task 1: 领域实体 `domain/assist/entities.py`

**文件：**
- 创建：`domain/assist/entities.py`
- 创建：`domain/assist/__init__.py`（空文件）

- [ ] **Step 1: 编写领域实体**

```python
# domain/assist/entities.py
"""灵感助手领域实体 — 作者：Axelton"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from domain.shared.base_entity import BaseEntity


class InspirationStrategy(str, Enum):
    """灵感策略枚举"""
    BRAINSTORM = "brainstorm"          # 脑洞爆破
    WORLD_FIRST = "world_first"        # 世界观优先
    CHARACTER_DRIVEN = "character_driven"  # 角色驱动
    THEME_FIRST = "theme_first"        # 主题先行


class SessionStatus(str, Enum):
    """会话状态"""
    ACTIVE = "active"
    COMPLETED = "completed"


class InspireSession(BaseEntity):
    """灵感对话会话"""

    def __init__(
        self,
        id: str,
        novel_id: str,
        strategy: InspirationStrategy,
        status: SessionStatus = SessionStatus.ACTIVE,
    ):
        super().__init__(id)
        self.novel_id = novel_id
        self.strategy = strategy
        self.status = status

    def complete(self) -> None:
        """标记会话完成"""
        self.status = SessionStatus.COMPLETED
        from datetime import datetime, timezone
        self.updated_at = datetime.now(timezone.utc)


class InspireMessage(BaseEntity):
    """对话消息"""

    def __init__(
        self,
        id: str,
        session_id: str,
        role: str,  # "user" | "assistant"
        content: str,
        field_suggestions: Optional[dict] = None,
    ):
        super().__init__(id)
        self.session_id = session_id
        self.role = role
        self.content = content
        self.field_suggestions = field_suggestions or {}


@dataclass(frozen=True)
class InspireFieldData:
    """字段提取结果 — 不可变值对象，由 generate_fields action 产出"""
    title: str = ""
    premise: str = ""
    genre: str = ""
    world_preset: str = ""
    story_structure: str = ""
    pacing_control: str = ""
    writing_style: str = ""
    special_requirements: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "premise": self.premise,
            "genre": self.genre,
            "world_preset": self.world_preset,
            "story_structure": self.story_structure,
            "pacing_control": self.pacing_control,
            "writing_style": self.writing_style,
            "special_requirements": self.special_requirements,
        }
```

- [ ] **Step 2: 验证语法正确**

```bash
python -c "from domain.assist.entities import InspireSession, InspireMessage, InspirationStrategy, InspireFieldData; print('OK')"
```

- [ ] **Step 3: 提交**

```bash
git add domain/assist/__init__.py domain/assist/entities.py
git commit -m "feat(assist): add domain entities for inspiration assistant"
```

---

### Task 2: 仓储抽象接口 `domain/assist/repository.py`

**文件：**
- 修改：`domain/assist/repository.py`（尚未创建，本质是新建）

- [ ] **Step 1: 编写仓储抽象接口**

```python
# domain/assist/repository.py
"""灵感助手仓储抽象接口 — 作者：Axelton"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from domain.assist.entities import InspireSession, InspireMessage


class InspireRepository(ABC):
    """灵感助手仓储抽象接口"""

    @abstractmethod
    async def create_session(self, session: InspireSession) -> InspireSession:
        """创建会话"""
        ...

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[InspireSession]:
        """获取会话"""
        ...

    @abstractmethod
    async def update_session(self, session: InspireSession) -> InspireSession:
        """更新会话"""
        ...

    @abstractmethod
    async def add_message(self, message: InspireMessage) -> InspireMessage:
        """添加消息"""
        ...

    @abstractmethod
    async def get_messages(self, session_id: str) -> List[InspireMessage]:
        """获取会话的全部消息（按时间正序）"""
        ...

    @abstractmethod
    async def get_latest_session(self, novel_id: str) -> Optional[InspireSession]:
        """获取某书目最近一次活跃会话"""
        ...
```

- [ ] **Step 2: 验证语法正确**

```bash
python -c "from domain.assist.repository import InspireRepository; print('OK')"
```

- [ ] **Step 3: 提交**

```bash
git add domain/assist/repository.py
git commit -m "feat(assist): add repository abstract interface"
```

---

### Task 3: 灵感策略 `application/assist/strategies/`

**文件：**
- 创建：`application/assist/__init__.py`（空文件）
- 创建：`application/assist/strategies/__init__.py`（空文件）
- 创建：`application/assist/strategies/base.py`
- 创建：`application/assist/strategies/brainstorm.py`
- 创建：`application/assist/strategies/world_first.py`
- 创建：`application/assist/strategies/character_driven.py`
- 创建：`application/assist/strategies/theme_first.py`

- [ ] **Step 1: 编写策略基类**

```python
# application/assist/strategies/base.py
"""灵感策略抽象基类 — 作者：Axelton"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from domain.ai.value_objects.prompt import Prompt


class BaseInspirationStrategy(ABC):
    """灵感策略抽象基类 — 每个策略定义系统提示词和字段提取提示词"""

    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """策略描述（给用户看的）"""
        ...

    @abstractmethod
    def build_system_prompt(self) -> str:
        """构建系统提示词 — 锁定对话框架"""
        ...

    @abstractmethod
    def build_field_extraction_prompt(self, conversation_history: str) -> str:
        """构建字段提取提示词 — 从对话历史中提取结构化字段"""
        ...

    def make_prompt(self, user_message: str) -> Prompt:
        """根据用户消息创建 Prompt 对象"""
        return Prompt(
            system=self.build_system_prompt(),
            user=user_message,
        )

    def make_field_extraction_prompt_obj(self, conversation_history: str) -> Prompt:
        """创建字段提取 Prompt 对象"""
        return Prompt(
            system=self.build_system_prompt(),
            user=self.build_field_extraction_prompt(conversation_history),
        )
```

- [ ] **Step 2: 编写脑洞爆破策略**

```python
# application/assist/strategies/brainstorm.py
"""脑洞爆破策略 — 作者：Axelton"""
from __future__ import annotations

from application.assist.strategies.base import BaseInspirationStrategy


class BrainstormStrategy(BaseInspirationStrategy):
    """脑洞爆破 — 通过轻松聊天帮用户从兴趣、情绪、最近看过的作品等角度找到创作冲动"""

    @property
    def name(self) -> str:
        return "brainstorm"

    @property
    def description(self) -> str:
        return "脑洞爆破 — 从你的兴趣和情绪出发，轻松聊出创作火花"

    def build_system_prompt(self) -> str:
        return (
            "你是一个创意写作灵感助手，擅长通过轻松自然的对话帮助用户发现想写的故事。\n\n"
            "你的对话风格：\n"
            "- 使用日常语言，不问专业术语\n"
            "- 从用户的兴趣、情绪、最近看过的作品、梦、记忆等角度切入\n"
            "- 像朋友聊天一样，引导用户说出心中模糊的故事种子\n"
            "- 每次只问一个问题，耐心引导\n"
            "- 当用户提到一个具体想法时，帮他/她展开并具象化\n\n"
            "不要直接问「你想写什么类型的小说」，而是通过侧面引导让用户自己发现。\n"
            "用中文回复。"
        )

    def build_field_extraction_prompt(self, conversation_history: str) -> str:
        return (
            f"根据以下对话历史，提取用户想要创作的小说的结构化信息。\n\n"
            f"对话历史：\n{conversation_history}\n\n"
            f"请以 JSON 格式输出，包含以下字段（如果对话中未明确提及，根据上下文合理推断）：\n"
            f'{{"title": "建议的书名", "premise": "200字以内的核心梗概", '
            f'"genre": "大类/细分主题（如：科幻/末世废土）", '
            f'"worldPreset": "世界观基调描述", '
            f'"storyStructure": "建议的剧情结构", '
            f'"pacingControl": "节奏把控建议", '
            f'"writingStyle": "建议的写作风格", '
            f'"specialRequirements": "特殊要求或注意事项"}}\n\n'
            f"只输出 JSON，不要任何额外文字。"
        )
```

- [ ] **Step 3: 编写世界观优先策略**

```python
# application/assist/strategies/world_first.py
"""世界观优先策略 — 作者：Axelton"""
from __future__ import annotations

from application.assist.strategies.base import BaseInspirationStrategy


class WorldFirstStrategy(BaseInspirationStrategy):
    """世界观优先 — 引导描述物理规则、社会结构、历史背景、独特美学"""

    @property
    def name(self) -> str:
        return "world_first"

    @property
    def description(self) -> str:
        return "世界观优先 — 先构建世界，再让故事从中自然生长"

    def build_system_prompt(self) -> str:
        return (
            "你是一个世界观架构师，擅长通过「如果……会怎样」的假设性问题，"
            "帮助用户构建独特的世界设定。\n\n"
            "你的对话风格：\n"
            "- 从宏观到微观，逐步细化世界设定\n"
            "- 引导用户思考物理规则、社会结构、历史背景、独特美学\n"
            "- 用「如果…会怎样」的方式展开想象\n"
            "- 每次聚焦一个维度，不要一次问太多\n"
            "- 帮助用户发现世界中蕴含的天然冲突和故事可能性\n\n"
            "对话维度顺序建议：基础规则 → 社会结构 → 历史事件 → 美学风格 → 冲突发现\n"
            "用中文回复。"
        )

    def build_field_extraction_prompt(self, conversation_history: str) -> str:
        return (
            f"根据以下对话历史，提取用户构建的世界观及由此衍生的故事信息。\n\n"
            f"对话历史：\n{conversation_history}\n\n"
            f"请以 JSON 格式输出，包含以下字段：\n"
            f'{{"title": "建议的书名", "premise": "200字以内的核心梗概（基于世界观推导）", '
            f'"genre": "大类/细分主题", '
            f'"worldPreset": "世界观基调描述（基于对话提炼）", '
            f'"storyStructure": "建议的剧情结构（与世界观匹配）", '
            f'"pacingControl": "节奏把控建议", '
            f'"writingStyle": "建议的写作风格", '
            f'"specialRequirements": "特殊要求或注意事项"}}\n\n'
            f"只输出 JSON，不要任何额外文字。"
        )
```

- [ ] **Step 4: 编写角色驱动策略**

```python
# application/assist/strategies/character_driven.py
"""角色驱动策略 — 作者：Axelton"""
from __future__ import annotations

from application.assist.strategies.base import BaseInspirationStrategy


class CharacterDrivenStrategy(BaseInspirationStrategy):
    """角色驱动 — 追问角色的欲望、恐惧、缺陷、关系，从角色推导故事"""

    @property
    def name(self) -> str:
        return "character_driven"

    @property
    def description(self) -> str:
        return "角色驱动 — 从一个鲜活的人物出发，让故事围绕他/她展开"

    def build_system_prompt(self) -> str:
        return (
            "你是一个角色驱动的故事开发助手，相信「好故事从好角色开始」。\n\n"
            "你的对话风格：\n"
            "- 先帮助用户发现/塑造一个有意思的主角\n"
            "- 追问角色的欲望（想要什么）、恐惧（害怕什么）、缺陷（有什么毛病）、关系（身边有谁）\n"
            "- 从角色的内在矛盾推导故事冲突\n"
            "- 从角色的世界观推导故事世界设定\n"
            "- 每次聚焦角色的一两个方面，逐步丰富\n\n"
            "对话维度顺序建议：角色初印象 → 欲望与恐惧 → 缺陷与成长弧 → 关系网 → 由此衍生的世界与冲突\n"
            "用中文回复。"
        )

    def build_field_extraction_prompt(self, conversation_history: str) -> str:
        return (
            f"根据以下对话历史，提取角色信息及由此衍生的故事结构化信息。\n\n"
            f"对话历史：\n{conversation_history}\n\n"
            f"请以 JSON 格式输出，包含以下字段：\n"
            f'{{"title": "建议的书名", "premise": "200字以内的核心梗概（从角色出发推导）", '
            f'"genre": "大类/细分主题", '
            f'"worldPreset": "世界观基调描述（与角色匹配）", '
            f'"storyStructure": "建议的剧情结构（配适角色成长弧）", '
            f'"pacingControl": "节奏把控建议", '
            f'"writingStyle": "建议的写作风格", '
            f'"specialRequirements": "特殊要求或注意事项"}}\n\n'
            f"只输出 JSON，不要任何额外文字。"
        )
```

- [ ] **Step 5: 编写主题先行策略**

```python
# application/assist/strategies/theme_first.py
"""主题先行策略 — 作者：Axelton"""
from __future__ import annotations

from application.assist.strategies.base import BaseInspirationStrategy


class ThemeFirstStrategy(BaseInspirationStrategy):
    """主题先行 — 追问主题的切面、对立面、载体，找到具象化的故事外壳"""

    @property
    def name(self) -> str:
        return "theme_first"

    @property
    def description(self) -> str:
        return "主题先行 — 从一个你想探讨的主题出发，找到最适合承载它的故事"

    def build_system_prompt(self) -> str:
        return (
            "你是一个主题驱动的故事开发助手，擅长帮助用户将抽象主题具象化为故事。\n\n"
            "你的对话风格：\n"
            "- 从用户感兴趣的主题/议题切入（如「自由」「复仇」「成长」「爱」）\n"
            "- 追问主题的不同切面和对立面（例如「正义」vs「复仇」的边界）\n"
            "- 帮助用户找到承载主题的具体人物和情境\n"
            "- 推导最适合这个主题的叙事结构\n"
            "- 每次深入一个切面，逐步构建完整的故事框架\n\n"
            "对话维度顺序建议：主题确认 → 切面展开 → 对立面引入 → 人物载体 → 故事结构\n"
            "用中文回复。"
        )

    def build_field_extraction_prompt(self, conversation_history: str) -> str:
        return (
            f"根据以下对话历史，提取主题信息及由此衍生的故事结构化信息。\n\n"
            f"对话历史：\n{conversation_history}\n\n"
            f"请以 JSON 格式输出，包含以下字段：\n"
            f'{{"title": "建议的书名", "premise": "200字以内的核心梗概（表现主题）", '
            f'"genre": "大类/细分主题", '
            f'"worldPreset": "世界观基调描述（服务于主题）", '
            f'"storyStructure": "建议的剧情结构（匹配主题展开节奏）", '
            f'"pacingControl": "节奏把控建议", '
            f'"writingStyle": "建议的写作风格", '
            f'"specialRequirements": "特殊要求或注意事项"}}\n\n'
            f"只输出 JSON，不要任何额外文字。"
        )
```

- [ ] **Step 6: 验证所有策略可导入**

```bash
python -c "
from application.assist.strategies.brainstorm import BrainstormStrategy
from application.assist.strategies.world_first import WorldFirstStrategy
from application.assist.strategies.character_driven import CharacterDrivenStrategy
from application.assist.strategies.theme_first import ThemeFirstStrategy
s = BrainstormStrategy()
print(s.name, '-', s.description)
print('OK')
"
```

- [ ] **Step 7: 提交**

```bash
git add application/assist/__init__.py application/assist/strategies/
git commit -m "feat(assist): add four inspiration strategies"
```

---

### Task 4: SQLite 仓储实现 `infrastructure/persistence/assist_repository.py`

**文件：**
- 创建：`infrastructure/persistence/assist_repository.py`

- [ ] **Step 1: 编写 SQLite 仓储实现（含建表迁移）**

```python
# infrastructure/persistence/assist_repository.py
"""灵感助手 SQLite 仓储实现 — 作者：Axelton"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List, Optional

from domain.assist.entities import (
    InspireSession,
    InspireMessage,
    InspirationStrategy,
    SessionStatus,
)
from domain.assist.repository import InspireRepository
from infrastructure.persistence.database.connection import DatabaseConnection


class SqliteAssistRepository(InspireRepository):
    """灵感助手 SQLite 仓储实现"""

    def __init__(self, db: DatabaseConnection):
        self._db = db
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """建表迁移（幂等）"""
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS assist_sessions ("
            "  id TEXT PRIMARY KEY,"
            "  novel_id TEXT NOT NULL,"
            "  strategy TEXT NOT NULL,"
            "  status TEXT NOT NULL DEFAULT 'active',"
            "  created_at TEXT NOT NULL,"
            "  updated_at TEXT NOT NULL"
            ")"
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_assist_sessions_novel "
            "ON assist_sessions(novel_id)"
        )
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS assist_messages ("
            "  id TEXT PRIMARY KEY,"
            "  session_id TEXT NOT NULL,"
            "  role TEXT NOT NULL,"
            "  content TEXT NOT NULL,"
            "  field_suggestions TEXT DEFAULT '{}',"
            "  created_at TEXT NOT NULL,"
            "  updated_at TEXT NOT NULL"
            ")"
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_assist_messages_session "
            "ON assist_messages(session_id)"
        )
        self._db.commit()

    # ---- session helpers ----

    def _row_to_session(self, row: dict) -> InspireSession:
        session = InspireSession(
            id=row["id"],
            novel_id=row["novel_id"],
            strategy=InspirationStrategy(row["strategy"]),
            status=SessionStatus(row["status"]),
        )
        session.created_at = datetime.fromisoformat(row["created_at"])
        session.updated_at = datetime.fromisoformat(row["updated_at"])
        return session

    def _message_to_row(self, msg: InspireMessage) -> dict:
        return {
            "id": msg.id,
            "session_id": msg.session_id,
            "role": msg.role,
            "content": msg.content,
            "field_suggestions": json.dumps(msg.field_suggestions or {}, ensure_ascii=False),
            "created_at": msg.created_at.isoformat(),
            "updated_at": msg.updated_at.isoformat(),
        }

    def _row_to_message(self, row: dict) -> InspireMessage:
        msg = InspireMessage(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            field_suggestions=json.loads(row.get("field_suggestions", "{}")),
        )
        msg.created_at = datetime.fromisoformat(row["created_at"])
        msg.updated_at = datetime.fromisoformat(row["updated_at"])
        return msg

    # ---- public API ----

    async def create_session(self, session: InspireSession) -> InspireSession:
        self._db.execute(
            "INSERT INTO assist_sessions (id, novel_id, strategy, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                session.id,
                session.novel_id,
                session.strategy.value,
                session.status.value,
                session.created_at.isoformat(),
                session.updated_at.isoformat(),
            ),
        )
        self._db.commit()
        return session

    async def get_session(self, session_id: str) -> Optional[InspireSession]:
        row = self._db.fetch_one(
            "SELECT * FROM assist_sessions WHERE id = ?", (session_id,)
        )
        if row is None:
            return None
        return self._row_to_session(row)

    async def update_session(self, session: InspireSession) -> InspireSession:
        session.updated_at = datetime.now(timezone.utc)
        self._db.execute(
            "UPDATE assist_sessions SET status = ?, updated_at = ? WHERE id = ?",
            (session.status.value, session.updated_at.isoformat(), session.id),
        )
        self._db.commit()
        return session

    async def add_message(self, message: InspireMessage) -> InspireMessage:
        row = self._message_to_row(message)
        self._db.execute(
            "INSERT INTO assist_messages (id, session_id, role, content, field_suggestions, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                row["id"], row["session_id"], row["role"], row["content"],
                row["field_suggestions"], row["created_at"], row["updated_at"],
            ),
        )
        self._db.commit()
        return message

    async def get_messages(self, session_id: str) -> List[InspireMessage]:
        rows = self._db.fetch_all(
            "SELECT * FROM assist_messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        )
        return [self._row_to_message(r) for r in rows]

    async def get_latest_session(self, novel_id: str) -> Optional[InspireSession]:
        row = self._db.fetch_one(
            "SELECT * FROM assist_sessions WHERE novel_id = ? AND status = 'active' "
            "ORDER BY created_at DESC LIMIT 1",
            (novel_id,),
        )
        if row is None:
            return None
        return self._row_to_session(row)
```

- [ ] **Step 2: 验证可导入（需要后端运行环境）**

```bash
python -c "from infrastructure.persistence.assist_repository import SqliteAssistRepository; print('OK')"
```

- [ ] **Step 3: 提交**

```bash
git add infrastructure/persistence/assist_repository.py
git commit -m "feat(assist): add SQLite repository implementation"
```

---

### Task 5: 核心应用服务 `application/assist/assist_service.py`

**文件：**
- 创建：`application/assist/assist_service.py`

- [ ] **Step 1: 编写核心服务**

```python
# application/assist/assist_service.py
"""灵感助手核心服务 — 会话管理 + 对话 + 字段提取 — 作者：Axelton"""
from __future__ import annotations

import json
import uuid
from typing import AsyncIterator, List, Optional

from domain.ai.value_objects.prompt import Prompt
from domain.assist.entities import (
    InspireSession,
    InspireMessage,
    InspirationStrategy,
    SessionStatus,
    InspireFieldData,
)
from domain.assist.repository import InspireRepository
from infrastructure.ai.llm_client import LLMClient

from application.assist.strategies.base import BaseInspirationStrategy
from application.assist.strategies.brainstorm import BrainstormStrategy
from application.assist.strategies.world_first import WorldFirstStrategy
from application.assist.strategies.character_driven import CharacterDrivenStrategy
from application.assist.strategies.theme_first import ThemeFirstStrategy


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
    """灵感助手核心服务"""

    def __init__(self, repository: InspireRepository, llm_client: LLMClient = None):
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
        return await self._repo.get_session(session_id)

    async def get_messages(self, session_id: str) -> List[InspireMessage]:
        return await self._repo.get_messages(session_id)

    # ---- chat ----

    async def chat(
        self,
        session: InspireSession,
        user_message: str,
    ) -> AsyncIterator[str]:
        """流式对话 — 返回 AI 回复的逐块文本"""
        # 1. 保存用户消息
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

        # 构建带历史的多轮对话 prompt
        conversation = _build_conversation_text(history)
        full_prompt = (
            f"以下是对话历史：\n\n{conversation}\n\n"
            f"请根据对话历史，继续引导用户深入探索。用中文回复。"
        )
        prompt = Prompt(system=strategy.build_system_prompt(), user=full_prompt)

        # 3. 流式生成
        full_content = ""
        async for chunk in self._llm.stream_generate(prompt):
            full_content += chunk
            yield chunk

        # 4. 保存 AI 回复
        ai_msg = InspireMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            session_id=session.id,
            role="assistant",
            content=full_content,
        )
        await self._repo.add_message(ai_msg)

    # ---- field extraction ----

    async def generate_fields(self, session: InspireSession) -> InspireFieldData:
        """从对话历史提取字段"""
        history = await self._repo.get_messages(session.id)
        strategy = _get_strategy(session.strategy.value)
        conversation = _build_conversation_text(history)

        prompt = Prompt(
            system=strategy.build_system_prompt(),
            user=strategy.build_field_extraction_prompt(conversation),
        )

        raw = await self._llm.generate(prompt)

        # 解析 JSON（清洗可能的 markdown 包裹）
        raw = raw.strip()
        if raw.startswith("```"):
            # 移除 markdown 代码块标记
            raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        data = json.loads(raw)

        fields = InspireFieldData(
            title=data.get("title", ""),
            premise=data.get("premise", ""),
            genre=data.get("genre", ""),
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
        """恢复历史会话 — 返回全部消息"""
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
```

- [ ] **Step 2: 验证语法**

```bash
python -c "from application.assist.assist_service import AssistService; print('OK')"
```

- [ ] **Step 3: 提交**

```bash
git add application/assist/assist_service.py
git commit -m "feat(assist): add core assist service with chat and field extraction"
```

---

### Task 6: SSE API 端点 `interfaces/api/v1/assist/inspire_routes.py`

**文件：**
- 创建：`interfaces/api/v1/assist/__init__.py`（空文件）
- 创建：`interfaces/api/v1/assist/inspire_routes.py`

- [ ] **Step 1: 编写 SSE 端点**

先查看一个现有 SSE 端点的完整模式以精确匹配格式：

```
# 参考 interfaces/api/v1/engine/generation.py 中 SSE StreamingResponse 写法
```

- [ ] **Step 2: 实现路由**

```python
# interfaces/api/v1/assist/inspire_routes.py
"""灵感助手 SSE 流式端点 — 作者：Axelton"""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from application.assist.assist_service import AssistService
from domain.assist.entities import InspirationStrategy
from infrastructure.persistence.assist_repository import SqliteAssistRepository
from infrastructure.persistence.database.connection import get_database
from infrastructure.ai.llm_client import LLMClient

router = APIRouter()


class InspireRequest(BaseModel):
    """灵感助手请求体"""
    novel_id: str = Field(..., description="书目 ID")
    session_id: Optional[str] = Field(None, description="会话 ID，首次为空")
    strategy: Optional[str] = Field(None, description="策略名，首次必传")
    action: str = Field(..., description="操作类型: chat / generate_fields / resume")
    message: Optional[str] = Field(None, description="用户消息（action=chat 时必传）")


def _get_service() -> AssistService:
    """创建服务实例"""
    db = get_database()
    repo = SqliteAssistRepository(db)
    llm = LLMClient()
    return AssistService(repo, llm)


async def _event_gen(service: AssistService, req: InspireRequest, request: Request):
    """SSE 事件生成器"""
    try:
        if req.action == "resume":
            # 恢复会话 — 非流式 JSON
            if not req.session_id:
                yield f"data: {json.dumps({'error': 'session_id 不能为空'})}\n\n"
                return
            try:
                data = await service.resume_session(req.session_id)
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            except ValueError as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        # 获取或创建会话
        if req.session_id:
            session = await service.get_session(req.session_id)
            if not session:
                yield f"data: {json.dumps({'error': '会话不存在'})}\n\n"
                return
        else:
            if not req.strategy:
                yield f"data: {json.dumps({'error': '首次请求必须提供 strategy'})}\n\n"
                return
            session = await service.get_or_create_session(req.novel_id, req.strategy)
            # 发送 session_created 事件
            yield (
                f"event: session_created\n"
                f"data: {json.dumps({'session_id': session.id, 'strategy': session.strategy.value})}\n\n"
            )

        if req.action == "chat":
            if not req.message:
                yield f"data: {json.dumps({'error': 'message 不能为空'})}\n\n"
                return

            # 流式对话
            async for chunk in service.chat(session, req.message):
                if await request.is_disconnected():
                    break
                yield f"event: chat_chunk\ndata: {json.dumps({'content': chunk})}\n\n"

            # 发送完成事件
            yield f"event: chat_done\ndata: {json.dumps({'message_id': f'msg_{session.id}'})}\n\n"

        elif req.action == "generate_fields":
            # 字段提取（非流式）
            fields = await service.generate_fields(session)
            yield (
                f"event: fields_done\n"
                f"data: {json.dumps(fields.to_dict(), ensure_ascii=False)}\n\n"
            )

        else:
            yield f"data: {json.dumps({'error': f'未知 action: {req.action}'})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@router.post("/assist/inspire", tags=["灵感助手"])
async def inspire(request: Request, body: InspireRequest):
    """灵感助手 SSE 流式端点"""
    service = _get_service()
    return StreamingResponse(
        _event_gen(service, body, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 3: 验证语法**

```bash
python -c "from interfaces.api.v1.assist.inspire_routes import router; print('OK')"
```

- [ ] **Step 4: 提交**

```bash
git add interfaces/api/v1/assist/
git commit -m "feat(assist): add SSE streaming endpoint for inspiration assistant"
```

---

### Task 7: 路由注册 `interfaces/api/routes.py`

**文件：**
- 修改：`interfaces/api/routes.py`

- [ ] **Step 1: 在 `register_api_routes` 中注册 assist 路由**

找到 `interfaces/api/routes.py` 中的 import 区域和 `_include_registered_routes` 调用，添加两处改动：

```python
# 在 import 区域末尾添加（约第 98 行附近，anti_ai 导入之后）：
from interfaces.api.v1.assist import inspire_routes as assist_routes

# 在 _include_registered_routes 调用的元组末尾添加（anti_ai_routes 之后）：
RouterRegistration(assist_routes.router, API_V1_PREFIX),
```

具体来说，在文件中找到这两段：

**import 区域**（anti_ai 导入之后添加）：
```python
    from interfaces.api.v1.assist import inspire_routes as assist_routes
```

**_include_registered_routes 元组**（`RouterRegistration(anti_ai_routes.router, API_V1_PREFIX),` 之后添加）：
```python
            RouterRegistration(assist_routes.router, API_V1_PREFIX),
```

- [ ] **Step 2: 验证路由注册**

```bash
python -c "
from fastapi import FastAPI
from interfaces.api.routes import register_api_routes
app = FastAPI()
register_api_routes(app)
routes = [r.path for r in app.routes]
print([r for r in routes if 'assist' in r])
"
```

- [ ] **Step 3: 提交**

```bash
git add interfaces/api/routes.py
git commit -m "feat(assist): register assist routes in API router"
```

---

### Task 8: 前端 API 封装 `frontend/src/api/assist.ts`

**文件：**
- 创建：`frontend/src/api/assist.ts`

- [ ] **Step 1: 编写前端 API 模块**

```typescript
// frontend/src/api/assist.ts
/** 灵感助手 API 封装 — SSE 流式消费 — 作者：Axelton */
import { resolveHttpUrl } from './config'

export interface AssistSessionInfo {
  session_id: string
  strategy: string
}

export interface AssistMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  field_suggestions?: Record<string, unknown>
  created_at: string
}

export interface AssistResumeData {
  session_id: string
  strategy: string
  status: string
  messages: AssistMessage[]
}

export interface AssistFieldData {
  title: string
  premise: string
  genre: string
  world_preset: string
  story_structure: string
  pacing_control: string
  writing_style: string
  special_requirements: string
}

export interface AssistChatHandlers {
  onSessionCreated?: (info: AssistSessionInfo) => void
  onChatChunk?: (content: string) => void
  onChatDone?: (messageId: string) => void
  onFieldsDone?: (fields: AssistFieldData) => void
  onResumeDone?: (data: AssistResumeData) => void
  onError?: (error: string) => void
}

/**
 * 发起 SSE 请求到灵感助手
 * 返回 AbortController 用于取消
 */
export function subscribeAssist(
  body: {
    novel_id: string
    session_id?: string
    strategy?: string
    action: 'chat' | 'generate_fields' | 'resume'
    message?: string
  },
  handlers: AssistChatHandlers,
): AbortController {
  const ctrl = new AbortController()

  void (async () => {
    try {
      const url = resolveHttpUrl('/api/v1/assist/inspire')
      const res = await fetch(url, {
        method: 'POST',
        signal: ctrl.signal,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache',
        },
        body: JSON.stringify(body),
      })

      if (!res.ok || !res.body) {
        handlers.onError?.(`HTTP ${res.status}`)
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      const flushBlocks = (buf: string): string => {
        let sepIdx: number
        let rest = buf
        while ((sepIdx = rest.indexOf('\n\n')) >= 0) {
          const block = rest.slice(0, sepIdx)
          rest = rest.slice(sepIdx + 2)

          let eventType = ''
          let dataStr = ''

          for (const line of block.split('\n')) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7)
            } else if (line.startsWith('data: ')) {
              dataStr = line.slice(6)
            }
          }

          if (!dataStr) continue
          try {
            const payload = JSON.parse(dataStr)

            if (payload.error) {
              handlers.onError?.(payload.error)
              continue
            }

            switch (eventType) {
              case 'session_created':
                handlers.onSessionCreated?.(payload as AssistSessionInfo)
                break
              case 'chat_chunk':
                handlers.onChatChunk?.(payload.content || '')
                break
              case 'chat_done':
                handlers.onChatDone?.(payload.message_id || '')
                break
              case 'fields_done':
                handlers.onFieldsDone?.(payload as AssistFieldData)
                break
              default:
                // resume 的 data 无 event type，直接是 JSON
                if (payload.messages) {
                  handlers.onResumeDone?.(payload as AssistResumeData)
                }
            }
          } catch {
            /* 忽略解析失败的行 */
          }
        }
        return rest
      }

      while (true) {
        const { done, value } = await reader.read()
        if (value) buffer += decoder.decode(value, { stream: true })
        buffer = flushBlocks(buffer)
        if (done) {
          buffer += decoder.decode()
          buffer = flushBlocks(buffer)
          break
        }
      }
    } catch (e) {
      if (e instanceof Error && e.name === 'AbortError') return
      handlers.onError?.(e instanceof Error ? e.message : '流连接异常')
    }
  })()

  return ctrl
}
```

- [ ] **Step 2: TypeScript 类型检查**

```bash
cd frontend && npx vue-tsc --noEmit src/api/assist.ts 2>&1 | head -20
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/api/assist.ts
git commit -m "feat(assist): add frontend SSE API wrapper"
```

---

### Task 9: 灵感助手弹窗组件 `InspirationAssistantModal.vue`

**文件：**
- 创建：`frontend/src/components/inspiration/InspirationAssistantModal.vue`
- 创建：`frontend/src/components/inspiration/` 目录

- [ ] **Step 1: 编写弹窗组件**

```vue
<!-- frontend/src/components/inspiration/InspirationAssistantModal.vue -->
<!-- 灵感助手多轮对话弹窗 — 作者：Axelton -->
<template>
  <n-modal
    v-model:show="visible"
    preset="card"
    :title="null"
    :style="{ width: '92vw', maxWidth: '960px', height: '80vh', marginTop: '8vh' }"
    :bordered="true"
    :segmented="{ content: true, footer: 'soft' }"
    :mask-closable="true"
    :close-on-esc="true"
    @update:show="handleClose"
  >
    <template #header>
      <div class="assist-header">
        <span class="assist-header-title">灵感助手</span>
        <n-select
          v-model:value="currentStrategy"
          :options="strategyOptions"
          size="small"
          :style="{ width: '160px' }"
          :disabled="isSessionActive"
        />
      </div>
    </template>

    <div class="assist-body">
      <!-- 对话区 -->
      <div class="assist-chat" ref="chatContainerRef">
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="chat-message"
          :class="`chat-${msg.role}`"
        >
          <div class="chat-avatar">
            {{ msg.role === 'user' ? '😀' : '🤖' }}
          </div>
          <div class="chat-bubble">
            {{ msg.content }}
          </div>
        </div>
        <!-- 流式输出中的气泡 -->
        <div v-if="streamingContent" class="chat-message chat-assistant">
          <div class="chat-avatar">🤖</div>
          <div class="chat-bubble chat-streaming">{{ streamingContent }}</div>
        </div>
        <!-- 空状态引导 -->
        <div v-if="messages.length === 0 && !streamingContent" class="chat-empty">
          <p class="chat-empty-title">告诉我你的想法，或让灵感助手帮你找到方向</p>
          <p class="chat-empty-hint">{{ strategyHint }}</p>
        </div>
      </div>

      <!-- 侧栏：字段预览 -->
      <div class="assist-sidebar">
        <div class="sidebar-title">字段预览</div>
        <div class="field-list">
          <div class="field-item">
            <span class="field-label">书名</span>
            <span class="field-value" :class="{ empty: !fieldData.title }">
              {{ fieldData.title || '—' }}
            </span>
          </div>
          <div class="field-item">
            <span class="field-label">简介</span>
            <span class="field-value premise" :class="{ empty: !fieldData.premise }">
              {{ fieldData.premise || '—' }}
            </span>
          </div>
          <div class="field-item">
            <span class="field-label">大类</span>
            <span class="field-value" :class="{ empty: !fieldData.genre }">
              {{ fieldData.genre || '—' }}
            </span>
          </div>
          <div class="field-item">
            <span class="field-label">世界观基调</span>
            <span class="field-value" :class="{ empty: !fieldData.world_preset }">
              {{ fieldData.world_preset || '—' }}
            </span>
          </div>
          <div class="field-item">
            <span class="field-label">剧情结构</span>
            <span class="field-value" :class="{ empty: !fieldData.story_structure }">
              {{ fieldData.story_structure || '—' }}
            </span>
          </div>
          <div class="field-item">
            <span class="field-label">节奏把控</span>
            <span class="field-value" :class="{ empty: !fieldData.pacing_control }">
              {{ fieldData.pacing_control || '—' }}
            </span>
          </div>
          <div class="field-item">
            <span class="field-label">写作风格</span>
            <span class="field-value" :class="{ empty: !fieldData.writing_style }">
              {{ fieldData.writing_style || '—' }}
            </span>
          </div>
          <div class="field-item">
            <span class="field-label">特殊要求</span>
            <span class="field-value" :class="{ empty: !fieldData.special_requirements }">
              {{ fieldData.special_requirements || '—' }}
            </span>
          </div>
        </div>
        <n-button
          type="primary"
          block
          :disabled="!hasFields"
          @click="handleFillForm"
          style="margin-top: 16px"
        >
          填充到表单
        </n-button>
        <n-button
          type="default"
          block
          :loading="generatingFields"
          :disabled="messages.length === 0"
          @click="handleGenerateFields"
          style="margin-top: 8px"
        >
          生成字段
        </n-button>
      </div>
    </div>

    <!-- 底部输入区 -->
    <template #footer>
      <div class="assist-footer">
        <n-input
          v-model:value="inputMessage"
          placeholder="说说你的想法…"
          :disabled="sending"
          @keydown.enter="handleSend"
          clearable
          round
          size="large"
        />
        <n-button
          type="primary"
          circle
          :loading="sending"
          :disabled="!inputMessage.trim()"
          @click="handleSend"
        >
          <template #icon>
            <n-icon>
              <svg viewBox="0 0 24 24" width="18" height="18">
                <path fill="currentColor" d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            </n-icon>
          </template>
        </n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { NModal, NSelect, NInput, NButton, NIcon, useMessage } from 'naive-ui'
import { subscribeAssist, type AssistFieldData, type AssistMessage } from '@/api/assist'

const emit = defineEmits<{
  (e: 'fill-fields', fields: AssistFieldData): void
}>()

const props = defineProps<{
  show: boolean
  novelId: string
}>()

const message = useMessage()

const visible = computed({
  get: () => props.show,
  set: (val: boolean) => {
    if (!val) emit('fill-fields', {} as AssistFieldData) // 关闭信号通过特殊值
  },
})

const currentStrategy = ref('brainstorm')
const isSessionActive = ref(false)
const sessionId = ref<string | null>(null)
const messages = ref<AssistMessage[]>([])
const inputMessage = ref('')
const sending = ref(false)
const generatingFields = ref(false)
const streamingContent = ref('')
const fieldData = ref<AssistFieldData>({} as AssistFieldData)
const chatContainerRef = ref<HTMLElement | null>(null)

const strategyOptions = [
  { label: '脑洞爆破', value: 'brainstorm' },
  { label: '世界观优先', value: 'world_first' },
  { label: '角色驱动', value: 'character_driven' },
  { label: '主题先行', value: 'theme_first' },
]

const strategyHints: Record<string, string> = {
  brainstorm: '随便聊聊吧！你最近对什么故事感兴趣？看过什么让你印象深刻的作品？',
  world_first: '如果有一个世界，它的规则和我们的完全不同，你最想改变什么？',
  character_driven: '你心中有没有一个模糊的人物形象？他/她最大的愿望是什么？',
  theme_first: '有没有一个主题或议题你一直想探讨？比如自由、复仇、成长…',
}

const strategyHint = computed(() => strategyHints[currentStrategy.value] || '')

const hasFields = computed(() => {
  const fd = fieldData.value
  return !!(fd.title || fd.genre || fd.premise)
})

function scrollToBottom() {
  nextTick(() => {
    const el = chatContainerRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

async function handleSend() {
  const text = inputMessage.value.trim()
  if (!text || sending.value || generatingFields.value) return

  inputMessage.value = ''
  sending.value = true
  streamingContent.value = ''

  // 添加用户消息到本地列表
  const userMsg: AssistMessage = {
    id: `local_${Date.now()}`,
    role: 'user',
    content: text,
    created_at: new Date().toISOString(),
  }
  messages.value.push(userMsg)
  scrollToBottom()

  // 发起 SSE
  const ctrl = subscribeAssist(
    {
      novel_id: props.novelId,
      session_id: sessionId.value || undefined,
      strategy: isSessionActive.value ? undefined : currentStrategy.value,
      action: 'chat',
      message: text,
    },
    {
      onSessionCreated(info) {
        sessionId.value = info.session_id
        isSessionActive.value = true
      },
      onChatChunk(content) {
        streamingContent.value += content
        scrollToBottom()
      },
      onChatDone() {
        // 将流式内容转为正式消息
        if (streamingContent.value) {
          messages.value.push({
            id: `ai_${Date.now()}`,
            role: 'assistant',
            content: streamingContent.value,
            created_at: new Date().toISOString(),
          })
        }
        streamingContent.value = ''
        sending.value = false
      },
      onError(err) {
        message.error(err)
        sending.value = false
        streamingContent.value = ''
      },
    },
  )
}

async function handleGenerateFields() {
  if (!sessionId.value || generatingFields.value) return
  generatingFields.value = true

  subscribeAssist(
    {
      novel_id: props.novelId,
      session_id: sessionId.value,
      action: 'generate_fields',
    },
    {
      onFieldsDone(fields) {
        fieldData.value = fields
        generatingFields.value = false
      },
      onError(err) {
        message.error(err)
        generatingFields.value = false
      },
    },
  )
}

function handleFillForm() {
  emit('fill-fields', fieldData.value)
  message.success('已填充到表单')
}

function handleClose(_show: boolean) {
  // modal 关闭不做额外操作，会话已持久化
}
</script>

<style scoped>
.assist-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.assist-header-title {
  font-size: 17px;
  font-weight: 700;
}

.assist-body {
  display: flex;
  gap: 16px;
  height: calc(80vh - 160px);
  min-height: 360px;
}

.assist-chat {
  flex: 1;
  overflow-y: auto;
  padding-right: 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-message {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.chat-user {
  flex-direction: row-reverse;
}

.chat-avatar {
  font-size: 24px;
  flex-shrink: 0;
  width: 32px;
  text-align: center;
}

.chat-bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  background: var(--app-surface-subtle);
  color: var(--app-text-primary);
}

.chat-user .chat-bubble {
  background: var(--color-brand, #4f46e5);
  color: #fff;
}

.chat-streaming {
  border: 1px dashed var(--color-brand-border, rgba(79, 70, 229, 0.3));
}

.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  gap: 8px;
  color: var(--app-text-muted);
}

.chat-empty-title {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
}

.chat-empty-hint {
  font-size: 13px;
  max-width: 320px;
  margin: 0;
}

.assist-sidebar {
  width: 220px;
  flex-shrink: 0;
  border-left: 1px solid var(--app-border);
  padding-left: 16px;
  overflow-y: auto;
}

.sidebar-title {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 12px;
  color: var(--app-text-primary);
}

.field-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.field-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.field-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--app-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.field-value {
  font-size: 13px;
  color: var(--app-text-primary);
  word-break: break-all;
}

.field-value.empty {
  color: var(--app-text-muted);
  font-style: italic;
}

.field-value.premise {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.assist-footer {
  display: flex;
  align-items: center;
  gap: 10px;
}

.assist-footer :deep(.n-input) {
  flex: 1;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .assist-body {
    flex-direction: column;
    height: calc(80vh - 140px);
  }

  .assist-sidebar {
    width: 100%;
    border-left: none;
    border-top: 1px solid var(--app-border);
    padding-left: 0;
    padding-top: 12px;
    flex-shrink: 0;
  }

  .field-list {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
}
</style>
```

- [ ] **Step 2: TypeScript 类型检查**

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | head -30
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/inspiration/
git commit -m "feat(assist): add InspirationAssistantModal component"
```

---

### Task 10: 集成到 Home.vue

**文件：**
- 修改：`frontend/src/views/Home.vue`

- [ ] **Step 1: 在「高级」按钮旁添加「灵感助手」按钮**

在 `create-header` div 中（第 61-66 行，「高级」按钮后面）添加灵感助手按钮：

```vue
<!-- 找到 create-header div，在「高级」按钮后添加： -->
<n-button
  text
  type="info"
  @click="showInspireAssistant = true"
  style="margin-left: 8px"
>
  <template #icon>
    <n-icon><IconBulb /></n-icon>
  </template>
  灵感助手
</n-button>
```

同时需要在模板末尾（`</template>` 之前）添加弹窗组件挂载点：

```vue
<!-- 灵感助手弹窗 -->
<InspirationAssistantModal
  v-if="showInspireAssistant"
  :show="showInspireAssistant"
  :novel-id="'__preview__'"
  @fill-fields="handleInspireFill"
  @update:show="(val: boolean) => { if (!val) showInspireAssistant = false }"
/>
```

- [ ] **Step 2: 在 script 中添加对应逻辑**

在 `<script setup>` 中：

添加图标定义（在现有 Icon 定义区域）：
```typescript
const IconBulb = () =>
  h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', width: '1em', height: '1em' },
    h('path', { fill: 'currentColor', d: 'M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7zm2.85 11.1l-.85.6V16h-4v-2.3l-.85-.6A4.997 4.997 0 0 1 7 9c0-2.76 2.24-5 5-5s5 2.24 5 5c0 1.63-.8 3.16-2.15 4.1z' }))
```

添加 reactive 状态变量（在其他 ref 旁边）：
```typescript
const showInspireAssistant = ref(false)
```

添加 `defineAsyncComponent` 导入弹窗组件（在 MarketTaxonomyPicker 附近）：
```typescript
const InspirationAssistantModal = defineAsyncComponent(
  () => import('@/components/inspiration/InspirationAssistantModal.vue'),
)
```

添加 `handleInspireFill` 函数：
```typescript
/** 灵感助手字段填充处理 */
function handleInspireFill(fields: { title?: string; premise?: string; genre?: string; world_preset?: string; story_structure?: string; pacing_control?: string; writing_style?: string; special_requirements?: string }) {
  if (!fields || Object.keys(fields).length === 0) {
    showInspireAssistant.value = false
    return
  }
  if (fields.title) newBook.value.title = fields.title
  if (fields.premise) newBook.value.premise = fields.premise
  if (fields.genre) newBook.value.genre = fields.genre
  if (fields.world_preset) newBook.value.worldPreset = fields.world_preset
  if (fields.story_structure) newBook.value.storyStructure = fields.story_structure
  if (fields.pacing_control) newBook.value.pacingControl = fields.pacing_control
  if (fields.writing_style) newBook.value.writingStyle = fields.writing_style
  if (fields.special_requirements) newBook.value.specialRequirements = fields.special_requirements
  showInspireAssistant.value = false
  message.success('已填充灵感助手生成的内容，可继续修改后创建')
}
```

- [ ] **Step 3: 类型检查和构建验证**

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | head -30
cd frontend && npm run build 2>&1 | tail -20
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/views/Home.vue
git commit -m "feat(assist): integrate InspirationAssistant into Home.vue"
```

---

### Task 11: 端到端验证

- [ ] **Step 1: 启动后端**

```bash
uvicorn interfaces.main:app --host 127.0.0.1 --port 8005 --reload &
sleep 3
```

- [ ] **Step 2: 测试 API 端点可访问**

```bash
# 测试 resume（无 session 时）
curl -s http://127.0.0.1:8005/api/v1/assist/inspire \
  -H 'Content-Type: application/json' \
  -d '{"novel_id":"test-001","action":"resume","session_id":"nonexistent"}' \
  | head -5
```

- [ ] **Step 3: 启动前端并手动验证**

```bash
cd frontend && npm run dev &
# 打开 http://localhost:3000
# 1. 验证「灵感助手」按钮出现在「高级」旁边
# 2. 点击打开弹窗 → 选择策略 → 发送消息 → 观察 SSE 流式回复
# 3. 点击「生成字段」→ 右侧预览更新
# 4. 点击「填充表单」→ 字段写入新建书目表单
# 5. 关闭弹窗后重新打开 → 会话恢复
```

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "chore(assist): end-to-end verification notes"
```
