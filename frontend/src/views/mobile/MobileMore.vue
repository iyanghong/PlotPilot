<template>
  <div class="mobile-more">
    <div class="mobile-more-list">
      <div class="mobile-more-item" @click="handleAI">
        <span class="mobile-more-icon">⚙️</span>
        <span class="mobile-more-label">AI 控制台</span>
        <span class="mobile-more-arrow">›</span>
      </div>
      <div class="mobile-more-item" @click="handlePlaza">
        <span class="mobile-more-icon">✦</span>
        <span class="mobile-more-label">提示词广场</span>
        <span class="mobile-more-arrow">›</span>
      </div>
      <div class="mobile-more-item" @click="handleReader">
        <span class="mobile-more-icon">👁</span>
        <span class="mobile-more-label">在线预览</span>
        <span class="mobile-more-arrow">›</span>
      </div>
      <div class="mobile-more-divider" />
      <div class="mobile-more-item" @click="handleExport('epub')">
        <span class="mobile-more-icon">📱</span>
        <span class="mobile-more-label">导出 EPUB</span>
        <span class="mobile-more-arrow">›</span>
      </div>
      <div class="mobile-more-item" @click="handleExport('pdf')">
        <span class="mobile-more-icon">📄</span>
        <span class="mobile-more-label">导出 PDF</span>
        <span class="mobile-more-arrow">›</span>
      </div>
      <div class="mobile-more-item" @click="handleExport('docx')">
        <span class="mobile-more-icon">📝</span>
        <span class="mobile-more-label">导出 DOCX</span>
        <span class="mobile-more-arrow">›</span>
      </div>
      <div class="mobile-more-divider" />
      <div class="mobile-more-item" @click="handleSettings">
        <span class="mobile-more-icon">⚙</span>
        <span class="mobile-more-label">应用设置</span>
        <span class="mobile-more-arrow">›</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/** 移动端更多 Tab — AI 控制台 / 提示词广场 / 导出 / 预览 / 设置
 *
 * 作者: Axelton
 */
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useAppSettingsShellStore } from '@/stores/appSettingsShellStore'
import { novelApi } from '@/api/novel'

const props = defineProps<{
  slug: string
}>()

const router = useRouter()
const message = useMessage()
const appSettingsShell = useAppSettingsShellStore()

function handleAI() {
  document.querySelector<HTMLButtonElement>('.global-llm-main button')?.click()
}

function handlePlaza() {
  document.querySelector<HTMLButtonElement>('.plaza-main button')?.click()
}

function handleReader() {
  router.push(`/book/${props.slug}/reader`)
}

async function handleExport(format: string) {
  try {
    message.info(`开始导出为 ${format} 格式...`)
    const blob = await novelApi.exportNovel(props.slug, format)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `novel-${props.slug}.${format}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    message.success(`导出 ${format} 成功`)
  } catch {
    message.error('导出失败')
  }
}

function handleSettings() {
  appSettingsShell.open()
}
</script>

<style scoped>
.mobile-more {
  height: 100%;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.mobile-more-list {
  padding: 0;
}

.mobile-more-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  cursor: pointer;
  border-bottom: 1px solid var(--app-border, rgba(0, 0, 0, 0.04));
  -webkit-tap-highlight-color: transparent;
  user-select: none;
}

.mobile-more-item:active {
  background: var(--app-surface-subtle, #f1f5f9);
}

.mobile-more-icon {
  font-size: 20px;
  width: 28px;
  text-align: center;
  flex-shrink: 0;
}

.mobile-more-label {
  flex: 1;
  font-size: 15px;
  font-weight: 500;
}

.mobile-more-arrow {
  font-size: 18px;
  color: var(--app-text-muted);
}

.mobile-more-divider {
  height: 8px;
  background: var(--app-page-bg, #f0f2f8);
}
</style>
