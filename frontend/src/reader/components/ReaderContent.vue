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
    <!-- 仿真翻页模式：Canvas 渲染 -->
    <PageFlipCanvas
      v-else-if="pageMode === 'curl'"
      ref="pageFlipRef"
      :content="chapter.content"
      :settings="settings"
      :is-last-chapter="isLastChapter"
      @prev-chapter="$emit('prev-chapter')"
      @next-chapter="$emit('next-chapter')"
    />
    <!-- 滚动/分页模式：DOM 渲染 -->
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
import { computed, ref } from 'vue'
import { NSpin, NButton } from 'naive-ui'
import type { ChapterContent, ReaderSettings } from '../types'
import { settingsToCSSVars } from '../composables/useReaderSettings'
import PageFlipCanvas from './PageFlipCanvas.vue'

const props = defineProps<{
  chapter: ChapterContent | null
  totalChapters: number
  settings: ReaderSettings
  loading: boolean
  error: string | null
  isLastChapter: boolean
}>()

defineEmits<{ retry: []; 'prev-chapter': []; 'next-chapter': [] }>()

/** PageFlipCanvas 引用，用于键盘翻页 */
const pageFlipRef = ref<InstanceType<typeof PageFlipCanvas> | null>(null)

/** 暴露翻页方法供父组件键盘事件调用 */
defineExpose({
  prevPage() { pageFlipRef.value?.prevPage() },
  nextPage() { pageFlipRef.value?.nextPage() },
})

// 章节标题：优先使用实际标题，否则回退到「第 N 章」
const displayTitle = computed(() => {
  if (!props.chapter) return ''
  if (props.chapter.title?.trim()) return props.chapter.title.trim()
  return `第 ${props.chapter.number} 章`
})

// 将章节正文按换行符拆分为段落
const paragraphs = computed(() => {
  const content = props.chapter?.content || ''
  return content
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
})

// 将 ReaderSettings 转为 CSS 自定义属性
const styleVars = computed(() => settingsToCSSVars(props.settings))
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

/* 翻页模式：多列布局，横向滚动 */
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
