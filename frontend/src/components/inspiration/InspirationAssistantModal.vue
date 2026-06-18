<!-- 灵感助手多轮对话弹窗 — 作者：Axelton -->
<template>
  <n-modal
    v-model:show="visible"
    preset="card"
    :style="{ width: '96vw', maxWidth: '1200px', height: '90vh', marginTop: '4vh' }"
    :bordered="true"
    :segmented="{ content: true, footer: 'soft' }"
    :mask-closable="true"
    :close-on-esc="true"
    @update:show="handleClose"
  >
    <template #header>
      <div class="assist-header">
        <span class="assist-header-title">灵感助手</span>
        <div class="assist-header-right">
          <!-- 会话选择器 — 始终显示 -->
          <n-select
            :value="sessionId"
            :options="sessionSelectOptions"
            size="small"
            :style="{ width: '200px' }"
            :placeholder="sessionList.length === 0 ? '暂无历史会话' : '选择历史会话…'"
            :disabled="sessionList.length === 0"
            @update:value="handleSessionSelect"
          />
          <n-select
            v-model:value="currentStrategy"
            :options="strategyOptions"
            size="small"
            :style="{ width: '130px' }"
            :disabled="isSessionActive"
          />
          <n-button
            v-if="sessionId"
            size="tiny"
            quaternary
            type="warning"
            @click="startNewSession"
          >
            新会话
          </n-button>
        </div>
      </div>
    </template>

    <div class="assist-body">
      <!-- 对话区 -->
      <div class="assist-chat" ref="chatContainerRef">
        <!-- 工具调用状态条 -->
        <Transition name="slide-fade">
          <div v-if="toolStatus.show" class="tool-status-bar" :class="`tool-status-${toolStatus.type}`">
            <span class="tool-status-icon">{{ toolStatus.type === 'info' ? '🔍' : '✅' }}</span>
            <span class="tool-status-text">{{ toolStatus.text }}</span>
          </div>
        </Transition>

        <div
          v-for="msg in messages"
          :key="msg.id"
          class="chat-message"
          :class="`chat-${msg.role}`"
        >
          <div class="chat-avatar">
            {{ msg.role === 'user' ? '😀' : (msg as LocalMessage).messageType === 'question' ? '🤔' : '💡' }}
          </div>
          <div
            class="chat-bubble"
            :class="msg.role === 'assistant' && (msg as LocalMessage).messageType === 'question' ? 'bubble-question' : 'bubble-suggestion'"
            v-html="renderMarkdown(msg.content)"
          />
        </div>
        <!-- 流式输出中的气泡 -->
        <div v-if="streamingContent" class="chat-message chat-assistant">
          <div class="chat-avatar">🤖</div>
          <div class="chat-bubble chat-streaming">{{ streamingContent }}</div>
        </div>

        <!-- Agent 思考中指示器 -->
        <Transition name="slide-fade">
          <div v-if="thinking" class="thinking-indicator">
            <span class="thinking-dot" />
            <span class="thinking-dot" />
            <span class="thinking-dot" />
            <span class="thinking-text">{{ streamingContent ? '正在生成回复…' : '正在思考…' }}</span>
          </div>
        </Transition>

        <!-- 空状态引导 -->
        <div v-if="messages.length === 0 && !streamingContent" class="chat-empty">
          <p class="chat-empty-title">告诉我你的想法，或让灵感助手帮你找到方向</p>
          <p class="chat-empty-hint">{{ strategyHint }}</p>
        </div>
      </div>

      <!-- 侧栏：字段预览 -->
      <div class="assist-sidebar" :class="{ 'sidebar-expanded': sidebarExpanded }">
        <div class="sidebar-header">
          <span class="sidebar-title">字段预览</span>
          <button class="sidebar-toggle" @click="sidebarExpanded = !sidebarExpanded" :title="sidebarExpanded ? '收起侧栏' : '展开侧栏'">
            <svg viewBox="0 0 24 24" width="14" height="14" :style="sidebarExpanded ? { transform: 'rotate(180deg)' } : {}">
              <path fill="currentColor" d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/>
            </svg>
          </button>
        </div>

        <!-- 中间滚动区 -->
        <div class="sidebar-scroll">
          <!-- 提取中 shimmer 骨架屏 -->
          <div v-if="autoExtracting" class="field-list field-shimmer">
            <div v-for="w in shimmerWidths" :key="w" class="shimmer-item">
              <span class="shimmer-label" />
              <span class="shimmer-value" :style="{ width: w + '%' }" />
            </div>
          </div>

          <!-- 正常字段列表 -->
          <div v-else class="field-list">
            <div class="field-item">
              <span class="field-label">书名</span>
              <span class="field-value" :class="{ empty: !fieldData.title }">
                {{ fieldData.title || '—' }}
              </span>
            </div>
            <div class="field-item">
              <span class="field-label">简介</span>
              <span class="field-value premise" :class="{ empty: !fieldData.premise }">
                {{ fieldData.premise || '—' }}
              </span>
            </div>
            <div class="field-item">
              <span class="field-label">大类</span>
              <span class="field-value" :class="{ empty: !fieldData.genre }">
                {{ fieldData.genre || '—' }}
              </span>
            </div>
            <div class="field-item">
              <span class="field-label">网文主题</span>
              <span class="field-value" :class="{ empty: !fieldData.sub_genre }">
                {{ fieldData.sub_genre || '—' }}
              </span>
            </div>
            <div class="field-item">
              <span class="field-label">世界观基调</span>
              <span class="field-value" :class="{ empty: !fieldData.world_preset }">
                {{ fieldData.world_preset || '—' }}
              </span>
            </div>
            <div class="field-item">
              <span class="field-label">剧情结构</span>
              <span class="field-value" :class="{ empty: !fieldData.story_structure }">
                {{ fieldData.story_structure || '—' }}
              </span>
            </div>
            <div class="field-item">
              <span class="field-label">节奏把控</span>
              <span class="field-value" :class="{ empty: !fieldData.pacing_control }">
                {{ fieldData.pacing_control || '—' }}
              </span>
            </div>
            <div class="field-item">
              <span class="field-label">写作风格</span>
              <span class="field-value" :class="{ empty: !fieldData.writing_style }">
                {{ fieldData.writing_style || '—' }}
              </span>
            </div>
            <div class="field-item">
              <span class="field-label">特殊要求</span>
              <span class="field-value" :class="{ empty: !fieldData.special_requirements }">
                {{ fieldData.special_requirements || '—' }}
              </span>
            </div>
          </div>

          <!-- 提取中指示器 -->
          <div v-if="autoExtracting" class="extracting-indicator">
            <span class="extracting-dot" />
            <span class="extracting-dot" />
            <span class="extracting-dot" />
            <span>提取中…</span>
          </div>
        </div>

        <!-- 底部固定按钮区 -->
        <div class="sidebar-footer">
          <n-button
            type="primary"
            block
            :disabled="!hasFields"
            @click="handleFillForm"
          >
            填充到表单
          </n-button>
          <n-button
            v-if="hasFields && !autoExtracting"
            size="small"
            quaternary
            block
            @click="autoGenerateFields()"
            style="margin-top: 6px"
          >
            重新提取
          </n-button>
        </div>
      </div>
    </div>

    <!-- 底部输入区 -->
    <template #footer>
      <div class="assist-footer">
        <n-input
          v-model:value="inputMessage"
          placeholder="说说你的想法…"
          :disabled="sending"
          @keydown.enter="handleSend"
          clearable
          round
          size="large"
        />
        <n-button
          type="primary"
          circle
          :loading="sending"
          :disabled="!inputMessage.trim()"
          @click="handleSend"
        >
          <template #icon>
            <n-icon>
              <svg viewBox="0 0 24 24" width="18" height="18">
                <path fill="currentColor" d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            </n-icon>
          </template>
        </n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, nextTick } from 'vue'
import { NModal, NSelect, NInput, NButton, NIcon, useMessage } from 'naive-ui'
import { subscribeAssist, fetchSessions, type AssistFieldData, type AssistMessage, type AssistSessionListItem } from '@/api/assist'
import { marked } from 'marked'

/** 扩展本地消息类型，追加 messageType 字段用于区分追问/建议气泡 */
interface LocalMessage extends AssistMessage {
  messageType?: 'question' | 'suggestion'
}

const emit = defineEmits<{
  (e: 'fill-fields', fields: AssistFieldData): void
}>()

const props = defineProps<{
  show: boolean
  novelId: string
}>()

const message = useMessage()

const visible = computed({
  get: () => props.show,
  set: (val: boolean) => {
    if (!val) emit('fill-fields', {} as AssistFieldData) // 关闭信号通过空值
  },
})

const currentStrategy = ref('brainstorm')
const isSessionActive = ref(false)
const sessionId = ref<string | null>(null)
const messages = ref<LocalMessage[]>([])
const inputMessage = ref('')
const sending = ref(false)
const streamingContent = ref('')
const thinking = ref(false)  // Agent 多轮思考中
const fieldData = ref<AssistFieldData>({} as AssistFieldData)
const autoExtracting = ref(false)
const sidebarExpanded = ref(false)
const chatContainerRef = ref<HTMLElement | null>(null)

/** shimmer 骨架屏的随机宽度 — 依赖 autoExtracting 以在每次提取时重新生成 */
const shimmerWidths = computed(() => {
  void autoExtracting.value  // 触发重新计算
  return Array.from({ length: 9 }, () => 55 + Math.floor(Math.random() * 40))
})

// 工具调用状态条
const toolStatus = reactive({
  show: false,
  text: '',
  type: 'info' as 'info' | 'success',
})

let toolTimer: ReturnType<typeof setTimeout> | null = null

/** 显示工具调用状态 — 查找中 */
function showToolCall(_name: string, args: Record<string, unknown>) {
  if (toolTimer) clearTimeout(toolTimer)
  const keyword = (args.genre_keyword as string) || ''
  toolStatus.show = true
  toolStatus.text = keyword ? `正在查找「${keyword}」类型写作模板…` : `正在查找灵感素材…`
  toolStatus.type = 'info'
}

/** 显示工具结果状态 — 完成后 1.5s 自动收起 */
function showToolResult(_name: string, _summary: string) {
  if (toolTimer) clearTimeout(toolTimer)
  toolStatus.text = `已参考类型模板`
  toolStatus.type = 'success'
  toolTimer = setTimeout(() => {
    toolStatus.show = false
  }, 1500)
}

/** 会话历史列表 */
const sessionList = ref<AssistSessionListItem[]>([])
const loadingSessions = ref(false)

/** 会话选择器选项（n-select 格式） */
const sessionSelectOptions = computed(() =>
  sessionList.value.map((s) => {
    const strategyLabel = strategyOptions.find(o => o.value === s.strategy)?.label || s.strategy
    const title = s.field_data?.title || '未命名'
    const isActive = s.session_id === sessionId.value
    return {
      value: s.session_id,
      label: `${title} · ${strategyLabel}${isActive ? ' ✓' : ''}`,
    }
  })
)

/** 加载会话列表 */
async function loadSessions() {
  if (!props.novelId) return
  loadingSessions.value = true
  try {
    sessionList.value = await fetchSessions(props.novelId)
    console.log('[灵感助手] 会话列表加载完成:', sessionList.value.length, '条', sessionList.value)
  } catch (err) {
    console.error('[灵感助手] 会话列表加载失败:', err)
  } finally {
    loadingSessions.value = false
  }
}

/** 自动恢复最近的 completed 会话（或 active 会话） */
async function autoResumeLatest() {
  if (sessionList.value.length === 0) return
  // 优先恢复最近完成的会话，其次最近的活跃会话
  const latest = sessionList.value.find(s => s.status === 'completed') || sessionList.value[0]
  if (!latest) return
  await switchToSession(latest.session_id)
}

/** 切换到指定会话 */
function switchToSession(targetSessionId: string) {
  return new Promise<void>((resolve) => {
    subscribeAssist(
      {
        novel_id: props.novelId,
        session_id: targetSessionId,
        action: 'resume',
      },
      {
        onResumeDone(data) {
          sessionId.value = data.session_id
          currentStrategy.value = data.strategy
          isSessionActive.value = true
          messages.value = data.messages.map((m) => ({
            ...m,
            messageType: undefined,
          }))
          // 从会话列表中加载 field_data
          const sess = sessionList.value.find(s => s.session_id === targetSessionId)
          if (sess?.field_data) {
            fieldData.value = sess.field_data as AssistFieldData
          } else {
            fieldData.value = {} as AssistFieldData
          }
          scrollToBottom()
          resolve()
        },
        onError(_err) {
          resolve()
        },
      },
    )
  })
}

/** 切换会话 */
async function handleSessionSelect(value: string) {
  if (!value || value === sessionId.value) return
  await switchToSession(value)
}

/** 开始新会话 */
function startNewSession() {
  sessionId.value = null
  isSessionActive.value = false
  messages.value = []
  fieldData.value = {} as AssistFieldData
  streamingContent.value = ''
  currentStrategy.value = 'brainstorm'
}

const strategyOptions = [
  { label: '脑洞爆破', value: 'brainstorm' },
  { label: '世界观优先', value: 'world_first' },
  { label: '角色驱动', value: 'character_driven' },
  { label: '主题先行', value: 'theme_first' },
]

const strategyHints: Record<string, string> = {
  brainstorm: '随便聊聊吧！你最近对什么故事感兴趣？看过什么让你印象深刻的作品？',
  world_first: '如果有一个世界，它的规则和我们的完全不同，你最想改变什么？',
  character_driven: '你心中有没有一个模糊的人物形象？他/她最大的愿望是什么？',
  theme_first: '有没有一个主题或议题你一直想探讨？比如自由、复仇、成长…',
}

const strategyHint = computed(() => strategyHints[currentStrategy.value] || '')

const hasFields = computed(() => {
  const fd = fieldData.value
  return !!(fd.title || fd.genre || fd.premise)
})

function scrollToBottom() {
  nextTick(() => {
    const el = chatContainerRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

/** 将 markdown 文本渲染为 HTML */
function renderMarkdown(text: string): string {
  if (!text) return ''
  return marked.parse(text, { breaks: true }) as string
}

async function handleSend() {
  const text = inputMessage.value.trim()
  if (!text || sending.value || autoExtracting.value) return

  inputMessage.value = ''
  sending.value = true
  streamingContent.value = ''
  thinking.value = true  // Agent 思考开始

  // 添加用户消息到本地列表
  const userMsg: AssistMessage = {
    id: `local_${Date.now()}`,
    role: 'user',
    content: text,
    created_at: new Date().toISOString(),
  }
  messages.value.push(userMsg)
  scrollToBottom()

  // 发起 SSE
  subscribeAssist(
    {
      novel_id: props.novelId,
      session_id: sessionId.value || undefined,
      strategy: isSessionActive.value ? undefined : currentStrategy.value,
      action: 'chat',
      message: text,
    },
    {
      onSessionCreated(info) {
        sessionId.value = info.session_id
        isSessionActive.value = true
        // 手动将会话插入列表顶部，避免 PersistenceQueue 异步写入导致尚未查到
        sessionList.value.unshift({
          session_id: info.session_id,
          strategy: currentStrategy.value,
          status: 'active',
          field_data: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })
      },
      onChatChunk(content) {
        streamingContent.value += content
        scrollToBottom()
      },
      onChatDone(messageType) {
        // 将流式内容转为正式消息，携带 messageType 用于气泡区分
        if (streamingContent.value) {
          messages.value.push({
            id: `ai_${Date.now()}`,
            role: 'assistant',
            content: streamingContent.value,
            messageType: messageType || 'suggestion',
            created_at: new Date().toISOString(),
          })
        }
        streamingContent.value = ''
        sending.value = false
        thinking.value = false  // Agent 思考结束
        // 每次 AI 回复后自动提取字段
        autoGenerateFields()
      },
      onToolCall(name, args) {
        showToolCall(name, args)
      },
      onToolResult(name, summary) {
        showToolResult(name, summary)
      },
      onError(err) {
        message.error(err)
        sending.value = false
        streamingContent.value = ''
        thinking.value = false
      },
    },
  )
}

/** 每次 AI 回复后自动提取字段（静默模式，不阻塞 UI） */
function autoGenerateFields() {
  if (!sessionId.value) return
  autoExtracting.value = true

  subscribeAssist(
    {
      novel_id: props.novelId,
      session_id: sessionId.value,
      action: 'generate_fields',
    },
    {
      onFieldsDone(fields) {
        fieldData.value = fields
        autoExtracting.value = false
        // 更新会话列表中的 field_data 和状态
        const idx = sessionList.value.findIndex(s => s.session_id === sessionId.value)
        if (idx !== -1) {
          sessionList.value[idx] = {
            ...sessionList.value[idx],
            status: 'completed',
            field_data: fields,
          }
        }
      },
      onError(_err) {
        // 静默失败
        autoExtracting.value = false
      },
    },
  )
}

function handleFillForm() {
  emit('fill-fields', fieldData.value)
  message.success('已填充到表单')
}

function handleClose(_show: boolean) {
  // 会话已持久化到后端，关闭弹窗不做额外操作
}

/** 弹窗打开时自动加载会话列表并恢复最近会话 */
watch(() => props.show, async (now) => {
  if (!now) return
  await loadSessions()
  if (sessionList.value.length > 0 && !sessionId.value) {
    await autoResumeLatest()
  }
}, { immediate: true })
</script>

<style scoped>
.assist-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.assist-header-title {
  font-size: 17px;
  font-weight: 700;
  flex-shrink: 0;
}

.assist-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.assist-body {
  display: flex;
  gap: 16px;
  height: calc(90vh - 160px);
  min-height: 420px;
}

.assist-chat {
  flex: 1;
  overflow-y: auto;
  padding-right: 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-message {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.chat-user {
  flex-direction: row-reverse;
}

.chat-avatar {
  font-size: 24px;
  flex-shrink: 0;
  width: 32px;
  text-align: center;
}

.chat-bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  background: var(--app-surface-subtle);
  color: var(--app-text-primary);
}

/** markdown 渲染内容样式 */
.chat-bubble :deep(p) {
  margin: 0 0 6px;
}
.chat-bubble :deep(p:last-child) {
  margin-bottom: 0;
}
.chat-bubble :deep(ul),
.chat-bubble :deep(ol) {
  margin: 4px 0;
  padding-left: 20px;
}
.chat-bubble :deep(li) {
  margin: 2px 0;
}
.chat-bubble :deep(code) {
  background: rgba(127, 127, 127, 0.15);
  padding: 2px 5px;
  border-radius: 3px;
  font-size: 13px;
  font-family: 'SF Mono', 'Menlo', monospace;
}
.chat-bubble :deep(pre) {
  background: rgba(127, 127, 127, 0.1);
  padding: 8px 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 6px 0;
}
.chat-bubble :deep(pre code) {
  background: none;
  padding: 0;
}
.chat-bubble :deep(strong) {
  font-weight: 600;
}
.chat-bubble :deep(em) {
  font-style: italic;
}
.chat-bubble :deep(blockquote) {
  border-left: 3px solid var(--app-border);
  margin: 6px 0;
  padding-left: 10px;
  color: var(--app-text-muted);
}
.chat-bubble :deep(h1),
.chat-bubble :deep(h2),
.chat-bubble :deep(h3),
.chat-bubble :deep(h4) {
  margin: 8px 0 4px;
  font-weight: 600;
  line-height: 1.3;
}
.chat-bubble :deep(h1) { font-size: 1.3em; }
.chat-bubble :deep(h2) { font-size: 1.15em; }
.chat-bubble :deep(h3) { font-size: 1.05em; }
.chat-bubble :deep(hr) {
  border: none;
  border-top: 1px solid var(--app-border);
  margin: 8px 0;
}

.chat-user .chat-bubble {
  background: var(--color-brand, #4f46e5);
  color: #fff;
}

.chat-streaming {
  border: 1px dashed var(--color-brand-border, rgba(79, 70, 229, 0.3));
}

.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  gap: 8px;
  color: var(--app-text-muted);
}

.chat-empty-title {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
}

.chat-empty-hint {
  font-size: 13px;
  max-width: 320px;
  margin: 0;
}

.assist-sidebar {
  width: 220px;
  flex-shrink: 0;
  border-left: 1px solid var(--app-border);
  padding-left: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width 0.3s ease;
}

.assist-sidebar.sidebar-expanded {
  width: 50%;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.sidebar-scroll {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.sidebar-footer {
  flex-shrink: 0;
  padding-top: 12px;
  border-top: 1px solid var(--app-border);
  margin-top: 8px;
}

.sidebar-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.sidebar-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: 1px solid var(--app-border);
  border-radius: 4px;
  background: var(--app-surface-subtle);
  color: var(--app-text-muted);
  cursor: pointer;
  padding: 0;
  transition: background 0.2s;
}
.sidebar-toggle:hover {
  background: var(--app-surface-hover);
  color: var(--app-text-primary);
}
.sidebar-toggle svg {
  transition: transform 0.3s;
}

.field-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.field-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.field-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--app-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.field-value {
  font-size: 13px;
  color: var(--app-text-primary);
  word-break: break-all;
}

.field-value.empty {
  color: var(--app-text-muted);
  font-style: italic;
}

.field-value.premise {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.assist-footer {
  display: flex;
  align-items: center;
  gap: 10px;
}

.assist-footer :deep(.n-input) {
  flex: 1;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .assist-body {
    flex-direction: column;
    height: calc(90vh - 140px);
  }

  .assist-sidebar {
    width: 100%;
    border-left: none;
    border-top: 1px solid var(--app-border);
    padding-left: 0;
    padding-top: 12px;
    flex-shrink: 0;
  }

  .field-list {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
}

/* 追问气泡 — 琥珀/浅黄底，左侧高亮边框 */
.bubble-question {
  background: rgba(245, 158, 11, 0.08) !important;
  border-left: 3px solid #f59e0b;
}

/* 建议气泡 — 继承默认灰底样式 */
.bubble-suggestion {
  /* 继承 chat-bubble 默认样式 */
}

/* 工具调用状态条 */
.tool-status-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
  margin-bottom: 4px;
}
.tool-status-info {
  background: rgba(59, 130, 246, 0.08);
  color: var(--app-text-secondary);
}
.tool-status-success {
  background: rgba(34, 197, 94, 0.08);
  color: var(--app-text-secondary);
}
.tool-status-icon {
  flex-shrink: 0;
}

/* 滑入/滑出动画 */
.slide-fade-enter-active {
  transition: all 0.3s ease;
}
.slide-fade-leave-active {
  transition: all 0.3s ease;
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateY(-10px);
  opacity: 0;
}

/* ── Shimmer 骨架屏（提取中动画） ── */
@keyframes shimmer {
  0%   { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.field-shimmer {
  gap: 14px;
}

.shimmer-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.shimmer-label,
.shimmer-value {
  border-radius: 4px;
  background: linear-gradient(
    90deg,
    var(--app-surface-subtle) 25%,
    var(--app-surface-hover) 37%,
    var(--app-surface-subtle) 63%
  );
  background-size: 200% 100%;
  animation: shimmer 1.4s ease-in-out infinite;
}

.shimmer-label {
  height: 10px;
  width: 40%;
}

.shimmer-value {
  height: 14px;
}

/* ── 提取中指示器 ── */
.extracting-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--app-text-muted);
}

.extracting-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-brand, #4f46e5);
  animation: dotPulse 1.2s ease-in-out infinite;
}
.extracting-dot:nth-child(2) { animation-delay: 0.2s; }
.extracting-dot:nth-child(3) { animation-delay: 0.4s; }

/* ── Agent 思考中指示器 ── */
.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: 13px;
  color: var(--app-text-muted);
}

.thinking-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-brand, #4f46e5);
  animation: dotPulse 1.2s ease-in-out infinite;
}
.thinking-dot:nth-child(2) { animation-delay: 0.2s; }
.thinking-dot:nth-child(3) { animation-delay: 0.4s; }

.thinking-text {
  font-size: 13px;
  color: var(--app-text-muted);
}

@keyframes dotPulse {
  0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.2); }
}
</style>
