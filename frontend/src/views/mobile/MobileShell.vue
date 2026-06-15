<template>
  <div class="mobile-shell">
    <MobileTopBar :title="bookTitle || '墨枢'" />

    <!-- Tab 内容区 -->
    <div class="mobile-shell-body">
      <KeepAlive>
        <MobileHome v-if="activeTab === 'home'" :slug="slug" @enter-novel="handleEnterNovel" />
        <MobileTOC v-else-if="activeTab === 'toc'" :slug="slug" :chapters="chapters" :current-chapter-id="currentChapterId" @select-chapter="handleChapterSelect" />
        <MobileWrite v-else-if="activeTab === 'write'" :slug="slug" :book-title="bookTitle" :chapters="chapters" :current-chapter-id="currentChapterId" :chapter-content="chapterContent" :chapter-loading="chapterLoading" :generation-prefs="generationPrefs" @chapter-updated="emit('chapter-updated')" @select-chapter="handleChapterSelect" />
        <MobileLore v-else-if="activeTab === 'lore'" :slug="slug" :current-chapter="currentChapter" :generation-prefs="generationPrefs" />
        <MobileMore v-else-if="activeTab === 'more'" :slug="slug" />
      </KeepAlive>
    </div>

    <!-- 底部 Tab 栏 -->
    <div class="mobile-tab-bar">
      <div
        v-for="tab in tabs"
        :key="tab.key"
        class="mobile-tab-item"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        <span class="mobile-tab-icon">{{ tab.icon }}</span>
        <span class="mobile-tab-label">{{ tab.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/** 移动端底部 Tab 壳 — 5 Tab 导航容器
 *
 * 作者: Axelton
 */
import { ref, computed, type ComponentPublicInstance } from 'vue'
import MobileTopBar from './MobileTopBar.vue'
import MobileHome from './MobileHome.vue'
import MobileTOC from './MobileTOC.vue'
import MobileWrite from './MobileWrite.vue'
import MobileLore from './MobileLore.vue'
import MobileMore from './MobileMore.vue'

interface Chapter {
  id: number
  number: number
  title: string
  word_count: number
}

const props = defineProps<{
  slug: string
  bookTitle: string
  chapters: Chapter[]
  currentChapterId: number | null
  chapterContent: string
  chapterLoading: boolean
  generationPrefs: Record<string, unknown> | null
}>()

const emit = defineEmits<{
  'chapter-updated': []
  'select-chapter': [id: number, title: string]
  'go-home': []
}>()

type TabKey = 'home' | 'toc' | 'write' | 'lore' | 'more'

const activeTab = ref<TabKey>('write')

const tabs: { key: TabKey; label: string; icon: string }[] = [
  { key: 'home', label: '首页', icon: '🏠' },
  { key: 'toc', label: '目录', icon: '📋' },
  { key: 'write', label: '写作', icon: '✏️' },
  { key: 'lore', label: '设定', icon: '📚' },
  { key: 'more', label: '更多', icon: '⋯' },
]

const currentChapter = computed(() => {
  if (!props.currentChapterId) return null
  return props.chapters.find(ch => ch.id === props.currentChapterId) || null
})

function handleEnterNovel(slug: string) {
  // 由父组件处理路由跳转
}

function handleChapterSelect(id: number, title: string) {
  activeTab.value = 'write'
  emit('select-chapter', id, title)
}
</script>

<style scoped>
.mobile-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--app-page-bg, #f0f2f8);
}

.mobile-shell-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* 底部 Tab 栏 */
.mobile-tab-bar {
  height: 52px;
  min-height: 52px;
  display: flex;
  background: var(--app-surface, #fff);
  border-top: 1px solid var(--app-border, #e2e8f0);
  flex-shrink: 0;
  padding-bottom: env(safe-area-inset-bottom, 0);
}

.mobile-tab-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  cursor: pointer;
  color: var(--app-text-muted, #94a3b8);
  transition: color 0.15s;
  -webkit-tap-highlight-color: transparent;
  user-select: none;
}

.mobile-tab-item.active {
  color: #4f46e5;
}

.mobile-tab-icon {
  font-size: 18px;
  line-height: 1;
}

.mobile-tab-label {
  font-size: 10px;
  font-weight: 600;
}
</style>
