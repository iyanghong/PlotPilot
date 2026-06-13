# 在线小说阅读器模块 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增独立的在线小说阅读器模块（类似番茄小说/起点阅读体验），入口位于 StatsTopBar 导出按钮旁。

**Architecture:** 全新 `frontend/src/reader/` 独立模块，包含 Vue 视图、组件、composables、类型定义。后端零改动。仅 router 和 StatsTopBar 各增加少量代码接入。

**Tech Stack:** Vue 3 + TypeScript + Naive UI (NDrawer, NDropdown, NButton) + Pinia (optional) + localStorage

---

### Task 1: 创建阅读器类型定义

**Files:**
- Create: `frontend/src/reader/types/index.ts`

- [ ] **Step 1: 编写类型文件**

```typescript
// frontend/src/reader/types/index.ts

/** 章节目录项（轻量，来自 GET /novels/{id}/chapters 列表） */
export interface ChapterMeta {
  id: string
  number: number
  title: string
  word_count: number
}

/** 章节正文（来自 GET /novels/{id}/chapters/{num}） */
export interface ChapterContent {
  id: string
  number: number
  title: string
  content: string
  word_count: number
}

/** 阅读进度（存 localStorage） */
export interface ReadingProgress {
  novelId: string
  chapterNumber: number
  scrollTop: number
  updatedAt: number // Date.now()
}

/** 阅读设置（存 localStorage） */
export interface ReaderSettings {
  fontSize: number // 默认 16
  lineHeight: number // 默认 2.0
  paragraphSpacing: string // 默认 '1em'
  marginWidth: number // 默认 48
  theme: 'day' | 'night' | 'parchment' | 'green'
  fontFamily: 'system' | 'serif' | 'kai' | 'hei'
  pageMode: 'scroll' | 'paged'
}

/** 书签 */
export interface Bookmark {
  chapterNumber: number
  chapterTitle: string
  createdAt: number // Date.now()
}

/** 默认阅读设置 */
export function defaultReaderSettings(): ReaderSettings {
  return {
    fontSize: 16,
    lineHeight: 2.0,
    paragraphSpacing: '1em',
    marginWidth: 48,
    theme: 'day',
    fontFamily: 'system',
    pageMode: 'scroll',
  }
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/reader/types/index.ts
git commit -m "feat(reader): add reader type definitions"
```

---

### Task 2: 创建阅读器 API 调用

**Files:**
- Create: `frontend/src/api/reader.ts`

- [ ] **Step 1: 编写 API 调用文件**

```typescript
// frontend/src/api/reader.ts
import { apiClient } from './config'
import { apiRoutes } from './endpoints'
import type { ChapterMeta, ChapterContent } from '@/reader/types'

/**
 * GET /api/v1/novels/{novelId}/chapters
 * 返回章节目录（不含正文）
 */
export function listChapters(novelId: string): Promise<ChapterMeta[]> {
  return apiClient.get<ChapterMeta[]>(apiRoutes.novels.chaptersClient(novelId)) as Promise<ChapterMeta[]>
}

/**
 * GET /api/v1/novels/{novelId}/chapters/{chapterNumber}
 * 返回指定章节正文
 */
export function getChapter(novelId: string, chapterNumber: number): Promise<ChapterContent> {
  return apiClient.get<ChapterContent>(
    apiRoutes.novels.chaptersClient(novelId) + '/' + encodeURIComponent(chapterNumber)
  ) as Promise<ChapterContent>
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/api/reader.ts
git commit -m "feat(reader): add reader API client"
```

---

### Task 3: 创建 useReaderSettings composable

**Files:**
- Create: `frontend/src/reader/composables/useReaderSettings.ts`

- [ ] **Step 1: 编写 composable**

```typescript
// frontend/src/reader/composables/useReaderSettings.ts
import { reactive, watch } from 'vue'
import { type ReaderSettings, defaultReaderSettings } from '../types'

const STORAGE_KEY_PREFIX = 'plotpilot-reader-settings'

function load(novelId: string): ReaderSettings {
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}-${novelId}`)
    if (raw) {
      const parsed = JSON.parse(raw)
      return { ...defaultReaderSettings(), ...parsed }
    }
  } catch {
    // localStorage 不可用或数据损坏
  }
  return defaultReaderSettings()
}

function save(novelId: string, settings: ReaderSettings): void {
  try {
    localStorage.setItem(`${STORAGE_KEY_PREFIX}-${novelId}`, JSON.stringify(settings))
  } catch {
    // localStorage 满或不可用，静默降级
  }
}

/** 将 ReaderSettings 转为 CSS 变量对象 */
export function settingsToCSSVars(settings: ReaderSettings): Record<string, string> {
  const fontFamilyMap: Record<string, string> = {
    system: 'system-ui, -apple-system, sans-serif',
    serif: 'KaiTi, STKaiti, "Noto Serif CJK SC", "Source Han Serif SC", serif',
    kai: 'KaiTi, STKaiti, serif',
    hei: '"Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif',
  }
  const themeMap: Record<string, { bg: string; text: string }> = {
    day: { bg: '#fafafa', text: '#1a1a1a' },
    night: { bg: '#1a1a1a', text: '#c8c8c8' },
    parchment: { bg: '#f5f0e8', text: '#3d2e22' },
    green: { bg: '#e8f0e3', text: '#2d3a25' },
  }
  const theme = themeMap[settings.theme] || themeMap.day
  return {
    '--reader-font-size': `${settings.fontSize}px`,
    '--reader-line-height': String(settings.lineHeight),
    '--reader-paragraph-spacing': settings.paragraphSpacing,
    '--reader-margin-width': `${settings.marginWidth}px`,
    '--reader-bg': theme.bg,
    '--reader-text': theme.text,
    '--reader-font-family': fontFamilyMap[settings.fontFamily] || fontFamilyMap.system,
  }
}

export function useReaderSettings(novelId: string) {
  const settings = reactive<ReaderSettings>(load(novelId))

  const cssVars = () => settingsToCSSVars(settings)

  watch(
    () => settings,
    (val) => {
      save(novelId, { ...val })
    },
    { deep: true }
  )

  function resetSettings() {
    Object.assign(settings, defaultReaderSettings())
  }

  return { settings, cssVars, resetSettings }
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/reader/composables/useReaderSettings.ts
git commit -m "feat(reader): add useReaderSettings composable"
```

---

### Task 4: 创建 useBookmarks composable

**Files:**
- Create: `frontend/src/reader/composables/useBookmarks.ts`

- [ ] **Step 1: 编写 composable**

```typescript
// frontend/src/reader/composables/useBookmarks.ts
import { ref } from 'vue'
import type { Bookmark } from '../types'

const STORAGE_KEY_PREFIX = 'plotpilot-reader-bookmarks'

function load(novelId: string): Bookmark[] {
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}-${novelId}`)
    if (raw) {
      return JSON.parse(raw) as Bookmark[]
    }
  } catch {
    // ignore
  }
  return []
}

function save(novelId: string, bookmarks: Bookmark[]): void {
  try {
    localStorage.setItem(`${STORAGE_KEY_PREFIX}-${novelId}`, JSON.stringify(bookmarks))
  } catch {
    // 静默降级
  }
}

export function useBookmarks(novelId: string) {
  const bookmarks = ref<Bookmark[]>(load(novelId))

  function addBookmark(chapterNumber: number, chapterTitle: string): boolean {
    if (hasBookmark(chapterNumber)) return false
    const bm: Bookmark = {
      chapterNumber,
      chapterTitle,
      createdAt: Date.now(),
    }
    bookmarks.value.push(bm)
    save(novelId, bookmarks.value)
    return true
  }

  function removeBookmark(chapterNumber: number): boolean {
    const idx = bookmarks.value.findIndex((b) => b.chapterNumber === chapterNumber)
    if (idx === -1) return false
    bookmarks.value.splice(idx, 1)
    save(novelId, bookmarks.value)
    return true
  }

  function hasBookmark(chapterNumber: number): boolean {
    return bookmarks.value.some((b) => b.chapterNumber === chapterNumber)
  }

  function toggleBookmark(chapterNumber: number, chapterTitle: string): boolean {
    if (hasBookmark(chapterNumber)) {
      removeBookmark(chapterNumber)
      return false // now unbookmarked
    } else {
      addBookmark(chapterNumber, chapterTitle)
      return true // now bookmarked
    }
  }

  return { bookmarks, addBookmark, removeBookmark, hasBookmark, toggleBookmark }
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/reader/composables/useBookmarks.ts
git commit -m "feat(reader): add useBookmarks composable"
```

---

### Task 5: 创建 useReader composable（核心）

**Files:**
- Create: `frontend/src/reader/composables/useReader.ts`

- [ ] **Step 1: 编写 composable**

```typescript
// frontend/src/reader/composables/useReader.ts
import { ref, computed } from 'vue'
import { listChapters, getChapter } from '@/api/reader'
import type { ChapterMeta, ChapterContent, ReadingProgress } from '../types'

const STORAGE_KEY_PREFIX = 'plotpilot-reader-progress'

function loadProgress(novelId: string): ReadingProgress | null {
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}-${novelId}`)
    if (raw) {
      return JSON.parse(raw) as ReadingProgress
    }
  } catch {
    // ignore
  }
  return null
}

function saveProgress(progress: ReadingProgress): void {
  try {
    localStorage.setItem(
      `${STORAGE_KEY_PREFIX}-${progress.novelId}`,
      JSON.stringify(progress)
    )
  } catch {
    // 静默降级
  }
}

export function useReader(novelId: string) {
  const toc = ref<ChapterMeta[]>([])
  const currentChapter = ref<ChapterContent | null>(null)
  const currentIndex = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const totalChapters = computed(() => toc.value.length)
  const isFirstChapter = computed(() => currentIndex.value <= 0)
  const isLastChapter = computed(() => currentIndex.value >= totalChapters.value - 1)

  /** 加载章节目录 */
  async function loadTOC(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      toc.value = await listChapters(novelId)
    } catch (e) {
      error.value = '加载章节目录失败'
      console.error('loadTOC error:', e)
    } finally {
      loading.value = false
    }
  }

  /** 加载指定章节 */
  async function loadChapter(chapterNumber: number): Promise<void> {
    loading.value = true
    error.value = null
    try {
      currentChapter.value = await getChapter(novelId, chapterNumber)
      const idx = toc.value.findIndex((c) => c.number === chapterNumber)
      if (idx !== -1) {
        currentIndex.value = idx
      }
      // 保存进度
      saveProgress({
        novelId,
        chapterNumber,
        scrollTop: 0,
        updatedAt: Date.now(),
      })
    } catch (e) {
      error.value = '加载章节内容失败'
      console.error('loadChapter error:', e)
    } finally {
      loading.value = false
    }
  }

  /** 跳转到指定章节（通过序号） */
  async function goToChapter(chapterNumber: number): Promise<void> {
    if (chapterNumber < 1 || chapterNumber > totalChapters.value) return
    await loadChapter(chapterNumber)
    window.scrollTo(0, 0)
  }

  /** 上一章 */
  async function goPrev(): Promise<void> {
    if (isFirstChapter.value) return
    const prev = toc.value[currentIndex.value - 1]
    if (prev) {
      await loadChapter(prev.number)
      window.scrollTo(0, 0)
    }
  }

  /** 下一章 */
  async function goNext(): Promise<void> {
    if (isLastChapter.value) return
    const next = toc.value[currentIndex.value + 1]
    if (next) {
      await loadChapter(next.number)
      window.scrollTo(0, 0)
    }
  }

  /** 初始化：加载目录 → 恢复上次位置或从第一章开始 */
  async function init(chapterNumber?: number): Promise<void> {
    await loadTOC()
    if (toc.value.length === 0) return

    if (chapterNumber) {
      await loadChapter(chapterNumber)
      return
    }

    const progress = loadProgress(novelId)
    if (progress && toc.value.some((c) => c.number === progress.chapterNumber)) {
      await loadChapter(progress.chapterNumber)
      // 恢复滚动位置在组件中处理
    } else {
      await loadChapter(toc.value[0].number)
    }
  }

  /** 更新滚动位置（由组件在 onUnmounted 时调用） */
  function updateScrollPosition(scrollTop: number): void {
    if (!currentChapter.value) return
    saveProgress({
      novelId,
      chapterNumber: currentChapter.value.number,
      scrollTop,
      updatedAt: Date.now(),
    })
  }

  /** 获取保存的滚动位置 */
  function getSavedScrollTop(): number {
    const progress = loadProgress(novelId)
    return progress?.scrollTop ?? 0
  }

  return {
    toc,
    currentChapter,
    currentIndex,
    totalChapters,
    isFirstChapter,
    isLastChapter,
    loading,
    error,
    init,
    loadTOC,
    loadChapter,
    goToChapter,
    goNext,
    goPrev,
    updateScrollPosition,
    getSavedScrollTop,
  }
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/reader/composables/useReader.ts
git commit -m "feat(reader): add useReader composable"
```

---

### Task 6: 创建 ReaderContent 组件

**Files:**
- Create: `frontend/src/reader/components/ReaderContent.vue`

- [ ] **Step 1: 编写组件**

```vue
<!-- frontend/src/reader/components/ReaderContent.vue -->
<template>
  <div class="reader-content" :style="styleVars">
    <h1 v-if="chapter" class="reader-chapter-title">{{ displayTitle }}</h1>
    <div v-if="error" class="reader-error">
      <p>{{ error }}</p>
      <n-button size="small" @click="$emit('retry')">重新加载</n-button>
    </div>
    <n-spin v-else-if="loading" class="reader-loading" />
    <div v-else-if="!chapter || !chapter.content?.trim()" class="reader-empty">
      本章内容为空
    </div>
    <div
      v-else
      class="reader-body"
      :class="{ 'reader-paged': pageMode === 'paged' }"
    >
      <p v-for="(para, i) in paragraphs" :key="i" class="reader-paragraph">
        {{ para }}
      </p>
    </div>
    <div v-if="chapter && !loading" class="reader-chapter-end">
      ━━ 第 {{ chapter.number }} / {{ totalChapters }} 章 ━━
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NSpin, NButton } from 'naive-ui'
import type { ChapterContent } from '../../types'
import { settingsToCSSVars } from '../../composables/useReaderSettings'
import type { ReaderSettings } from '../../types'

const props = defineProps<{
  chapter: ChapterContent | null
  totalChapters: number
  settings: ReaderSettings
  loading: boolean
  error: string | null
}>()

defineEmits<{
  retry: []
}>()

const displayTitle = computed(() => {
  if (!props.chapter) return ''
  if (props.chapter.title?.trim()) return props.chapter.title.trim()
  return `第 ${props.chapter.number} 章`
})

const paragraphs = computed(() => {
  const content = props.chapter?.content || ''
  return content
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
})

const styleVars = computed(() => {
  return settingsToCSSVars(props.settings)
})

const pageMode = computed(() => props.settings.pageMode)
</script>

<style scoped>
.reader-content {
  background: var(--reader-bg, #fafafa);
  color: var(--reader-text, #1a1a1a);
  font-family: var(--reader-font-family, system-ui);
  font-size: var(--reader-font-size, 16px);
  line-height: var(--reader-line-height, 2);
  min-height: 60vh;
  padding: 24px var(--reader-margin-width, 48px) 48px;
  max-width: 860px;
  margin: 0 auto;
  transition: background 0.3s, color 0.3s;
}

.reader-chapter-title {
  text-align: center;
  font-size: calc(var(--reader-font-size, 16px) + 6px);
  font-weight: 700;
  margin-bottom: 32px;
  letter-spacing: 0.05em;
}

.reader-body {
  text-align: justify;
}

/* 分页模式：CSS columns 横向翻页（简单实现） */
.reader-paged {
  column-width: 360px;
  column-gap: 48px;
  height: calc(100vh - 160px);
  overflow-x: auto;
  overflow-y: hidden;
}

.reader-paragraph {
  text-indent: 2em;
  margin-bottom: var(--reader-paragraph-spacing, 1em);
}

.reader-chapter-end {
  text-align: center;
  color: #999;
  font-size: 12px;
  margin-top: 40px;
  user-select: none;
}

.reader-error,
.reader-empty {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

.reader-loading {
  display: flex;
  justify-content: center;
  padding: 80px 0;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/reader/components/ReaderContent.vue
git commit -m "feat(reader): add ReaderContent component"
```

---

### Task 7: 创建 ReaderBottomBar 组件

**Files:**
- Create: `frontend/src/reader/components/ReaderBottomBar.vue`

- [ ] **Step 1: 编写组件**

```vue
<!-- frontend/src/reader/components/ReaderBottomBar.vue -->
<template>
  <div class="reader-bottom-bar">
    <button class="bottom-btn" :disabled="isFirstChapter" @click="$emit('prev')">
      ◀ 上一章
    </button>
    <span class="bottom-progress">
      第 {{ currentNumber }} / {{ totalChapters }} 章
    </span>
    <button class="bottom-btn" :disabled="isLastChapter" @click="$emit('next')">
      下一章 ▶
    </button>
    <button class="bottom-btn bottom-btn-settings" @click="$emit('open-settings')">
      Aa
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  currentNumber: number
  totalChapters: number
  isFirstChapter: boolean
  isLastChapter: boolean
}>()

defineEmits<{
  prev: []
  next: []
  'open-settings': []
}>()
</script>

<style scoped>
.reader-bottom-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 10px 20px;
  background: #f0ece6;
  border-top: 1px solid #e0d8cc;
  color: #5c4a3a;
}

.bottom-btn {
  background: transparent;
  border: 1px solid #c4b9a8;
  border-radius: 6px;
  padding: 6px 14px;
  font-size: 13px;
  cursor: pointer;
  color: inherit;
  transition: all 0.15s;
}

.bottom-btn:hover:not(:disabled) {
  background: #e8e0d4;
  border-color: #8b7355;
}

.bottom-btn:disabled {
  opacity: 0.35;
  cursor: default;
}

.bottom-progress {
  font-size: 13px;
  font-weight: 600;
  opacity: 0.8;
}

.bottom-btn-settings {
  font-weight: 700;
  font-size: 14px;
  letter-spacing: -0.02em;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/reader/components/ReaderBottomBar.vue
git commit -m "feat(reader): add ReaderBottomBar component"
```

---

### Task 8: 创建 ReaderTopBar 组件

**Files:**
- Create: `frontend/src/reader/components/ReaderTopBar.vue`

- [ ] **Step 1: 编写组件**

```vue
<!-- frontend/src/reader/components/ReaderTopBar.vue -->
<template>
  <div class="reader-top-bar">
    <button class="top-btn" @click="$emit('back')">
      ← 返回工作台
    </button>
    <span class="top-title">{{ title }}</span>
    <div class="top-right">
      <button class="top-btn" @click="$emit('toggle-toc')">
        ☰ 目录
      </button>
      <button
        class="top-btn"
        :class="{ bookmarked: isBookmarked }"
        @click="$emit('toggle-bookmark')"
      >
        {{ isBookmarked ? '🔖' : '🏷' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  isBookmarked: boolean
}>()

defineEmits<{
  back: []
  'toggle-toc': []
  'toggle-bookmark': []
}>()
</script>

<style scoped>
.reader-top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 20px;
  background: #f0ece6;
  border-bottom: 1px solid #e0d8cc;
  color: #5c4a3a;
}

.top-title {
  font-size: 15px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 50%;
}

.top-btn {
  background: transparent;
  border: none;
  padding: 4px 10px;
  font-size: 13px;
  cursor: pointer;
  color: inherit;
  border-radius: 4px;
  transition: background 0.15s;
}

.top-btn:hover {
  background: #e8e0d4;
}

.top-right {
  display: flex;
  gap: 4px;
}

.bookmarked {
  color: #d4a017;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/reader/components/ReaderTopBar.vue
git commit -m "feat(reader): add ReaderTopBar component"
```

---

### Task 9: 创建 ReaderBookmarks 组件

**Files:**
- Create: `frontend/src/reader/components/ReaderBookmarks.vue`

- [ ] **Step 1: 编写组件**

```vue
<!-- frontend/src/reader/components/ReaderBookmarks.vue -->
<template>
  <div class="reader-bookmarks">
    <div v-if="bookmarks.length === 0" class="bookmarks-empty">
      暂无书签
    </div>
    <div
      v-for="bm in sortedBookmarks"
      :key="bm.chapterNumber"
      class="bookmark-item"
      @click="$emit('go-to-chapter', bm.chapterNumber)"
    >
      <span class="bookmark-chapter">第 {{ bm.chapterNumber }} 章</span>
      <span class="bookmark-title">{{ bm.chapterTitle }}</span>
      <span class="bookmark-time">{{ formatTime(bm.createdAt) }}</span>
      <button
        class="bookmark-remove"
        @click.stop="$emit('remove-bookmark', bm.chapterNumber)"
      >
        ✕
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Bookmark } from '../../types'

const props = defineProps<{
  bookmarks: Bookmark[]
}>()

defineEmits<{
  'go-to-chapter': [chapterNumber: number]
  'remove-bookmark': [chapterNumber: number]
}>()

const sortedBookmarks = computed(() =>
  [...props.bookmarks].sort((a, b) => b.createdAt - a.createdAt)
)

function formatTime(ts: number): string {
  const d = new Date(ts)
  const now = new Date()
  const diffDays = Math.floor((now.getTime() - d.getTime()) / 86400000)
  if (diffDays === 0) return '今天'
  if (diffDays === 1) return '昨天'
  if (diffDays < 7) return `${diffDays}天前`
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}
</script>

<style scoped>
.reader-bookmarks {
  padding: 8px 0;
}

.bookmarks-empty {
  text-align: center;
  color: #999;
  padding: 24px;
  font-size: 14px;
}

.bookmark-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.15s;
}

.bookmark-item:hover {
  background: rgba(0, 0, 0, 0.04);
}

.bookmark-chapter {
  font-weight: 600;
  font-size: 13px;
  flex-shrink: 0;
}

.bookmark-title {
  flex: 1;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bookmark-time {
  font-size: 11px;
  color: #999;
  flex-shrink: 0;
}

.bookmark-remove {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 12px;
  color: #ccc;
  padding: 2px;
}

.bookmark-remove:hover {
  color: #e74c3c;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/reader/components/ReaderBookmarks.vue
git commit -m "feat(reader): add ReaderBookmarks component"
```

---

### Task 10: 创建 ReaderDrawerTOC 组件（章节目录 + 书签 Tab）

**Files:**
- Create: `frontend/src/reader/components/ReaderDrawerTOC.vue`

- [ ] **Step 1: 编写组件**

```vue
<!-- frontend/src/reader/components/ReaderDrawerTOC.vue -->
<template>
  <n-drawer
    :show="show"
    placement="left"
    :width="320"
    @update:show="$emit('update:show', $event)"
  >
    <n-drawer-content title="目录" closable>
      <n-tabs v-model:value="activeTab" type="line" size="small">
        <n-tab-pane name="toc" tab="章节">
          <div class="toc-list">
            <div v-if="chapters.length === 0" class="toc-empty">
              暂无章节
            </div>
            <div
              v-for="(ch, i) in chapters"
              :key="ch.number"
              class="toc-item"
              :class="{
                'toc-current': ch.number === currentChapterNumber,
                'toc-read': readSet.has(ch.number) && ch.number !== currentChapterNumber,
              }"
              @click="selectChapter(ch.number)"
            >
              <span class="toc-number">第 {{ ch.number }} 章</span>
              <span class="toc-title">{{ ch.title || `第 ${ch.number} 章` }}</span>
              <span v-if="readSet.has(ch.number)" class="toc-check">✓</span>
            </div>
          </div>
        </n-tab-pane>
        <n-tab-pane name="bookmarks" tab="书签">
          <ReaderBookmarks
            :bookmarks="bookmarks"
            @go-to-chapter="selectChapter"
            @remove-bookmark="$emit('remove-bookmark', $event)"
          />
        </n-tab-pane>
      </n-tabs>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NDrawer, NDrawerContent, NTabs, NTabPane } from 'naive-ui'
import type { ChapterMeta, Bookmark } from '../../types'
import ReaderBookmarks from './ReaderBookmarks.vue'

defineProps<{
  show: boolean
  chapters: ChapterMeta[]
  currentChapterNumber: number
  readSet: Set<number>
  bookmarks: Bookmark[]
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
  'go-to-chapter': [chapterNumber: number]
  'remove-bookmark': [chapterNumber: number]
}>()

const activeTab = ref('toc')

function selectChapter(chapterNumber: number) {
  emit('go-to-chapter', chapterNumber)
  emit('update:show', false)
}
</script>

<style scoped>
.toc-list {
  padding: 4px 0;
}

.toc-empty {
  text-align: center;
  color: #999;
  padding: 24px;
  font-size: 14px;
}

.toc-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.15s;
}

.toc-item:hover {
  background: rgba(0, 0, 0, 0.04);
}

.toc-current {
  background: rgba(79, 70, 229, 0.08);
  font-weight: 600;
}

.toc-read {
  opacity: 0.55;
}

.toc-number {
  font-size: 12px;
  flex-shrink: 0;
  color: #888;
}

.toc-title {
  flex: 1;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.toc-check {
  font-size: 12px;
  color: #4caf50;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/reader/components/ReaderDrawerTOC.vue
git commit -m "feat(reader): add ReaderDrawerTOC component"
```

---

### Task 11: 创建 ReaderDrawerSettings 组件

**Files:**
- Create: `frontend/src/reader/components/ReaderDrawerSettings.vue`

- [ ] **Step 1: 编写组件**

```vue
<!-- frontend/src/reader/components/ReaderDrawerSettings.vue -->
<template>
  <n-drawer
    :show="show"
    placement="right"
    :width="300"
    @update:show="$emit('update:show', $event)"
  >
    <n-drawer-content title="阅读设置" closable>
      <div class="settings-section">
        <label class="settings-label">字号：{{ settings.fontSize }}px</label>
        <input
          type="range"
          class="settings-slider"
          :min="12"
          :max="28"
          :value="settings.fontSize"
          @input="update('fontSize', Number(($event.target as HTMLInputElement).value))"
        />
      </div>

      <div class="settings-section">
        <label class="settings-label">行间距</label>
        <div class="settings-options">
          <button
            v-for="v in [1.5, 1.8, 2.0, 2.5]"
            :key="v"
            class="settings-option"
            :class="{ active: settings.lineHeight === v }"
            @click="update('lineHeight', v)"
          >
            {{ v }}
          </button>
        </div>
      </div>

      <div class="settings-section">
        <label class="settings-label">段间距</label>
        <div class="settings-options">
          <button
            v-for="v in ['0.5em', '1em', '1.5em']"
            :key="v"
            class="settings-option"
            :class="{ active: settings.paragraphSpacing === v }"
            @click="update('paragraphSpacing', v)"
          >
            {{ v }}
          </button>
        </div>
      </div>

      <div class="settings-section">
        <label class="settings-label">页边距</label>
        <div class="settings-options">
          <button
            v-for="opt in marginOptions"
            :key="opt.value"
            class="settings-option"
            :class="{ active: settings.marginWidth === opt.value }"
            @click="update('marginWidth', opt.value)"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>

      <div class="settings-section">
        <label class="settings-label">主题</label>
        <div class="settings-themes">
          <button
            v-for="t in themeOptions"
            :key="t.value"
            class="theme-swatch"
            :class="{ active: settings.theme === t.value }"
            :style="{ background: t.bg, color: t.text }"
            :title="t.label"
            @click="update('theme', t.value)"
          >
            {{ t.label }}
          </button>
        </div>
      </div>

      <div class="settings-section">
        <label class="settings-label">字体</label>
        <div class="settings-options">
          <button
            v-for="f in fontOptions"
            :key="f.value"
            class="settings-option"
            :class="{ active: settings.fontFamily === f.value }"
            @click="update('fontFamily', f.value)"
          >
            {{ f.label }}
          </button>
        </div>
      </div>

      <div class="settings-section">
        <label class="settings-label">翻页模式</label>
        <div class="settings-options">
          <button
            class="settings-option"
            :class="{ active: settings.pageMode === 'scroll' }"
            @click="update('pageMode', 'scroll' as const)"
          >
            滚动
          </button>
          <button
            class="settings-option"
            :class="{ active: settings.pageMode === 'paged' }"
            @click="update('pageMode', 'paged' as const)"
          >
            分页
          </button>
        </div>
      </div>

      <div class="settings-section">
        <n-button size="small" quaternary @click="$emit('reset')">
          恢复默认设置
        </n-button>
      </div>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup lang="ts">
import { NDrawer, NDrawerContent, NButton } from 'naive-ui'
import type { ReaderSettings } from '../../types'

const props = defineProps<{
  show: boolean
  settings: ReaderSettings
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
  'update:settings': [settings: ReaderSettings]
  reset: []
}>()

const marginOptions = [
  { label: '窄', value: 24 },
  { label: '标准', value: 48 },
  { label: '宽', value: 80 },
]

const themeOptions = [
  { label: '日间', value: 'day', bg: '#fafafa', text: '#1a1a1a' },
  { label: '夜间', value: 'night', bg: '#1a1a1a', text: '#c8c8c8' },
  { label: '羊皮纸', value: 'parchment', bg: '#f5f0e8', text: '#3d2e22' },
  { label: '护眼', value: 'green', bg: '#e8f0e3', text: '#2d3a25' },
]

const fontOptions = [
  { label: '系统', value: 'system' },
  { label: '宋体', value: 'serif' },
  { label: '楷体', value: 'kai' },
  { label: '黑体', value: 'hei' },
]

function update<K extends keyof ReaderSettings>(key: K, value: ReaderSettings[K]) {
  emit('update:settings', { ...props.settings, [key]: value })
}
</script>

<style scoped>
.settings-section {
  margin-bottom: 20px;
}

.settings-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #555;
}

.settings-slider {
  width: 100%;
}

.settings-options {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.settings-option {
  padding: 5px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}

.settings-option:hover {
  border-color: #999;
}

.settings-option.active {
  background: #4f46e5;
  color: #fff;
  border-color: #4f46e5;
}

.settings-themes {
  display: flex;
  gap: 8px;
}

.theme-swatch {
  width: 52px;
  height: 52px;
  border-radius: 8px;
  border: 2px solid transparent;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.theme-swatch:hover {
  transform: scale(1.05);
}

.theme-swatch.active {
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.3);
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/reader/components/ReaderDrawerSettings.vue
git commit -m "feat(reader): add ReaderDrawerSettings component"
```

---

### Task 12: 创建 ReaderView 主视图

**Files:**
- Create: `frontend/src/reader/ReaderView.vue`

- [ ] **Step 1: 编写主视图**

```vue
<!-- frontend/src/reader/ReaderView.vue -->
<template>
  <div class="reader-view" :style="cssVars()">
    <ReaderTopBar
      :title="currentChapter?.title || '加载中...'"
      :is-bookmarked="isBookmarked"
      @back="goBack"
      @toggle-toc="showTOC = true"
      @toggle-bookmark="handleToggleBookmark"
    />

    <ReaderContent
      :chapter="currentChapter"
      :total-chapters="totalChapters"
      :settings="settings"
      :loading="loading"
      :error="error"
      @retry="currentChapter && loadChapter(currentChapter.number)"
    />

    <ReaderBottomBar
      v-if="currentChapter"
      :current-number="currentChapter.number"
      :total-chapters="totalChapters"
      :is-first-chapter="isFirstChapter"
      :is-last-chapter="isLastChapter"
      @prev="goPrev"
      @next="goNext"
      @open-settings="showSettings = true"
    />

    <ReaderDrawerTOC
      :show="showTOC"
      :chapters="toc"
      :current-chapter-number="currentChapter?.number ?? 0"
      :read-set="readSet"
      :bookmarks="bookmarks"
      @update:show="showTOC = $event"
      @go-to-chapter="goToChapter"
      @remove-bookmark="(num) => removeBookmark(num)"
    />

    <ReaderDrawerSettings
      :show="showSettings"
      :settings="settings"
      @update:show="showSettings = $event"
      @update:settings="handleSettingsUpdate"
      @reset="resetSettings"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import ReaderTopBar from './components/ReaderTopBar.vue'
import ReaderContent from './components/ReaderContent.vue'
import ReaderBottomBar from './components/ReaderBottomBar.vue'
import ReaderDrawerTOC from './components/ReaderDrawerTOC.vue'
import ReaderDrawerSettings from './components/ReaderDrawerSettings.vue'
import { useReader } from './composables/useReader'
import { useReaderSettings } from './composables/useReaderSettings'
import { useBookmarks } from './composables/useBookmarks'
import type { ReaderSettings } from './types'

const router = useRouter()
const route = useRoute()

const slug = route.params.slug as string
const chapterNumParam = route.params.chapterNum

const {
  toc,
  currentChapter,
  currentIndex,
  totalChapters,
  isFirstChapter,
  isLastChapter,
  loading,
  error,
  init,
  loadChapter,
  goToChapter,
  goNext,
  goPrev,
  updateScrollPosition,
  getSavedScrollTop,
} = useReader(slug)

const { settings, cssVars, resetSettings } = useReaderSettings(slug)
const { bookmarks, hasBookmark, toggleBookmark, removeBookmark } = useBookmarks(slug)

const showTOC = ref(false)
const showSettings = ref(false)

// 已读章节集合（从 toc + 当前进度推断）
const readSet = computed(() => {
  const s = new Set<number>()
  for (const ch of toc.value) {
    if (ch.number < (currentChapter.value?.number ?? 0)) {
      s.add(ch.number)
    }
  }
  return s
})

const isBookmarked = computed(() =>
  currentChapter.value ? hasBookmark(currentChapter.value.number) : false
)

// 键盘导航
function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowLeft') {
    e.preventDefault()
    goPrev()
  } else if (e.key === 'ArrowRight') {
    e.preventDefault()
    goNext()
  }
}

function handleToggleBookmark() {
  if (!currentChapter.value) return
  toggleBookmark(
    currentChapter.value.number,
    currentChapter.value.title || `第 ${currentChapter.value.number} 章`
  )
}

function handleSettingsUpdate(newSettings: ReaderSettings) {
  Object.assign(settings, newSettings)
}

function goBack() {
  router.push(`/book/${slug}/workbench`)
}

onMounted(async () => {
  window.addEventListener('keydown', handleKeydown)
  const chapterNum = chapterNumParam ? Number(chapterNumParam) : undefined
  await init(chapterNum)
  // 恢复滚动位置
  const savedTop = getSavedScrollTop()
  if (savedTop > 0) {
    window.scrollTo(0, savedTop)
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  updateScrollPosition(window.scrollY)
})
</script>

<style scoped>
.reader-view {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--reader-bg, #fafafa);
  transition: background 0.3s;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/reader/ReaderView.vue
git commit -m "feat(reader): add ReaderView main view"
```

---

### Task 13: 创建模块入口并接入路由

**Files:**
- Create: `frontend/src/reader/index.ts`
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: 编写模块入口**

```typescript
// frontend/src/reader/index.ts
import type { RouteRecordRaw } from 'vue-router'

const ReaderView = () => import('./ReaderView.vue')

export const readerRoutes: RouteRecordRaw[] = [
  {
    path: '/book/:slug/reader',
    name: 'Reader',
    component: ReaderView,
  },
  {
    path: '/book/:slug/reader/:chapterNum',
    name: 'ReaderChapter',
    component: ReaderView,
  },
]
```

- [ ] **Step 2: 修改路由文件**

在 `frontend/src/router/index.ts` 顶部添加：

```typescript
import { readerRoutes } from '@/reader'
```

在 `routes` 数组末尾（`]` 前）添加：

```typescript
  ...readerRoutes,
```

最终 `routes` 如下：

```typescript
  routes: [
    { path: '/', name: 'Home', component: Home },
    { path: '/book/:slug/workbench', name: 'Workbench', component: Workbench },
    { path: '/book/:slug/cast', name: 'Cast', component: Cast },
    { path: '/book/:slug/chapter/:id', name: 'Chapter', component: Chapter },
    { path: '/book/:slug/characters', name: 'CharacterGraph', component: CharacterGraph },
    { path: '/book/:slug/location-graph', name: 'LocationGraph', component: LocationGraph },
    {
      path: '/debug/scheduler',
      name: 'CharacterSchedulerSimulator',
      component: CharacterSchedulerSimulator,
    },
    ...readerRoutes,
  ],
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/reader/index.ts frontend/src/router/index.ts
git commit -m "feat(reader): register reader routes"
```

---

### Task 14: 在 StatsTopBar 添加阅读按钮入口

**Files:**
- Modify: `frontend/src/components/stats/StatsTopBar.vue`

- [ ] **Step 1: 在 template 中的导出按钮旁边（`.top-bar-actions` 内，`.action-trigger` 之前）添加预览按钮**

```vue
<!-- 在线预览按钮 -->
<n-tooltip trigger="hover" :show-arrow="false">
  <template #trigger>
    <div class="action-trigger" role="button" aria-label="在线预览" @click="openReader">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20">
        <path fill="currentColor" d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/>
      </svg>
    </div>
  </template>
  <span>在线预览</span>
</n-tooltip>
```

这会放在导出按钮的 `<n-dropdown>` 闭合之后，设置按钮 `.settings-trigger` 之前。

- [ ] **Step 2: 在 `<script setup>` 中添加**

在 import 区域添加：

```typescript
import { useRouter } from 'vue-router'
```

在 `const message = useMessage()` 后添加：

```typescript
const router = useRouter()
```

添加方法（放在 `handleExport` 之后）：

```typescript
function openReader() {
  router.push(`/book/${props.slug}/reader`)
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/stats/StatsTopBar.vue
git commit -m "feat(reader): add reader entry button in StatsTopBar"
```

---

### Task 15: 端到端验证

- [ ] **Step 1: 启动前端开发服务器**

```bash
cd frontend && npm run dev
```

- [ ] **Step 2: 手动验证核心流程**

验证清单：
1. 打开工作台，在顶部栏右侧看到 👁 预览按钮
2. 点击预览 → 跳转到 `/book/:slug/reader`
3. 自动加载第一章正文
4. 顶部栏显示"返回工作台"和章节标题
5. 点击"◀ 上一章"按钮，第一章时处于 disabled
6. 点击"下一章 ▶"，加载下一章内容
7. 点击"☰ 目录"，左侧抽屉滑出，显示全部章节列表
8. 点击任意章节，抽屉关闭并跳转
9. 点击 🔖 书签，添加当前章书签
10. 在目录抽屉切换到"书签" Tab，看到已添加书签
11. 点击"Aa 设置"，右侧抽屉滑出
12. 切换主题 → 正文区域颜色变化
13. 调节字号 → 文字大小变化
14. 按键盘 ← → 翻章
15. 刷新页面 → 自动恢复到上次阅读章节
16. 关闭标签页重新打开 → 恢复上次章节

- [ ] **Step 3: 如有 bug，在对应文件修复后提交**

---

### Task 16: 最终检查与清理

- [ ] **Step 1: 检查 TypeScript 编译**

```bash
cd frontend && npx vue-tsc --noEmit
```

- [ ] **Step 2: 运行已有测试确保无回归**

```bash
cd frontend && npm run test -- --run
```

- [ ] **Step 3: 检查文件结构是否符合设计**

```bash
find frontend/src/reader -type f | sort
```

预期输出：
```
frontend/src/reader/index.ts
frontend/src/reader/ReaderView.vue
frontend/src/reader/components/ReaderBookmarks.vue
frontend/src/reader/components/ReaderBottomBar.vue
frontend/src/reader/components/ReaderContent.vue
frontend/src/reader/components/ReaderDrawerSettings.vue
frontend/src/reader/components/ReaderDrawerTOC.vue
frontend/src/reader/components/ReaderTopBar.vue
frontend/src/reader/composables/useBookmarks.ts
frontend/src/reader/composables/useReader.ts
frontend/src/reader/composables/useReaderSettings.ts
frontend/src/reader/types/index.ts
```

- [ ] **Step 4: 提交**

```bash
git add -A && git status
# 确认所有变更在预期范围内
git commit -m "chore(reader): finalize reader module implementation"
```
