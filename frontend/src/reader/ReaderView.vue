<template>
  <div class="reader-view" :style="cssVars()">
    <ReaderTopBar
      :title="currentChapter?.title || '加载中...'"
      :is-bookmarked="isBookmarked"
      :visible="topBarVisible"
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
      class="reader-content-area"
      @retry="currentChapter && loadChapter(currentChapter.number)"
    />

    <ReaderBottomBar
      v-if="currentChapter"
      :current-number="currentChapter.number"
      :total-chapters="totalChapters"
      :is-first-chapter="isFirstChapter"
      :is-last-chapter="isLastChapter"
      :visible="bottomBarVisible"
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
      @remove-bookmark="(num: number) => removeBookmark(num)"
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

/** 滚动状态 — 用于控制栏位可见性 */
const scrollY = ref(0)
const viewHeight = ref(window.innerHeight)

/** 滚动到顶部（阈值 60px） */
const isAtTop = computed(() => scrollY.value < 60)

/** 滚动到底部（阈值 120px，考虑底栏高度） */
const isAtBottom = computed(() => {
  const docHeight = document.documentElement.scrollHeight
  return scrollY.value + viewHeight.value >= docHeight - 120
})

/** 顶栏可见：滚动在顶部 */
const topBarVisible = computed(() => isAtTop.value)

/** 底栏可见：滚动在底部 */
const bottomBarVisible = computed(() => isAtBottom.value)

/** 更新滚动状态 */
function handleScroll() {
  scrollY.value = window.scrollY
}

/** 已读章节集合：当前章节之前的全部标记为已读 */
const readSet = computed(() => {
  const s = new Set<number>()
  for (const ch of toc.value) {
    if (ch.number < (currentChapter.value?.number ?? 0)) {
      s.add(ch.number)
    }
  }
  return s
})

/** 当前章节是否已添加书签 */
const isBookmarked = computed(() =>
  currentChapter.value ? hasBookmark(currentChapter.value.number) : false
)

/** 键盘导航：← 上一章 → 下一章 */
function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowLeft') {
    e.preventDefault()
    goPrev()
  } else if (e.key === 'ArrowRight') {
    e.preventDefault()
    goNext()
  }
}

/** 切换当前章节书签 */
function handleToggleBookmark() {
  if (!currentChapter.value) return
  toggleBookmark(
    currentChapter.value.number,
    currentChapter.value.title || `第 ${currentChapter.value.number} 章`
  )
}

/** 合并设置更新 */
function handleSettingsUpdate(newSettings: ReaderSettings) {
  Object.assign(settings, newSettings)
}

/** 返回工作台 */
function goBack() {
  router.push(`/book/${slug}/workbench`)
}

onMounted(async () => {
  window.addEventListener('keydown', handleKeydown)
  window.addEventListener('scroll', handleScroll, { passive: true })
  window.addEventListener('resize', () => { viewHeight.value = window.innerHeight })
  const chapterNum = chapterNumParam ? Number(chapterNumParam) : undefined
  await init(chapterNum)
  // 恢复滚动位置，并初始化滚动状态
  const savedTop = getSavedScrollTop()
  if (savedTop > 0) {
    window.scrollTo(0, savedTop)
  }
  scrollY.value = window.scrollY
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('scroll', handleScroll)
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

/* 补偿固定顶栏/底栏高度，防止内容被遮挡 */
.reader-content-area {
  padding-top: 48px;
  padding-bottom: 56px;
}
</style>
