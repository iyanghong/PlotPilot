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
