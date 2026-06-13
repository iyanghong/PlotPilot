# 在线小说阅读器模块 — 设计文档

**日期**：2026-06-13
**作者**：Axelton
**状态**：已确认

---

## 一、概述

在 PlotPilot 工作台导出按钮旁边增加"在线阅读"入口，新增一个独立的在线小说阅读器模块，提供类似番茄小说/起点小说的沉浸式阅读体验。

核心原则：**独立模块，零侵入现有代码**（仅 StatsTopBar 增加按钮入口，router 增加路由注册）。

---

## 二、路由设计

```
/book/:slug/reader              → 阅读器入口（自动恢复到上次阅读位置）
/book/:slug/reader/:chapterNum  → 阅读指定章节
```

---

## 三、组件树

```
ReaderView.vue                      ← 顶级视图
├── ReaderTopBar.vue                ← 顶栏：返回 | 章节标题 | 🔖 书签
├── ReaderContent.vue               ← 正文渲染区，支持滚动/分页模式
├── ReaderBottomBar.vue             ← 底栏：◀ 上一章 | 进度 | 下一章 ▶ | Aa 设置
├── ReaderDrawerTOC.vue (NDrawer)   ← 左侧目录抽屉（含已读标记、书签 Tab）
├── ReaderDrawerSettings.vue (NDrawer) ← 右侧设置抽屉
└── ReaderBookmarks.vue             ← 书签列表（内嵌于目录抽屉 Tab）
```

---

## 四、核心交互

### 目录抽屉
- 左侧 NDrawer 滑出
- 章节列表，当前章节高亮
- 已读/未读标记（localStorage）
- 可切换 Tab 查看书签列表
- 点击任意章节跳转

### 设置抽屉
- 右侧 NDrawer 滑出
- 字号滑块：12px - 28px
- 行间距：1.5 / 1.8 / 2.0 / 2.5
- 段间距：0.5em / 1em / 1.5em
- 页边距：窄 / 标准 / 宽
- 主题：日间 / 夜间 / 羊皮纸 / 护眼绿
- 字体：系统默认 / 宋体 / 楷体 / 黑体
- 模式：滚动（默认）/ CSS 分页（CSS `column-width` 横向翻页，纯前端实现，无需服务端分页）

### 翻页交互
- 键盘 ← → 翻章
- 底栏 ◀ ▶ 按钮翻章
- 章节内滚动到底自动标记"已读"
- 离开页面时保存阅读位置（章节号 + scrollTop）

### 书签
- 顶栏 🔖 按钮：添加/取消当前章书签
- 目录抽屉可切换 Tab 查看书签列表
- 书签数据：章节号 + 标题 + 时间戳

---

## 五、数据存储策略

| 数据 | 存储方式 | Key 格式 |
|------|----------|----------|
| 章节内容 | 后端 API 按需拉取 | — |
| 章节目录 | 后端 API 拉取 | — |
| 阅读进度 | localStorage | `plotpilot-progress-{novelId}` |
| 阅读设置 | localStorage | `plotpilot-settings-{novelId}` |
| 书签 | localStorage | `plotpilot-bookmarks-{novelId}` |

全部阅读状态存 localStorage，后端零改动。后续可扩展为后端存储以支持跨设备同步。

---

## 六、后端 API

| 接口 | 用途 | 现状 |
|------|------|------|
| `GET /api/v1/novels/{id}` | 小说元数据 | ✅ 已有 |
| `GET /api/v1/novels/{id}/chapters` | 章节目录 | ✅ 已有 |
| `GET /api/v1/novels/{id}/chapters/{num}` | 章节正文 | ✅ 已有 |

后端零改动。

---

## 七、Composables 设计

### `useReader(novelId)`
```typescript
// 状态
chapters: Ref<ChapterMeta[]>
currentChapter: Ref<ChapterContent>
currentIndex: Ref<number>
loading: Ref<boolean>

// 方法
loadTOC()
loadChapter(num)
goNext()
goPrev()
goToChapter(num)
// 生命周期：恢复位置 → 加载章节 → 保存进度
```

### `useReaderSettings()`
```typescript
interface ReaderSettings {
  fontSize: number          // 默认 16
  lineHeight: number        // 默认 2.0
  paragraphSpacing: number  // 默认 1em
  marginWidth: number       // 默认 48
  theme: 'day' | 'night' | 'parchment' | 'green'
  fontFamily: 'system' | 'serif' | 'kai' | 'hei'
  pageMode: 'scroll' | 'paged'
}
// CSS 变量注入 ReaderContent，持久化到 localStorage
```

### `useBookmarks(novelId)`
```typescript
const bookmarks: Ref<Bookmark[]>
addBookmark(chapterNum, title)
removeBookmark(chapterNum)
hasBookmark(chapterNum): boolean
```

---

## 八、主题设计

| 主题 | 背景 | 文字 | 说明 |
|------|------|------|------|
| 日间 | `#fafafa` / `#1a1a1a` | 白底黑字 |
| 夜间 | `#1a1a1a` / `#c8c8c8` | 暗黑模式 |
| 羊皮纸 | `#f5f0e8` / `#3d2e22` | 仿古书 |
| 护眼绿 | `#e8f0e3` / `#2d3a25` | 护眼 |

字体 fallback：`KaiTi, STKaiti, 'Noto Serif CJK SC', 'Source Han Serif SC', serif`

---

## 九、错误处理

| 场景 | 处理 |
|------|------|
| 章节目录为空 | 空状态插画 + "暂无章节" |
| 章节加载失败 | NAlert + "重新加载"按钮 |
| 章节内容为空 | "本章内容为空" |
| 网络断开 | 不阻塞已加载内容，翻页时提示 |
| 第一章"上一章" | 按钮 disabled |
| 最后一章"下一章" | 按钮 disabled |
| localStorage 满 | 静默降级，仅内存生效 |
| 阅读进度不存在 | 默认第 1 章 |

---

## 十、现有代码改动（仅 2 处）

1. **`frontend/src/router/index.ts`**：+2 行（import + route 追加）
2. **`frontend/src/components/stats/StatsTopBar.vue`**：+13 行（预览按钮入口）

---

## 十一、新增文件清单

```
frontend/src/reader/                          ← 全新模块（约 12 个文件）
├── index.ts                                  ← 路由导出
├── ReaderView.vue                            ← ~200 行
├── components/
│   ├── ReaderTopBar.vue                      ← ~60 行
│   ├── ReaderContent.vue                     ← ~100 行
│   ├── ReaderBottomBar.vue                   ← ~80 行
│   ├── ReaderDrawerTOC.vue                   ← ~120 行
│   ├── ReaderDrawerSettings.vue              ← ~150 行
│   └── ReaderBookmarks.vue                   ← ~80 行
├── composables/
│   ├── useReader.ts                          ← ~120 行
│   ├── useReaderSettings.ts                  ← ~80 行
│   └── useBookmarks.ts                       ← ~60 行
└── types/
    └── index.ts                              ← ~40 行
```

总计：约 12 个新文件，约 1100 行代码，现有代码改动约 15 行。

---

## 十二、测试策略

| 层级 | 测试内容 | 方式 |
|------|----------|------|
| composables | useReader 加载/翻页/进度恢复 | Vitest + mock API |
| composables | useReaderSettings 读写/CSS 变量 | Vitest |
| composables | useBookmarks 增删查 | Vitest |
| 组件 | ReaderContent 主题渲染/字号/间距 | Vue Test Utils |
| 组件 | ReaderBottomBar 边界 disabled 态 | Vue Test Utils |
| 可访问性 | 键盘 ← → 翻章 | 手动 |
