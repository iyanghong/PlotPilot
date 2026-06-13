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
      >✕</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Bookmark } from '../types'

const props = defineProps<{ bookmarks: Bookmark[] }>()

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
.reader-bookmarks { padding: 8px 0; }
.bookmarks-empty { text-align: center; color: #999; padding: 24px; font-size: 14px; }
.bookmark-item { display: flex; align-items: center; gap: 8px; padding: 10px 12px; cursor: pointer; border-radius: 6px; transition: background 0.15s; }
.bookmark-item:hover { background: rgba(0, 0, 0, 0.04); }
.bookmark-chapter { font-weight: 600; font-size: 13px; flex-shrink: 0; }
.bookmark-title { flex: 1; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bookmark-time { font-size: 11px; color: #999; flex-shrink: 0; }
.bookmark-remove { background: transparent; border: none; cursor: pointer; font-size: 12px; color: #ccc; padding: 2px; }
.bookmark-remove:hover { color: #e74c3c; }
</style>
