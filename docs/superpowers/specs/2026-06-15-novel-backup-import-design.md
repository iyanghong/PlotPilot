# 小说数据导出/导入 — 设计规格

## 背景

PlotPilot 用 SQLite 存储全部数据（~90 张表，约 60 张含 `novel_id`），未来可能迁移到 MySQL/PG。用户需要将某本小说的全部关联数据导出为可移植文件，并支持在相同或不同数据库后端中导入还原。

## 目标

- 导出：将指定 `novel_id` 的所有关联表数据 + ChromaDB 向量打包为一个 `.zip` 文件
- 导入：从 `.zip` 文件还原全部数据，覆盖模式（清空目标 novel_id 后导入）
- 数据库无关：导出格式不依赖 SQLite 专属特性，后期换 MySQL/PG 仍可导入
- 操作入口：前端按钮 + API

## 技术方案：JSON + ChromaDB 导出 ZIP

### 为什么 JSON 而非 SQLite 文件

| 维度 | JSON | SQLite 文件 |
|------|------|-------------|
| 跨数据库移植 | 通过 ORM/原生 SQL 写入任意 DB | 只能 ATTACH 到 SQLite |
| 人类可读 | 可查看/编辑 | 二进制 |
| 版本控制 | git diff 友好 | 不支持 |
| 导入性能 | 逐行 INSERT | ATTACH 一键（仅 SQLite） |

### 导出格式

```
novel_{title}_{date}.zip
├── data.json              ← 所有表数据
│   {
│     "version": "1.0",
│     "novel_id": "nov_abc123",
│     "exported_at": "2026-06-15T10:30:00Z",
│     "source_db_type": "sqlite",
│     "tables": {
│       "novels": [{"id": "nov_abc123", "title": "...", ...}],
│       "chapters": [{"id": "...", "novel_id": "nov_abc123", "number": 1, "content": "...", ...}, ...],
│       "bibles": [...],
│       "story_nodes": [...],
│       "unified_characters": [...],
│       ... (所有含 novel_id 或关联到此小说的表)
│     }
│   }
└── chromadb/             ← 向量数据，按 collection 分 JSON 文件
    ├── chapter_content.json
    └── knowledge_triples.json
```

### API 端点

```
GET  /api/v1/core/novels/{novel_id}/backup
     → Content-Type: application/zip
     → Content-Disposition: attachment; filename="{小说标题}_{日期}.zip"
     → 响应: StreamingResponse（边构建边传输）

POST /api/v1/core/novels/{novel_id}/backup/restore
     → Content-Type: multipart/form-data
     → body: file（.zip 文件）
     → 响应: {"success": true, "stats": {"tables": 60, "total_rows": 1234}}
```

## 架构设计

### 后端分层

```
interfaces/api/v1/core/backup_routes.py    ← API 路由层
application/core/services/novel_backup_service.py  ← 应用服务层
infrastructure/persistence/backup/                    ← 基础设施层
  ├── data_exporter.py    ← 表数据导出
  ├── data_importer.py    ← 表数据导入
  └── chromadb_exporter.py ← 向量数据导出/导入
```

### 数据导出流程

1. **动态表发现**：查询 `sqlite_master` 获取所有表名，通过 `PRAGMA table_info` 判断哪些表包含 `novel_id` 列
2. **全局表特殊处理**：`novels`、`users` 等全局表仅导出与目标 novel_id 关联的行（通过 WHERE novel_id = ?）
3. **关联表发现**：部分表不直接含 `novel_id` 但通过外键关联（如 `assist_messages` 通过 `session_id` → `assist_sessions.novel_id`），需要 JOIN 导出
4. **流式 JSON 写入**：使用 `ijson` 或逐行写入方式，避免将整本小说（可能数 MB 正文）一次性加载到内存
5. **ChromaDB 向量导出**：通过 ChromaDB `collection.get()` 获取该小说所有章节的嵌入向量
6. **ZIP 打包**：`zipfile.ZipFile` 流式写入 `data.json` + `chromadb/` 目录

### 数据导入流程

1. **ZIP 解压**：解压到临时目录
2. **校验**：检查 `data.json` 结构、`version` 兼容性、`novel_id` 是否匹配路径参数
3. **事务性导入**：
   - 开启事务
   - 逐表 `DELETE FROM {table} WHERE novel_id = ?`（清空目标数据）
   - 逐表 `INSERT INTO {table} ({columns}) VALUES ({placeholders})`（批量插入）
   - ChromaDB 向量 `upsert()` 回写
   - 提交事务
4. **失败回滚**：任何步骤失败 → 回滚事务 + 清理临时文件 + 返回错误

### 表发现策略（避免硬编码 60 张表）

**直接关联表（含 novel_id 列）**：
```sql
SELECT name FROM sqlite_master WHERE type='table'
```
通过 `PRAGMA table_info({name})` 检查是否有 `novel_id` 列。

**间接关联表（通过外键链）**：
- `assist_sessions` → `novel_id`（直接）
- `assist_messages` → `session_id` → `assist_sessions`（间接）
  - 导出时用 JOIN：`SELECT m.* FROM assist_messages m JOIN assist_sessions s ON m.session_id = s.id WHERE s.novel_id = ?`

间接关联表需手动配置关联路径（数量有限，约 5-8 张），其余 50+ 张表都是直接 `novel_id` 关联。

### 前端设计

在 Workbench 页面（小说工作台顶部操作栏）增加两个按钮：

| 按钮 | 图标 | 行为 |
|------|------|------|
| 导出 | Download | `GET /api/v1/core/novels/{novel_id}/backup` → 触发浏览器下载 |
| 导入 | Upload | `<input type="file" accept=".zip">` → `POST /api/v1/core/novels/{novel_id}/backup/restore` |

导入成功后弹出提示："导入完成：60 张表，共 1234 行数据"，建议用户刷新页面。

## 错误处理

| 场景 | HTTP 状态码 | 处理 |
|------|------------|------|
| 导出时 novel 不存在 | 404 | 标准错误响应 |
| 导出时无 ChromaDB 向量 | 200（正常） | 仅打包 `data.json`，缺少的向量目录忽略 |
| 导入 ZIP 结构不合法 | 400 | 回滚事务 + 提示"文件格式不兼容" |
| 导入 version 不兼容 | 400 | 回滚事务 + 提示版本号 |
| 导入时数据库写入失败 | 500 | 回滚事务 + 清理临时文件 |
| 导入时 ChromaDB 写入失败 | 500 | 已写入的 SQLite 数据回滚 + 清理 |

## 全局表处理

以下表不按 `novel_id` 导出，而是全量忽略（属于平台级配置）：

- `users` — 用户账户
- `llm_configs` — LLM 配置
- `prompt_templates` — 提示词模板
- `migrations_applied` — 迁移记录
- `sqlite_sequence` — SQLite 内部表

## 修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `application/core/services/novel_backup_service.py` | **新建** | 核心导出/导入服务 |
| `infrastructure/persistence/backup/data_exporter.py` | **新建** | 表数据动态发现 + JSON 导出 |
| `infrastructure/persistence/backup/data_importer.py` | **新建** | JSON 解析 + 事务性导入 |
| `infrastructure/persistence/backup/chromadb_exporter.py` | **新建** | ChromaDB 向量导出/导入 |
| `interfaces/api/v1/core/backup_routes.py` | **新建** | API 路由 |
| `frontend/src/api/backup.ts` | **新建** | 前端 API 封装 |
| `frontend/src/views/Workbench.vue` | **修改** | 操作栏增加导出/导入按钮 |

## 兼容性

- 导出文件 `version: "1.0"` 随 schema 变更递增，导入时检查版本兼容
- `source_db_type` 字段记录源数据库类型，未来 MySQL/PG 兼容导入需加适配层
- 全局表跳过列表可配置，未来换数据库后调整

## 风险

| 风险 | 缓解 |
|------|------|
| JSON 中章节正文过大（50 万+ 字） | 流式写入，不一次性读到内存 |
| 60 张表手动维护易遗漏 | 动态发现 `novel_id` 列 + 间接关联表白名单 |
| 导入期间数据库锁冲突 | 导入为一次性管理操作，建议先停止自动驾驶 |
