<template>
  <div class="mobile-toc">
    <div class="mobile-toc-list">
      <div
        v-for="ch in chapters"
        :key="ch.id"
        class="mobile-toc-item"
        :class="{ active: currentChapterId === ch.id }"
        @click="$emit('select-chapter', ch.id, ch.title)"
      >
        <span class="mobile-toc-num">第{{ ch.number }}章</span>
        <span class="mobile-toc-title">{{ ch.title }}</span>
        <n-tag size="small" :type="ch.word_count > 0 ? 'success' : 'default'" round>
          {{ ch.word_count > 0 ? '已收' : '空' }}
        </n-tag>
      </div>

      <div v-if="!chapters.length" class="mobile-toc-empty">
        <p>暂无章节</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/** 移动端目录 Tab — 章节目录
 *
 * 作者: Axelton
 */
import { NTag } from 'naive-ui'

interface Chapter {
  id: number
  number: number
  title: string
  word_count: number
}

defineProps<{
  slug: string
  chapters: Chapter[]
  currentChapterId: number | null
}>()

defineEmits<{
  'select-chapter': [id: number, title: string]
}>()
</script>

<style scoped>
.mobile-toc {
  height: 100%;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.mobile-toc-list {
  padding: 8px;
}

.mobile-toc-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.mobile-toc-item:active {
  background: var(--app-surface-subtle, #f1f5f9);
}

.mobile-toc-item.active {
  background: #eef2ff;
}

.mobile-toc-num {
  font-size: 13px;
  font-weight: 600;
  color: var(--app-text-primary);
  white-space: nowrap;
}

.mobile-toc-title {
  flex: 1;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--app-text-secondary);
}

.mobile-toc-empty {
  text-align: center;
  padding-top: 48px;
  color: var(--app-text-muted);
}
</style>
