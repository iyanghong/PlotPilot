<template>
  <div v-if="loading" class="stats-top-bar loading">
    <n-spin size="medium" />
  </div>
  <div v-else-if="error" class="stats-top-bar error">
    <span>{{ error }}</span>
    <n-button size="small" secondary style="margin-left: 12px" @click="retryLoad">重试</n-button>
  </div>
  <div v-else class="stats-top-bar">
    <!-- 左侧：AI 工具统一入口（隐藏原始按钮，通过 ref 触发） -->
    <div class="topbar-left">
      <!-- 隐藏的原始组件，仅用于保留其 drawer/modal 功能 -->
      <div class="ai-hidden-entries" aria-hidden="true">
        <GlobalLLMEntryButton ref="llmRef" appearance="topbar" />
        <PromptPlazaEntryButton ref="plazaRef" appearance="topbar" />
      </div>

      <!-- 可见的统一触发按钮 -->
      <n-dropdown
        trigger="click"
        placement="bottom-start"
        :options="aiToolsOptions"
        @select="handleAiToolSelect"
      >
        <div class="ai-tools-trigger" role="button" aria-label="AI 工具">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16">
            <path fill="currentColor" d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1v2h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2v-2h1a7 7 0 0 1 7-7h1V5.73A2 2 0 0 1 10 4a2 2 0 0 1 2-2m0 2a.5.5 0 0 0 0 1 .5.5 0 0 0 0-1M7.5 13a5 5 0 0 0-4.95 4.5H21.45A5 5 0 0 0 16.5 13h-9M9 18v1h2v-1H9m4 0v1h2v-1h-2z"/>
          </svg>
          <span class="ai-tools-label">AI 工具</span>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="12" height="12">
            <path fill="currentColor" d="M7 10l5 5 5-5z"/>
          </svg>
        </div>
      </n-dropdown>
    </div>

    <!-- 书名（点击可编辑） -->
    <div class="topbar-title">
      <n-input
        v-if="editingTitle"
        ref="titleInputRef"
        v-model:value="editTitleValue"
        size="small"
        class="title-edit-input"
        @keyup.enter="saveTitle"
        @blur="saveTitle"
      />
      <n-tooltip v-else trigger="hover" :show-arrow="false">
        <template #trigger>
          <span class="book-title-display" @click="startEditTitle" role="button" tabindex="0" aria-label="点击编辑书名">
            {{ props.title || props.slug }}
            <svg class="title-edit-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="12" height="12">
              <path fill="currentColor" d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
            </svg>
          </span>
        </template>
        <span>点击编辑书名</span>
      </n-tooltip>
    </div>

    <!-- 中间：统计数据 -->
    <div class="topbar-center">
      <div
        v-for="stat in stats"
        :key="stat.key"
        class="stat-item"
        role="group"
        :aria-label="stat.label"
      >
        <n-tooltip :show-arrow="false">
          <template #trigger>
            <div class="stat-content">
              <span class="stat-label">{{ stat.label }}</span>
              <span class="stat-value">{{ stat.value }}</span>
            </div>
          </template>
          <span>{{ stat.tooltip }}</span>
        </n-tooltip>
      </div>
    </div>

    <!-- 右侧：操作按钮 -->
    <div class="top-bar-actions">
      <!-- 备份按钮 -->
      <n-dropdown
        trigger="click"
        placement="bottom-end"
        :options="backupOptions"
        @select="handleBackupSelect"
      >
        <div class="action-trigger" role="button" aria-label="数据备份">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20">
            <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
          </svg>
        </div>
      </n-dropdown>

      <!-- 隐藏的文件选择器用于还原 -->
      <input
        ref="restoreInputRef"
        type="file"
        accept=".zip"
        style="display: none"
        @change="handleRestoreFile"
      />

      <!-- 导出按钮 -->
      <n-dropdown
        trigger="click"
        placement="bottom-end"
        :options="exportOptions"
        @select="handleExport"
      >
        <div class="action-trigger" role="button" aria-label="导出">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20">
            <path fill="currentColor" d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
          </svg>
        </div>
      </n-dropdown>

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

      <!-- 设置按钮 -->
      <div class="settings-trigger" @click="$emit('open-settings')" role="button" aria-label="打开设置">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18">
          <path fill="currentColor" d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.49.49 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96a.49.49 0 0 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6A3.6 3.6 0 1 1 12 8.4a3.6 3.6 0 0 1 0 7.2z"/>
        </svg>
      </div>

      <!-- 用户菜单 -->
      <n-dropdown
        v-if="authStore.isAuthenticated"
        trigger="click"
        placement="bottom-end"
        :options="userMenuOptions"
        @select="handleUserMenuSelect"
      >
        <div class="user-trigger" role="button" aria-label="用户菜单">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18">
            <path fill="currentColor" d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
          </svg>
          <span class="user-name">{{ authStore.user?.username }}</span>
        </div>
      </n-dropdown>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NTooltip, NSpin, NDropdown, NButton, NInput, useMessage } from 'naive-ui'
import { useStatsStore } from '@/stores/statsStore'
import { novelApi } from '@/api/novel'
import { downloadBackup, uploadBackup } from '@/api/backup'
import GlobalLLMEntryButton from '@/components/global/GlobalLLMEntryButton.vue'
import PromptPlazaEntryButton from '@/components/global/PromptPlazaEntryButton.vue'
import { useAuthStore } from '@/stores/authStore'

const props = defineProps<{
  slug: string
  title?: string
}>()

const emit = defineEmits<{
  'open-settings': []
  'update:title': [title: string]
}>()

const message = useMessage()
const router = useRouter()
const authStore = useAuthStore()

// ── 书名内联编辑 ────────────────────────────────
const editingTitle = ref(false)
const editTitleValue = ref('')
const titleInputRef = ref<HTMLInputElement | null>(null)

function startEditTitle() {
  editTitleValue.value = props.title || ''
  editingTitle.value = true
  nextTick(() => {
    titleInputRef.value?.focus()
  })
}

async function saveTitle() {
  if (!editingTitle.value) return
  const newTitle = editTitleValue.value.trim()
  editingTitle.value = false
  if (!newTitle || newTitle === (props.title || '')) return

  try {
    await novelApi.updateNovel(props.slug, { title: newTitle })
    emit('update:title', newTitle)
    message.success('书名已更新')
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '书名更新失败')
  }
}

// AI 工具组件引用（用于以编程方式触发各组件内部按钮）
const llmRef = ref<{ $el: HTMLElement } | null>(null)
const plazaRef = ref<{ $el: HTMLElement } | null>(null)

const aiToolsOptions = [
  { label: '⚙️ AI 控制台', key: 'llm' },
  { label: '✦ 提示词广场', key: 'plaza' },
]

function handleAiToolSelect(key: string) {
  if (key === 'llm') {
    llmRef.value?.$el?.querySelector('button')?.click()
  } else if (key === 'plaza') {
    plazaRef.value?.$el?.querySelector('button')?.click()
  }
}

/** 用户菜单 */
const userMenuOptions = computed(() => {
  const items: { label: string; key: string }[] = []
  if (authStore.isAdmin) {
    items.push({ label: '后台管理', key: 'admin' })
  }
  items.push({ label: '退出登录', key: 'logout' })
  return items
})

function handleUserMenuSelect(key: string) {
  if (key === 'logout') {
    authStore.logout()
    router.push('/login')
  } else if (key === 'admin') {
    router.push('/admin/dashboard')
  }
}

// 导出选项
const exportOptions = [
  { label: '📱 EPUB (电子书)', key: 'epub' },
  { label: '📄 PDF (打印)', key: 'pdf' },
  { label: '📝 DOCX (Word)', key: 'docx' },
  { label: '📋 Markdown', key: 'markdown' },
  { label: '📄 TXT (纯文本)', key: 'txt' }
]

// 备份选项
const backupOptions = [
  { label: '📦 下载备份 (ZIP)', key: 'download-backup' },
  { label: '📥 从备份还原...', key: 'restore-backup' },
]

const restoreInputRef = ref<HTMLInputElement | null>(null)
const backupLoading = ref(false)

async function handleBackupSelect(key: string) {
  if (key === 'download-backup') {
    backupLoading.value = true
    try {
      await downloadBackup(props.slug)
      message.success('备份导出完成')
    } catch (e: any) {
      message.error(e?.message || '备份导出失败')
    } finally {
      backupLoading.value = false
    }
  } else if (key === 'restore-backup') {
    restoreInputRef.value?.click()
  }
}

async function handleRestoreFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  backupLoading.value = true
  try {
    const result = await uploadBackup(props.slug, file)
    message.success(
      `还原完成：${result.stats.tables} 张表，${result.stats.total_rows} 行数据`,
    )
  } catch (e: any) {
    message.error(e?.message || '还原失败，请检查文件格式')
  } finally {
    backupLoading.value = false
    // 清空 input，允许重复选择同一文件
    input.value = ''
  }
}

async function handleExport(format: string) {
  try {
    message.info(`开始导出为 ${format} 格式...`)
    const blob = await novelApi.exportNovel(props.slug, format)

    // 文件名以书名命名，回退到 slug
    const safeName = (props.title || props.slug).replace(/[<>:"/\\|?*]/g, '_').replace(/\s+/g, '_').slice(0, 80)

    // 创建下载链接
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${safeName}.${format}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    
    message.success(`导出 ${format} 格式成功！`)
  } catch (error) {
    console.error('导出失败:', error)
    message.error('导出失败，请稍后重试')
  }
}

/** 跳转到在线阅读器 */
function openReader() {
  router.push(`/book/${props.slug}/reader`)
}

const statsStore = useStatsStore()

// Constants
const DECIMAL_PRECISION = 1
const MS_PER_DAY = 1000 * 60 * 60 * 24
const DAYS_THRESHOLD = 7

// State
const loading = ref(false)
const error = ref<string | null>(null)

// Fix: Remove .value before function call
const bookStats = computed(() => statsStore.getBookStats(props.slug))

const stats = computed(() => {
  if (!bookStats.value) return []

  const s = bookStats.value

  const totalWords = Number(s.total_words ?? 0)
  const rate = Number(s.completion_rate ?? 0)
  const avgWords = Number(s.avg_chapter_words ?? 0)
  const done = Number(s.completed_chapters ?? 0)
  const total = Number(s.total_chapters ?? 0)

  const formattedWords = totalWords.toLocaleString()
  const formattedCompletionRate = rate.toFixed(DECIMAL_PRECISION)
  const formattedAvgWords = avgWords.toLocaleString()

  return [
    {
      key: 'words',
      label: '总字数',
      value: formattedWords,
      tooltip: `当前书籍共 ${formattedWords} 字`
    },
    {
      key: 'chapters',
      label: '完成章节',
      value: `${done}/${total}`,
      tooltip: `已完成 ${done} 章，共 ${total} 章`
    },
    {
      key: 'completion',
      label: '完成率',
      value: `${formattedCompletionRate}%`,
      tooltip: `项目完成度：${formattedCompletionRate}%`
    },
    {
      key: 'avg',
      label: '平均字数',
      value: formattedAvgWords,
      tooltip: `每章平均 ${formattedAvgWords} 字`
    },
    {
      key: 'updated',
      label: '最后更新',
      value: formatDate(s.last_updated),
      tooltip: `最后更新时间：${s.last_updated}`
    }
  ]
})

function formatStatsError(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const data = (err as { response?: { data?: { detail?: unknown } } }).response?.data
    const d = data?.detail
    if (typeof d === 'string') return d
    if (Array.isArray(d)) {
      return d
        .map((x: { msg?: string }) => (typeof x?.msg === 'string' ? x.msg : JSON.stringify(x)))
        .join('; ')
    }
  }
  if (err instanceof Error) return err.message
  return String(err)
}

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return '—'
  try {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffDays = Math.floor(diffMs / MS_PER_DAY)

    if (diffDays === 0) {
      return '今天'
    } else if (diffDays === 1) {
      return '昨天'
    } else if (diffDays < DAYS_THRESHOLD) {
      return `${diffDays}天前`
    } else {
      return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
    }
  } catch {
    return dateStr
  }
}

async function loadStats() {
  loading.value = true
  error.value = null
  try {
    await statsStore.loadBookStats(props.slug)
  } catch (err) {
    console.error('Failed to load book stats:', err)
    error.value = `加载统计数据失败：${formatStatsError(err)}`
  } finally {
    loading.value = false
  }
}

async function retryLoad() {
  await loadStats()
}

onMounted(loadStats)
</script>

<style scoped>
/* ═══════════════════════════════════════════════════
   StatsTopBar — 与 AI 控制台一体化的顶部导航栏
   使用 CSS 变量，自动适配亮/暗主题
   ═══════════════════════════════════════════════════ */
.stats-top-bar {
  height: var(--plotpilot-topbar-height);
  background: var(--stats-bar-gradient);
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--plotpilot-topbar-padding-x);
  color: var(--nav-hero-text, #ffffff);
  position: relative;
  gap: var(--plotpilot-topbar-inner-gap);
  min-width: 0;
  /* 横向不允许出现滚动条：内容若溢出则靠中间 stat 区自然收窄 */
  overflow: hidden;
  border-bottom: 1px solid var(--app-border, rgba(255, 255, 255, 0.08));
  box-shadow:
    var(--app-shadow-sm, 0 1px 3px rgba(0, 0, 0, 0.08)),
    0 4px 16px var(--color-brand-border, rgba(79, 70, 229, 0.08));
}

/* 书名（点击可编辑） */
.topbar-title {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  max-width: 200px;
  min-width: 0;
}

.book-title-display {
  font-size: 14px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.15s;
  user-select: none;
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--nav-hero-text, #ffffff);
}

.book-title-display:hover {
  background: rgba(255, 255, 255, 0.16);
}

.title-edit-icon {
  opacity: 0;
  transition: opacity 0.15s;
  flex-shrink: 0;
}

.book-title-display:hover .title-edit-icon {
  opacity: 0.6;
}

.title-edit-input {
  width: 180px;
}

/* 左侧：AI 控制台入口 */
.topbar-left {
  flex-shrink: 0;
  z-index: 2;
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  align-items: center;
  gap: var(--plotpilot-topbar-inner-gap);
}

/* 隐藏的 AI 入口组件（仅保留功能，不参与布局） */
.ai-hidden-entries {
  position: absolute;
  visibility: hidden;
  pointer-events: none;
  width: 0;
  height: 0;
  overflow: hidden;
  top: -9999px;
}

/* 统一 AI 工具触发按钮 */
.ai-tools-trigger {
  display: flex;
  align-items: center;
  gap: var(--plotpilot-space-2);
  padding: var(--plotpilot-ai-trigger-pad-y) var(--plotpilot-ai-trigger-pad-x);
  border-radius: var(--app-radius-md);
  cursor: pointer;
  background: var(--nav-hero-pill-bg-top, rgba(255, 255, 255, 0.16));
  border: 1px solid var(--nav-hero-pill-border, rgba(255, 255, 255, 0.28));
  color: var(--nav-hero-text, #ffffff);
  transition: all var(--app-transition);
  white-space: nowrap;
  box-shadow: var(--nav-hero-shadow);
  user-select: none;
}

.ai-tools-trigger:hover {
  background: rgba(255, 255, 255, 0.24);
}

.ai-tools-label {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.01em;
}

/* 中间：统计数据 */
.topbar-center {
  flex: 1;
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 0;
  z-index: 1;
  overflow: hidden;
}

.stats-top-bar.loading,
.stats-top-bar.error {
  justify-content: center;
}

.stats-top-bar.error span {
  font-size: 14px;
  opacity: 0.9;
}

.stat-item {
  flex: 0 1 auto;
  text-align: center;
  cursor: help;
  padding: 4px 10px;
  border-radius: var(--app-radius-sm);
  transition: background 0.2s ease;
}

.stat-item:hover {
  background: rgba(255, 255, 255, 0.12);
}

.stat-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  align-items: center;
}

.stat-label {
  font-size: 12px;
  opacity: 0.92;
  font-weight: 600;
  letter-spacing: 0.03em;
  white-space: nowrap;
  color: var(--nav-hero-text-muted, rgba(255, 255, 255, 0.86));
}

.stat-value {
  font-size: var(--plotpilot-topbar-stat-value-size);
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.2;
  color: var(--nav-hero-text, #ffffff);
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
}

.stat-item:hover .stat-value {
  transform: scale(1.04);
  transition: transform 0.2s ease;
}

/* 右侧：操作按钮 */
.top-bar-actions {
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  gap: var(--plotpilot-space-2);
  flex: 0 0 auto;
  align-items: center;
}

.action-trigger {
  width: var(--plotpilot-topbar-hit-lg);
  height: var(--plotpilot-topbar-hit-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  opacity: 0.9;
  transition: all 0.18s ease;
  border-radius: var(--app-radius-sm);
  color: inherit;
}

.action-trigger:hover {
  opacity: 1;
  background: rgba(255, 255, 255, 0.16);
  transform: rotate(45deg);
}

/* 右侧：设置触发器 */
.settings-trigger {
  flex-shrink: 0;
  width: var(--plotpilot-topbar-hit-md);
  height: var(--plotpilot-topbar-hit-md);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  opacity: 0.9;
  transition: all 0.18s ease;
  border-radius: var(--app-radius-sm);
  color: inherit;
}

.settings-trigger:hover {
  opacity: 1;
  background: rgba(255, 255, 255, 0.16);
  transform: rotate(45deg);
}

/* 用户菜单触发按钮 */
.user-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  cursor: pointer;
  opacity: 0.9;
  transition: all 0.18s ease;
  border-radius: var(--app-radius-sm);
  color: inherit;
  user-select: none;
}

.user-trigger:hover {
  opacity: 1;
  background: rgba(255, 255, 255, 0.16);
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dropdown-item-icon {
  margin-right: 8px;
  font-size: 16px;
}

/* Accessibility: Focus styles */
.stat-item:focus-within {
  outline: 2px solid rgba(255, 255, 255, 0.55);
  outline-offset: 4px;
  border-radius: 4px;
}

.settings-trigger:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.55);
  outline-offset: 2px;
}

/* Responsive design — 全程单行横向，窄屏可横向滚动 */
@media (max-width: 900px) {
  .stats-top-bar {
    flex-wrap: nowrap;
    padding: var(--plotpilot-space-3) var(--plotpilot-topbar-padding-x);
    gap: var(--plotpilot-topbar-inner-gap);
  }

  .topbar-left {
    flex-shrink: 0;
  }

  .topbar-left :deep(.global-llm-main.variant-topbar),
  .topbar-left :deep(.plaza-main.variant-topbar) {
    min-height: 42px;
    padding: 6px 10px;
  }

  .topbar-center {
    justify-content: flex-end;
    flex: 1 1 auto;
  }

  .stat-value {
    font-size: clamp(13px, 0.9rem + 0.2vw, 15px);
  }

  .settings-trigger {
    position: static;
    transform: none;
  }

  .settings-trigger:hover {
    transform: rotate(45deg);
  }
}

@media (max-width: 480px) {
  .stat-item {
    flex: 0 0 33%;
  }

  .stat-value {
    font-size: 14px;
  }

  .stat-label {
    font-size: 12px;
  }
}
</style>
