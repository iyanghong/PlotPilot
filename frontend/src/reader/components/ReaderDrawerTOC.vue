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
              <span v-if="readSet.has(ch.number)" class="toc-check">&#10003;</span>
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
import type { ChapterMeta, Bookmark } from '../types'
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

/** 当前激活的 Tab */
const activeTab = ref('toc')

/** 选择章节跳转并关闭抽屉 */
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
