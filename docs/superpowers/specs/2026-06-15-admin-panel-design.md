# 后台管理模块设计规格 — 作者：Axelton

> **目标**：在 PlotPilot 现有项目内新增一个自包含的后台管理模块，尽量不修改现有代码。

---

## 1. 概述

### 1.1 功能范围

| 模块 | 功能 | 权限 |
|------|------|------|
| 驾驶舱大屏 | 六维度统计图表仪表盘 | admin 看全局，普通用户看自己 |
| 用户管理 | 列表、创建、编辑角色、删除 | 仅 admin |
| 书籍管理 | 列表、详情、删除、转移归属 | 仅 admin |

### 1.2 设计原则

- **自包含**：admin 代码全部放在独立目录，通过路由注册挂载
- **零侵入**：不修改现有 Repository / Service / 业务逻辑
- **读优于写**：dashboard 统计通过原始 SQL 直接聚合，不走业务 Service
- **移动端适配**：侧边栏架构在移动端切换为顶栏 + 抽屉菜单

---

## 2. 前端设计

### 2.1 路由结构

```
/admin                  → AdminLayout.vue  (侧边栏/移动端抽屉)
  /admin/dashboard      → DashboardView.vue
  /admin/users          → UserListView.vue   (admin only)
  /admin/books          → BookListView.vue   (admin only)
```

**路由守卫**：
- 全局 `beforeEnter` 检查 `authStore.isAuthenticated`（复用现有守卫）
- `/admin/users` 和 `/admin/books` 额外 `beforeEnter` 检查 `authStore.isAdmin`
- 非 admin 访问管理子路由 → 重定向 `/admin/dashboard` + 提示无权访问

**现有代码改动**：仅 `frontend/src/router/index.ts` 加 `adminRoutes` 数组并注册。

### 2.2 文件结构

```
frontend/src/
├── views/admin/
│   ├── AdminLayout.vue              ← 响应式布局壳
│   ├── DashboardView.vue            ← 驾驶舱 (组合 6 个面板)
│   ├── UserListView.vue             ← 用户管理页
│   ├── BookListView.vue             ← 书籍管理页
│   └── components/
│       ├── WritingStatsPanel.vue     ← 写作产出面板
│       ├── AiUsagePanel.vue         ← AI 调用面板
│       ├── UserBookPanel.vue        ← 用户 & 书籍面板
│       ├── QualityPanel.vue         ← 叙事质量面板
│       ├── CharacterForeshadowPanel.vue ← 人物 & 伏笔面板
│       ├── SystemPanel.vue          ← 系统运行面板
│       ├── StatCard.vue             ← 通用数字卡片
│       └── AdminMobileTopBar.vue    ← 移动端顶栏
├── api/
│   └── admin.ts                     ← admin API 封装
└── router/
    └── index.ts                     ← 添加 adminRoutes (仅此文件修改)
```

### 2.3 AdminLayout 响应式布局

**桌面端** (`min-width: 768px`)：
```
┌──────────┬──────────────────────────────┐
│ 侧边栏   │  <router-view />             │
│ n-menu   │                              │
│ 200px    │                              │
│          │                              │
│ 驾驶舱   │                              │
│ 用户管理 │                              │
│ 书籍管理 │                              │
└──────────┴──────────────────────────────┘
```

**移动端** (`max-width: 767px`)：
```
┌──────────────────────────────┐
│ ☰ 驾驶舱                     │  ← AdminMobileTopBar
├──────────────────────────────┤
│                              │
│  <router-view />             │
│                              │
└──────────────────────────────┘

点击 ☰ → n-drawer 从左侧滑出菜单
```

- 使用项目已有 `useIsMobile` composable 判断设备
- 侧边栏菜单项：admin 看到全部 3 项，普通用户只看到"驾驶舱"一项

### 2.4 仪表盘布局

DashboardView 用 CSS Grid 自适应：

**桌面端**：3 列网格 (6 面板)
**平板端**：2 列网格
**移动端**：单列堆叠

每个面板内部图表使用 ECharts（项目已有此依赖），`grid` / `legend` 位置按容器宽度动态调整。

### 2.5 图表清单

#### 面板 1：写作产出 (WritingStatsPanel)

| 图表 | ECharts 类型 | 数据说明 |
|------|-------------|---------|
| 日写作量趋势 | 折线图 (line) | 近 30 天每天新增字数 |
| 章节完成分布 | 柱状图 (bar) | Top 10 书籍章节数对比 |
| 完本率 | 环形图 (pie, radius) | completed vs in_progress vs planning |
| 累计总览 | 数字卡片 (StatCard) | 总字数 / 总章节 / 平均每章字数 |

#### 面板 2：AI 调用 (AiUsagePanel)

| 图表 | ECharts 类型 | 数据说明 |
|------|-------------|---------|
| 调用量趋势 | 面积图 (line, areaStyle) | 近 30 天 LLM 调用次数 |
| Token 消耗 | 柱状图 (bar) | 按模型分组 Token 用量 |
| 模型占比 | 饼图 (pie) | 各模型调用次数占比 |
| 关键指标 | 数字卡片 | 今日调用 / 今日 Token / 平均延迟 |

#### 面板 3：用户 & 书籍 (UserBookPanel)

| 图表 | ECharts 类型 | 数据说明 |
|------|-------------|---------|
| 书籍阶段分布 | 横向柱状图 (bar, xAxis/yAxis 互换) | 各阶段书籍数量 |
| 新书创建趋势 | 折线图 (line) | 近 12 周每周新书数 |
| 活跃度 | 数字卡片 | 总用户 / 总书籍 / 本周活跃书籍 |
| 用户书籍排行 | n-data-table | Top 10 用户 + 书籍数 + 总字数 |

#### 面板 4：叙事质量 (QualityPanel)

| 图表 | ECharts 类型 | 数据说明 |
|------|-------------|---------|
| 伏笔闭合率 | 仪表盘 (gauge) | 已闭合 / 总伏笔 百分比 |
| 审核通过率 | 环形图 (pie, radius) | 通过 vs 需修改 |
| 风格一致性趋势 | 折线图 (line) | 近 30 天 style_score |
| 待处理问题 | 数字卡片 | 漂流告警数 / 待闭合伏笔数 |

#### 面板 5：人物 & 伏笔 (CharacterForeshadowPanel)

| 图表 | ECharts 类型 | 数据说明 |
|------|-------------|---------|
| 出场人物统计 | 柱状图 (bar) | Top 10 书籍人物数量 |
| 人物类型分布 | 饼图 (pie) | 主角 / 配角 / 龙套 |
| 伏笔状态分布 | 堆叠柱状图 (bar, stack) | planted / triggered / closed |
| 伏笔密度趋势 | 折线图 (line) | 每章平均伏笔数变化 |

#### 面板 6：系统运行 (SystemPanel)

| 图表 | ECharts 类型 | 数据说明 |
|------|-------------|---------|
| 自动驾驶队列 | 数字卡片 | 运行中 / 等待中 / 错误 |
| 24h 错误率 | 折线图 (line) | 每小时错误次数 |
| 响应延迟 | 折线图 (line, 多系列) | P50 / P95 / P99 |
| 健康状态 | 状态卡片 (StatCard) | DB / ChromaDB / LLM 连通性 |

---

## 3. 后端 API 设计

### 3.1 文件结构

```
interfaces/api/v1/admin/
├── __init__.py
├── dashboard_routes.py      ← GET /api/v1/admin/dashboard
├── user_routes.py           ← CRUD /api/v1/admin/users
└── book_routes.py           ← GET/DELETE /api/v1/admin/books

application/admin/
├── __init__.py
├── dashboard_service.py     ← 聚合统计查询
├── user_admin_service.py    ← 用户管理编排
└── book_admin_service.py    ← 书籍管理编排
```

**现有代码改动**：仅 `interfaces/api/routes.py` 加 3 行路由注册。

### 3.2 驾驶舱 API

```
GET /api/v1/admin/dashboard
  Query: scope=all|user  (默认: admin→all, user→user)
  Auth: get_current_user
  Response: {
    writing: {
      total_words: int,
      total_chapters: int,
      completed_novels: int,
      avg_words_per_chapter: float,
      daily_trend: [{ date, word_count }]      // 近 30 天
    },
    ai_usage: {
      total_calls: int,
      total_tokens: int,
      today_calls: int,
      today_tokens: int,
      avg_latency_ms: float,
      by_model: [{ model, calls, tokens }],
      daily_trend: [{ date, call_count }]      // 近 30 天
    },
    books: {
      total: int,
      active_this_week: int,
      by_stage: { planning, writing, auditing, completed },
      weekly_new_trend: [{ week, count }]      // 近 12 周
    },
    quality: {
      foreshadow_closure_rate: float,
      avg_style_score: float,
      audit_pass_rate: float,
      drift_alerts: int,
      open_foreshadows: int
    },
    cast_foreshadow: {
      avg_characters_per_novel: float,
      total_foreshadows: int,
      by_status: { planted, triggered, closed },
      character_type_distribution: { protagonist, supporting, minor },
      top_novels_by_characters: [{ novel_id, title, character_count }],
      top_novels_by_foreshadows: [{ novel_id, title, foreshadow_count }]
    },
    system: {
      autopilot_running: int,
      autopilot_waiting: int,
      autopilot_errors: int,
      error_rate_24h: [{ hour, error_count }],
      latency_p50: float,
      latency_p95: float,
      latency_p99: float,
      health: { db: bool, chromadb: bool, llm: bool }
    }
  }
```

**实现方式**：`DashboardService` 通过 `DatabaseConnection.fetch_all()` 直接执行聚合 SQL。scope=user 时所有查询加 `WHERE user_id = ?` 或 `WHERE novel_id IN (SELECT id FROM novels WHERE user_id = ?)`。

### 3.3 用户管理 API

所有端点 `require_admin`：

```
GET  /api/v1/admin/users
  Query: page, page_size, search (username 模糊搜索)
  Response: PaginatedResponse<UserDTO>

POST /api/v1/admin/users
  Body: { username, password, role }
  Response: SuccessResponse<UserDTO>
  逻辑：复用 AuthService.register()

PATCH /api/v1/admin/users/{id}
  Body: { role?, password? }
  Response: SuccessResponse<UserDTO>
  逻辑：更新角色或重置密码（bcrypt 重哈希）

DELETE /api/v1/admin/users/{id}
  Response: SuccessResponse
  约束：不能删除自己，若用户拥有书籍则提示先转移
```

### 3.4 书籍管理 API

```
GET  /api/v1/admin/books
  Query: page, page_size, search (标题模糊), user_id (过滤), stage (过滤)
  Response: PaginatedResponse<AdminBookDTO>  (含统计摘要)

GET  /api/v1/admin/books/{id}
  Response: AdminBookDetailDTO  (含字数、章节数、人物数、伏笔数等)

DELETE /api/v1/admin/books/{id}
  逻辑：级联删除所有相关数据（chapters, triples, story_nodes 等）

PATCH /api/v1/admin/books/{id}/owner
  Body: { user_id }
  Response: SuccessResponse
```

### 3.5 应用服务：DashboardService

直接在 `DatabaseConnection` 上执行聚合 SQL，示例：

```python
# 日写作量趋势
SELECT DATE(created_at) as date,
       SUM(LENGTH(content)) as word_count
FROM chapters
WHERE novel_id IN (...)   -- scope=user 时注入
  AND created_at >= DATE('now', '-30 days')
GROUP BY DATE(created_at)
ORDER BY date

# 各阶段分布
SELECT current_stage, COUNT(*) as cnt
FROM novels
WHERE (user_id = ? OR ? IS NULL)   -- scope 参数化
GROUP BY current_stage
```

### 3.6 应用服务：UserAdminService

编排用户 CRUD，组合现有 `UserRepository` 和 `AuthService`：
- `list_users()` → `UserRepository.count()` + `get_by_username()` 模糊搜索
- `create_user()` → `AuthService.register()`
- `update_user()` → 读 → 修改 → `UserRepository.save()`
- `delete_user()` → 检查是否拥有书籍 → `UserRepository.delete()`

### 3.7 应用服务：BookAdminService

编排书籍管理操作：
- `list_books()` → `NovelRepository.list_all()` + 统计聚合
- `get_book_detail()` → 组合多个 Repository 获取字数/章节/人物/伏笔统计
- `delete_book()` → 收集所有关联表 → 事务性级联删除
- `transfer_owner()` → `NovelRepository.patch(user_id=new_id)`

---

## 4. 权限矩阵

| 端点 | admin | user |
|------|-------|------|
| `GET /admin/dashboard` | 全局数据 | 仅自己书籍数据 |
| `GET /admin/users` | 全部用户 | 403 |
| `POST /admin/users` | 创建用户 | 403 |
| `PATCH /admin/users/{id}` | 更新/重置 | 403 |
| `DELETE /admin/users/{id}` | 删除 | 403 |
| `GET /admin/books` | 全部书籍 | 403 |
| `GET /admin/books/{id}` | 详情 | 403 |
| `DELETE /admin/books/{id}` | 删除 | 403 |
| `PATCH /admin/books/{id}/owner` | 转移 | 403 |

仪表盘权限在返回数据时按 scope 过滤，不返回 403。

---

## 5. 技术栈

| 层 | 技术 |
|----|------|
| 前端框架 | Vue 3 (Composition API) + TypeScript |
| UI 组件 | Naive UI (n-menu, n-layout, n-drawer, n-data-table, n-card, n-grid) |
| 图表 | ECharts 5 (项目已有依赖) |
| 状态 | Pinia (复用 authStore) |
| 响应式 | 复用 useIsMobile composable |
| 后端框架 | FastAPI (APIRouter + Depends) |
| 认证 | 复用 JWT + get_current_user / require_admin |
| 数据库 | SQLite (通过 DatabaseConnection.fetch_all) |
| 密码哈希 | bcrypt (复用 AuthService) |

---

## 6. 自检清单

- [x] 无占位符 (TBD/TODO)
- [x] 图表维度与 API 字段一一对应
- [x] 权限矩阵覆盖所有端点
- [x] 移动端方案明确
- [x] 声明了现有代码改动范围（仅路由注册，2 处）
- [x] 数据库无需新增表或字段
