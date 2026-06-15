<template>
  <div class="mobile-lore">
    <!-- 胶囊标签 -->
    <div class="mobile-lore-pills">
      <div
        v-for="p in panels"
        :key="p.key"
        class="mobile-lore-pill"
        :class="{ active: activePanel === p.key }"
        @click="activePanel = p.key"
      >
        {{ p.label }}
      </div>
    </div>

    <!-- 面板内容区 -->
    <div class="mobile-lore-body">
      <Suspense>
        <template #default>
          <component
            :is="activeComponent"
            v-if="activeComponent"
            :key="activePanel"
            :slug="slug"
            :currentChapter="currentChapter"
            :generationPrefs="generationPrefs"
          />
        </template>
        <template #fallback>
          <div class="mobile-lore-loading">
            <n-spin size="medium" />
            <p>加载中…</p>
          </div>
        </template>
      </Suspense>

      <div v-if="loadError" class="mobile-lore-error">
        <p>加载失败</p>
        <n-button size="small" @click="retryLoad">重试</n-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/** 移动端设定 Tab — 9 子面板，胶囊标签 + 异步加载
 *
 * 作者: Axelton
 */
import { ref, computed, defineAsyncComponent, type Component } from 'vue'
import { NSpin, NButton } from 'naive-ui'

const props = defineProps<{
  slug: string
  currentChapter: { id: number; number: number; title: string; word_count: number } | null
  generationPrefs: Record<string, unknown> | null
}>()

const panels = [
  { key: 'bible', label: '设定集' },
  { key: 'manuscript', label: '手稿' },
  { key: 'knowledge', label: '知识库' },
  { key: 'world', label: '世界观' },
  { key: 'evolution', label: '演进' },
  { key: 'foreshadow', label: '伏笔' },
  { key: 'dialogue', label: '对话' },
  { key: 'context', label: '上下文' },
  { key: 'dashboard', label: '数据' },
]

const activePanel = ref('bible')
const loadError = ref(false)

function onLoadError() {
  loadError.value = true
}

function retryLoad() {
  loadError.value = false
  // 切换 panel 再切回来触发重新加载
  const cur = activePanel.value
  activePanel.value = cur === 'bible' ? 'manuscript' : 'bible'
  setTimeout(() => { activePanel.value = cur }, 50)
}

/** 各面板异步组件（提前定义，避免 computed 内重复创建） */
const loreComponents: Record<string, Component> = {
  bible: defineAsyncComponent({
    loader: () => import('@/components/panels/BiblePanel.vue'),
    onError: onLoadError,
  }),
  manuscript: defineAsyncComponent({
    loader: () => import('@/components/workbench/ManuscriptPropsPanel.vue'),
    onError: onLoadError,
  }),
  knowledge: defineAsyncComponent({
    loader: () => import('@/components/knowledge/KnowledgePanel.vue'),
    onError: onLoadError,
  }),
  world: defineAsyncComponent({
    loader: () => import('@/components/workbench/WorldbuildingPanel.vue'),
    onError: onLoadError,
  }),
  evolution: defineAsyncComponent({
    loader: () => import('@/components/workbench/StoryEvolutionPanel.vue'),
    onError: onLoadError,
  }),
  foreshadow: defineAsyncComponent({
    loader: () => import('@/components/workbench/ForeshadowLedgerPanel.vue'),
    onError: onLoadError,
  }),
  dialogue: defineAsyncComponent({
    loader: () => import('@/components/workbench/CharacterDialoguePanel.vue'),
    onError: onLoadError,
  }),
  context: defineAsyncComponent({
    loader: () => import('@/components/workbench/CurrentChapterContextPanel.vue'),
    onError: onLoadError,
  }),
  dashboard: defineAsyncComponent({
    loader: () => import('@/components/workbench/NarrativeDashboardPanel.vue'),
    onError: onLoadError,
  }),
}

const activeComponent = computed(() => loreComponents[activePanel.value] || null)
</script>

<style scoped>
.mobile-lore {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 胶囊标签 */
.mobile-lore-pills {
  display: flex;
  gap: 6px;
  padding: 10px 12px;
  overflow-x: auto;
  scrollbar-width: none;
  flex-shrink: 0;
  background: var(--app-surface, #fff);
  border-bottom: 1px solid var(--app-border, #e2e8f0);
}
.mobile-lore-pills::-webkit-scrollbar { display: none; }

.mobile-lore-pill {
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--app-text-muted, #94a3b8);
  background: var(--app-surface-subtle, #f1f5f9);
  border-radius: 12px;
  white-space: nowrap;
  cursor: pointer;
  transition: all 0.15s;
  -webkit-tap-highlight-color: transparent;
  user-select: none;
}
.mobile-lore-pill.active { color: #fff; background: #4f46e5; }

/* 面板内容区 */
.mobile-lore-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

/* 移动端面板适配：强制子元素适应窄屏 */
.mobile-lore-body :deep(*) {
  max-width: 100%;
  box-sizing: border-box;
}

/* 覆盖桌面面板常见固定宽度模式 */
.mobile-lore-body :deep(.n-card),
.mobile-lore-body :deep(.n-tabs),
.mobile-lore-body :deep(table),
.mobile-lore-body :deep(.panel-container) {
  max-width: 100% !important;
  width: auto !important;
}

/* 让 Grid/两栏布局在窄屏下单列 */
.mobile-lore-body :deep(.n-grid) {
  grid-template-columns: 1fr !important;
}

.mobile-lore-body :deep([style*="width"]) {
  max-width: 100% !important;
}

/* 减小移动端面板内边距 */
.mobile-lore-body :deep(.n-card > .n-card__content) {
  padding: 10px !important;
}

.mobile-lore-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--app-text-muted);
  gap: 12px;
}

.mobile-lore-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--app-text-muted);
  gap: 12px;
}
</style>
