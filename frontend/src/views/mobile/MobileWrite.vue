<template>
  <div class="mobile-write">
    <!-- 二级子页签 -->
    <div class="mobile-write-subtabs">
      <div
        v-for="t in subTabs"
        :key="t.key"
        class="mobile-write-subtab"
        :class="{ active: activeSubTab === t.key }"
        @click="switchTab(t.key)"
      >
        {{ t.label }}
      </div>
    </div>

    <!-- 正文编辑 -->
    <div v-if="activeSubTab === 'manuscript'" class="mobile-write-body">
      <div v-if="!currentChapter" class="mobile-write-empty">
        <p>请在目录中选择章节</p>
      </div>
      <template v-else>
        <div class="mobile-write-editor">
          <div class="mobile-write-editor-head">
            <span class="mobile-write-chapter-label">
              第{{ currentChapter.number }}章 {{ currentChapter.title }}
            </span>
            <n-tag size="small" :type="currentChapter.word_count > 0 ? 'success' : 'default'" round>
              {{ currentChapter.word_count > 0 ? `${currentChapter.word_count}字` : '未收稿' }}
            </n-tag>
          </div>
          <n-input
            v-model:value="editorContent"
            type="textarea"
            placeholder="章节内容…"
            class="mobile-write-textarea"
            :disabled="chapterLoading"
          />
        </div>
        <div class="mobile-write-actions">
          <n-space :size="10" vertical>
            <n-button type="primary" size="medium" block :loading="saving" @click="handleSave">
              保存
            </n-button>
            <n-button size="medium" block :loading="aiGenerating" @click="handleAiGenerate">
              🤖 AI 生成本章
            </n-button>
          </n-space>
        </div>
      </template>
    </div>

    <!-- 元素 -->
    <div v-else-if="activeSubTab === 'elements'" class="mobile-write-body">
      <div v-if="!currentChapter" class="mobile-write-empty"><p>请先选择章节</p></div>
      <div v-else-if="elementsLoading" class="mobile-write-loading"><n-spin size="medium" /></div>
      <div v-else class="mobile-write-info-cards">
        <!-- 结构分析 -->
        <div v-if="structure" class="mw-info-card">
          <div class="mw-card-title">📊 章节结构</div>
          <div class="mw-card-grid">
            <div class="mw-stat"><span class="mw-stat-val">{{ structure.word_count ?? '-' }}</span><span class="mw-stat-lbl">字数</span></div>
            <div class="mw-stat"><span class="mw-stat-val">{{ structure.paragraph_count ?? '-' }}</span><span class="mw-stat-lbl">段落</span></div>
            <div class="mw-stat"><span class="mw-stat-val">{{ fmtRatio(structure.dialogue_ratio) }}</span><span class="mw-stat-lbl">对话占比</span></div>
            <div class="mw-stat"><span class="mw-stat-val">{{ structure.scene_count ?? '-' }}</span><span class="mw-stat-lbl">场景</span></div>
          </div>
          <div class="mw-card-row" v-if="structure.pacing">
            <span class="mw-card-label">节奏</span><n-tag size="small" round>{{ structure.pacing }}</n-tag>
          </div>
        </div>

        <!-- 微节拍 -->
        <div v-if="microBeats.length" class="mw-info-card">
          <div class="mw-card-title">🥁 微节拍 ({{ microBeats.length }})</div>
          <div v-for="(beat, i) in microBeats" :key="i" class="mw-beat-item">
            <div class="mw-beat-hd">
              <span class="mw-beat-idx">#{{ i + 1 }}</span>
              <span class="mw-beat-desc">{{ beat.description }}</span>
            </div>
            <div class="mw-beat-tags" v-if="beat.cast_refs?.length">
              <n-tag v-for="c in beat.cast_refs" :key="c" size="tiny" type="info">{{ c }}</n-tag>
            </div>
            <div class="mw-beat-meta" v-if="beat.pov">
              POV: {{ beat.pov }}<span v-if="beat.function"> · {{ beat.function }}</span>
            </div>
          </div>
        </div>
        <div v-else class="mw-info-card">
          <div class="mw-card-title">🥁 微节拍</div>
          <p class="mw-card-empty">暂无微节拍数据，AI 生成章节后自动填充</p>
        </div>
      </div>
    </div>

    <!-- 状态 -->
    <div v-else-if="activeSubTab === 'status'" class="mobile-write-body">
      <div v-if="!currentChapter" class="mobile-write-empty"><p>请先选择章节</p></div>
      <div v-else-if="reviewLoading" class="mobile-write-loading"><n-spin size="medium" /></div>
      <div v-else class="mobile-write-info-cards">
        <div class="mw-info-card">
          <div class="mw-card-title">📋 审阅状态</div>
          <div class="mw-card-row">
            <n-tag :type="reviewStatusType" size="medium" round>{{ reviewStatus }}</n-tag>
          </div>
          <div v-if="reviewMemo" class="mw-card-row">
            <span class="mw-card-label">评语</span>
            <p class="mw-memo">{{ reviewMemo }}</p>
          </div>
          <div class="mw-card-row" v-if="reviewUpdated">
            <span class="mw-card-label">更新时间</span>
            <span class="mw-card-val">{{ reviewUpdated }}</span>
          </div>
          <div class="mw-card-actions">
            <n-button size="small" :loading="aiReviewing" @click="handleAiReview">🤖 AI 审阅</n-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 质量 -->
    <div v-else-if="activeSubTab === 'quality'" class="mobile-write-body">
      <div v-if="!currentChapter" class="mobile-write-empty"><p>请先选择章节</p></div>
      <div v-else-if="guardrailLoading" class="mobile-write-loading"><n-spin size="medium" /></div>
      <div v-else-if="guardrail" class="mobile-write-info-cards">
        <div class="mw-info-card">
          <div class="mw-card-title">🛡 质量护栏</div>
          <div class="mw-gr-score" :class="guardrail.passed ? 'pass' : 'warn'">
            <span class="mw-gr-num">{{ fmtScore(guardrail.overall_score) }}</span>
            <span class="mw-gr-label">{{ guardrail.passed ? '通过' : '待关注' }}</span>
          </div>
          <!-- 各维度得分 -->
          <div v-if="guardrail.dimensions?.length" class="mw-gr-dims">
            <div v-for="d in guardrail.dimensions" :key="d.key" class="mw-gr-dim">
              <span class="mw-gr-dim-name">{{ d.name }}</span>
              <div class="mw-gr-dim-bar-bg">
                <div class="mw-gr-dim-bar" :style="{ width: (d.score * 100) + '%' }" :class="d.score >= 0.8 ? 'good' : d.score >= 0.5 ? 'mid' : 'bad'"></div>
              </div>
              <span class="mw-gr-dim-score">{{ fmtScore(d.score) }}</span>
            </div>
          </div>
          <!-- 违规 -->
          <div v-if="guardrail.violations?.length" class="mw-violations">
            <div class="mw-card-subtitle">⚠️ 违规提示 ({{ guardrail.violations.length }})</div>
            <div v-for="v in guardrail.violations" :key="v.description" class="mw-violation">
              <n-tag size="tiny" :type="v.severity === 'critical' ? 'error' : 'warning'">{{ v.severity }}</n-tag>
              <span class="mw-v-desc">{{ v.description }}</span>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="mobile-write-info-cards">
        <div class="mw-info-card">
          <div class="mw-card-title">🛡 质量护栏</div>
          <p class="mw-card-empty">暂无护栏数据，保存章节后自动生成</p>
        </div>
      </div>
    </div>

    <!-- 追踪 -->
    <div v-else-if="activeSubTab === 'trace'" class="mobile-write-body">
      <div v-if="autopilotLoading" class="mobile-write-loading"><n-spin size="medium" /></div>
      <div v-else class="mobile-write-info-cards">
        <div class="mw-info-card">
          <div class="mw-card-title">🔍 生成追踪</div>
          <div class="mw-card-row">
            <span class="mw-card-label">自动状态</span>
            <n-tag :type="apRunning ? 'info' : 'default'" size="small" round>{{ apRunning ? '运行中' : '空闲' }}</n-tag>
          </div>
          <div class="mw-card-row" v-if="apStage">
            <span class="mw-card-label">当前阶段</span>
            <span class="mw-card-val">{{ apStage }}</span>
          </div>
          <div class="mw-card-row" v-if="apStep">
            <span class="mw-card-label">当前步骤</span>
            <span class="mw-card-val">{{ apStep }}</span>
          </div>
          <div class="mw-card-row" v-if="apEpoch != null">
            <span class="mw-card-label">生成轮次</span>
            <span class="mw-card-val">第 {{ apEpoch }} 轮</span>
          </div>
          <!-- 熔断器 -->
          <div v-if="circuitBreaker" class="mw-card-section">
            <div class="mw-card-subtitle">⚡ 熔断器</div>
            <div class="mw-card-row">
              <span class="mw-card-label">状态</span>
              <n-tag :type="cbStatusType" size="small" round>{{ cbStatusLabel }}</n-tag>
            </div>
            <div class="mw-card-row">
              <span class="mw-card-label">错误数</span>
              <span class="mw-card-val">{{ circuitBreaker.error_count }} / {{ circuitBreaker.max_errors }}</span>
            </div>
            <div v-if="circuitBreaker.last_error" class="mw-cb-error">
              {{ circuitBreaker.last_error.message }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- AI托管驾驶舱：v-show 保持挂载以维持 SSE 连接和状态轮询 -->
    <div v-show="activeSubTab === 'ai'" class="mobile-write-body mobile-write-cockpit">
      <AutopilotCockpit
        v-if="cockpitMounted"
        :novel-id="slug"
        @desk-refresh="emit('chapter-updated')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/** 移动端写作 Tab — 编辑器 + 顶部二级页签（全部可用）
 *
 * 作者: Axelton
 */
import { ref, computed, watch, defineAsyncComponent, onMounted } from 'vue'
import { NInput, NTag, NButton, NSpace, NSpin, useMessage } from 'naive-ui'
import { chapterApi, type ChapterMicroBeatPayload, type ChapterStructureDTO, type ChapterReviewDTO } from '@/api/chapter'
import { autopilotApi, type AutopilotStatus, type AutopilotCircuitBreakerData } from '@/api/autopilot'
import type { GuardrailCheckResponse } from '@/api/engineCore'

/** 移动端延迟挂载驾驶舱，避免首屏加载大组件 */
const AutopilotCockpit = defineAsyncComponent(() => import('@/components/autopilot/AutopilotPanel.vue'))

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
}>()

const message = useMessage()

/** 延迟挂载驾驶舱：首屏先渲染轻量 UI，等 MobileWrite 挂载后再加载重量级 cockpit */
const cockpitMounted = ref(false)
onMounted(() => {
  // 下一帧再挂载，避免首屏闪烁
  requestAnimationFrame(() => { cockpitMounted.value = true })
})

// ── 页签 ──
const subTabs = [
  { key: 'manuscript' as const, label: '正文' },
  { key: 'elements' as const, label: '元素' },
  { key: 'status' as const, label: '状态' },
  { key: 'quality' as const, label: '质量' },
  { key: 'trace' as const, label: '追踪' },
  { key: 'ai' as const, label: 'AI托管' },
]
type SubTab = (typeof subTabs)[number]['key']
const activeSubTab = ref<SubTab>('manuscript')

const currentChapter = computed(() => {
  if (!props.currentChapterId) return null
  return props.chapters.find(ch => ch.id === props.currentChapterId) || null
})

// ── 正文 ──
const saving = ref(false)
const editorContent = ref('')
const aiGenerating = ref(false)

watch(() => props.chapterContent, (v) => { editorContent.value = v }, { immediate: true })

async function handleSave() {
  if (!currentChapter.value) return
  saving.value = true
  try {
    await chapterApi.updateChapter(props.slug, currentChapter.value.number, { content: editorContent.value })
    message.success('保存成功')
    emit('chapter-updated')
  } catch { message.error('保存失败') } finally { saving.value = false }
}

async function handleAiGenerate() {
  if (!currentChapter.value) return
  aiGenerating.value = true
  try {
    await autopilotApi.start(props.slug, { max_auto_chapters: 1, target_chapters: currentChapter.value.number, target_words_per_chapter: 2500 })
    message.success('AI 生成已启动，请稍候刷新查看')
  } catch { message.error('AI 生成启动失败') } finally { aiGenerating.value = false }
}

// ── 元素 ──
const elementsLoading = ref(false)
const structure = ref<ChapterStructureDTO | null>(null)
const microBeats = ref<ChapterMicroBeatPayload[]>([])

async function loadElements() {
  if (!currentChapter.value) return
  elementsLoading.value = true
  try {
    const [s, ch] = await Promise.all([
      chapterApi.getChapterStructure(props.slug, currentChapter.value.number),
      chapterApi.getChapter(props.slug, currentChapter.value.number),
    ])
    structure.value = s
    // micro_beats 可能包含在 chapter 响应中
    microBeats.value = (ch as any).micro_beats ?? []
  } catch { /* 静默处理 */ } finally { elementsLoading.value = false }
}

// ── 状态 ──
const reviewLoading = ref(false)
const reviewStatus = ref('未审阅')
const reviewMemo = ref('')
const reviewUpdated = ref('')
const aiReviewing = ref(false)

const reviewStatusType = computed(() => {
  const s = reviewStatus.value
  if (s === 'approved' || s === '通过') return 'success'
  if (s === 'rejected' || s === '驳回') return 'error'
  return 'default'
})

async function loadReview() {
  if (!currentChapter.value) return
  reviewLoading.value = true
  try {
    const r = await chapterApi.getChapterReview(props.slug, currentChapter.value.number)
    reviewStatus.value = r.status || '未审阅'
    reviewMemo.value = r.memo || ''
    reviewUpdated.value = r.updated_at || r.created_at || ''
  } catch { /* 静默处理 */ } finally { reviewLoading.value = false }
}

async function handleAiReview() {
  if (!currentChapter.value) return
  aiReviewing.value = true
  try {
    const r = await chapterApi.reviewChapterAi(props.slug, currentChapter.value.number, true)
    reviewStatus.value = r.status || '已审阅'
    reviewMemo.value = r.memo || ''
    message.success('AI 审阅完成')
  } catch { message.error('AI 审阅失败') } finally { aiReviewing.value = false }
}

// ── 质量 ──
const guardrailLoading = ref(false)
const guardrail = ref<GuardrailCheckResponse | null>(null)

async function loadGuardrail() {
  if (!currentChapter.value) return
  guardrailLoading.value = true
  try {
    guardrail.value = await chapterApi.getGuardrailSnapshot(props.slug, currentChapter.value.number)
  } catch { /* 静默处理 */ } finally { guardrailLoading.value = false }
}

function fmtScore(s: number): string {
  return Math.round(s * 100) + '分'
}

// ── 追踪 / AI托管 ──
const autopilotLoading = ref(false)
const apRunning = ref(false)
const apStage = ref('')
const apStep = ref('')
const apEpoch = ref<number | null>(null)
const circuitBreaker = ref<AutopilotCircuitBreakerData | null>(null)

const cbStatusType = computed(() => {
  const s = circuitBreaker.value?.status
  if (s === 'open') return 'error'
  if (s === 'half_open') return 'warning'
  return 'success'
})
const cbStatusLabel = computed(() => {
  const s = circuitBreaker.value?.status
  if (s === 'open') return '已断开'
  if (s === 'half_open') return '半开'
  return '正常'
})

async function loadAutopilot() {
  autopilotLoading.value = true
  try {
    const [status, cb] = await Promise.all([
      autopilotApi.getStatus(props.slug).catch(() => null),
      autopilotApi.getCircuitBreaker(props.slug).catch(() => null),
    ])
    if (status) {
      const s = status as AutopilotStatus
      apRunning.value = s.autopilot_run_epoch != null && s.last_stable_stage !== 'idle' && s.last_stable_stage !== 'completed'
      apStage.value = (s.active_pipeline_step || s.last_stable_stage || '') as string
      apStep.value = s.active_pipeline_step as string || ''
      apEpoch.value = typeof s.autopilot_run_epoch === 'number' ? s.autopilot_run_epoch : null
    }
    if (cb) circuitBreaker.value = cb
  } catch { /* 静默处理 */ } finally { autopilotLoading.value = false }
}

// ── Tab 切换时自动加载数据 ──
function switchTab(key: SubTab) {
  activeSubTab.value = key
  if (!currentChapter.value) return
  switch (key) {
    case 'elements': loadElements(); break
    case 'status': loadReview(); break
    case 'quality': loadGuardrail(); break
    case 'trace': case 'ai': loadAutopilot(); break
  }
}

// 帮助函数
function fmtRatio(r: number | undefined): string {
  if (r == null) return '-'
  return Math.round(r * 100) + '%'
}
</script>

<style scoped>
.mobile-write {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.mobile-write-subtabs {
  display: flex;
  border-bottom: 1px solid var(--app-border, #e2e8f0);
  background: var(--app-surface, #fff);
  overflow-x: auto;
  scrollbar-width: none;
  flex-shrink: 0;
}
.mobile-write-subtabs::-webkit-scrollbar { display: none; }

.mobile-write-subtab {
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  color: var(--app-text-muted, #94a3b8);
  white-space: nowrap;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
  -webkit-tap-highlight-color: transparent;
  user-select: none;
}
.mobile-write-subtab.active { color: #4f46e5; border-bottom-color: #4f46e5; }

.mobile-write-body {
  flex: 1; min-height: 0; overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: 12px;
}

.mobile-write-empty, .mobile-write-loading {
  display: flex; align-items: center; justify-content: center;
  height: 100%; color: var(--app-text-muted);
}

/* ── 正文 ── */
.mobile-write-editor-head {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;
}
.mobile-write-chapter-label {
  font-size: 14px; font-weight: 700; overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; flex: 1; min-width: 0; margin-right: 8px;
}
.mobile-write-textarea { min-height: 320px; }
.mobile-write-textarea :deep(textarea) { font-size: 15px; line-height: 1.7; min-height: 320px !important; }
.mobile-write-actions { padding-top: 12px; }

/* ── 信息卡片（元素/状态/质量/追踪/AI 共用）── */
.mobile-write-info-cards {
  display: flex; flex-direction: column; gap: 10px;
}
.mw-info-card {
  background: var(--app-surface, #fff); border-radius: 10px;
  padding: 14px; border: 1px solid var(--app-border, #e2e8f0);
}
.mw-card-title { font-size: 14px; font-weight: 700; margin-bottom: 10px; }
.mw-card-subtitle { font-size: 13px; font-weight: 600; margin: 10px 0 6px; color: var(--app-text-secondary); }
.mw-card-label { font-size: 12px; color: var(--app-text-muted); flex-shrink: 0; }
.mw-card-val { font-size: 13px; color: var(--app-text-primary); }
.mw-card-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.mw-card-empty { font-size: 12px; color: var(--app-text-muted); margin: 0; }
.mw-card-actions { margin-top: 10px; }
.mw-card-section { margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--app-border); }

/* 统计数据网格 */
.mw-card-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 8px;
}
.mw-stat {
  text-align: center; padding: 8px; background: var(--app-surface-subtle, #f8fafc);
  border-radius: 8px; display: flex; flex-direction: column; gap: 2px;
}
.mw-stat-val { font-size: 18px; font-weight: 700; color: #4f46e5; }
.mw-stat-lbl { font-size: 11px; color: var(--app-text-muted); }

/* 微节拍 */
.mw-beat-item {
  padding: 8px 0; border-bottom: 1px solid var(--app-border, rgba(0,0,0,.04));
}
.mw-beat-item:last-child { border-bottom: none; }
.mw-beat-hd { display: flex; gap: 6px; margin-bottom: 4px; }
.mw-beat-idx { font-size: 11px; font-weight: 700; color: #4f46e5; flex-shrink: 0; }
.mw-beat-desc { font-size: 13px; line-height: 1.45; }
.mw-beat-tags { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 2px; padding-left: 22px; }
.mw-beat-meta { font-size: 11px; color: var(--app-text-muted); padding-left: 22px; }
.mw-memo { font-size: 13px; line-height: 1.5; margin: 4px 0 0; color: var(--app-text-secondary); white-space: pre-wrap; }

/* 质量护栏 */
.mw-gr-score {
  display: flex; align-items: baseline; gap: 8px; margin-bottom: 12px;
}
.mw-gr-num { font-size: 28px; font-weight: 800; }
.mw-gr-score.pass .mw-gr-num { color: #10b981; }
.mw-gr-score.warn .mw-gr-num { color: #f59e0b; }
.mw-gr-label { font-size: 13px; color: var(--app-text-muted); }

.mw-gr-dims { display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px; }
.mw-gr-dim { display: flex; align-items: center; gap: 8px; }
.mw-gr-dim-name { font-size: 11px; width: 40px; flex-shrink: 0; color: var(--app-text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mw-gr-dim-bar-bg { flex: 1; height: 6px; background: var(--app-surface-subtle); border-radius: 3px; overflow: hidden; }
.mw-gr-dim-bar { height: 100%; border-radius: 3px; transition: width 0.3s; }
.mw-gr-dim-bar.good { background: #10b981; }
.mw-gr-dim-bar.mid { background: #f59e0b; }
.mw-gr-dim-bar.bad { background: #ef4444; }
.mw-gr-dim-score { font-size: 11px; width: 32px; text-align: right; color: var(--app-text-muted); }

.mw-violations { }
.mw-violation { display: flex; align-items: flex-start; gap: 6px; margin-bottom: 6px; padding: 6px; background: #fff7ed; border-radius: 6px; }
.mw-v-desc { font-size: 12px; line-height: 1.4; flex: 1; }

.mw-cb-error {
  font-size: 11px; color: #ef4444; background: #fef2f2; padding: 6px 8px;
  border-radius: 6px; margin-top: 6px; line-height: 1.4;
}

/* ── AI 托管驾驶舱移动端适配 ── */
.mobile-write-cockpit {
  padding: 8px;
}

/* 驾驶舱卡片内边距缩减 */
.mobile-write-cockpit :deep(.autopilot-panel) {
  padding: 10px 12px 10px;
  gap: 10px;
  border-radius: 10px;
}

/* Hero 区域 */
.mobile-write-cockpit :deep(.ap-hero) {
  padding: 10px 12px;
  gap: 8px;
}

.mobile-write-cockpit :deep(.ap-hero__pct-value) {
  font-size: 22px;
}

/* KPI 网格：移动端强制 2 列 */
.mobile-write-cockpit :deep(.ap-kpi-grid) {
  grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  gap: 8px;
}

.mobile-write-cockpit :deep(.ap-kpi) {
  padding: 8px 10px 8px;
  gap: 4px;
}

.mobile-write-cockpit :deep(.ap-kpi__label) {
  font-size: 9px;
}

.mobile-write-cockpit :deep(.ap-kpi__value) {
  font-size: 13px;
}

/* 实时管线 */
.mobile-write-cockpit :deep(.ap-telemetry) {
  padding: 10px 12px;
}

.mobile-write-cockpit :deep(.ap-telemetry__grid) {
  grid-template-columns: 1fr;
}

/* 操作按钮区 */
.mobile-write-cockpit :deep(.n-space) {
  flex-wrap: wrap;
}

/* 启动弹窗适配 */
.mobile-write-cockpit :deep(.n-modal) {
  max-width: 92vw;
}

/* 审阅警告内按钮换行 */
.mobile-write-cockpit :deep(.ap-review-alert) {
  flex-direction: column;
  align-items: flex-start;
}

/* 叙事描述 */
.mobile-write-cockpit :deep(.ap-narrative) {
  padding: 10px 12px;
}

.mobile-write-cockpit :deep(.ap-narrative__body) {
  font-size: 11px;
}

/* 阶段标签 */
.mobile-write-cockpit :deep(.ap-stage-tag) {
  font-size: 10px;
  padding: 3px 8px;
}

/* 内联警告 */
.mobile-write-cockpit :deep(.ap-inline-alert) {
  font-size: 11px;
}
</style>
