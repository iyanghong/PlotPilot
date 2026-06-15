<!-- 灵感助手多轮对话弹窗 — 作者：Axelton -->
<template>
  <n-modal
    v-model:show="visible"
    preset="card"
    :style="{ width: '92vw', maxWidth: '960px', height: '80vh', marginTop: '8vh' }"
    :bordered="true"
    :segmented="{ content: true, footer: 'soft' }"
    :mask-closable="true"
    :close-on-esc="true"
    @update:show="handleClose"
  >
    <template #header>
      <div class="assist-header">
        <span class="assist-header-title">灵感助手</span>
        <n-select
          v-model:value="currentStrategy"
          :options="strategyOptions"
          size="small"
          :style="{ width: '160px' }"
          :disabled="isSessionActive"
        />
      </div>
    </template>

    <div class="assist-body">
      <!-- 对话区 -->
      <div class="assist-chat" ref="chatContainerRef">
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="chat-message"
          :class="`chat-${msg.role}`"
        >
          <div class="chat-avatar">
            {{ msg.role === 'user' ? '😀' : '🤖' }}
          </div>
          <div class="chat-bubble">
            {{ msg.content }}
          </div>
        </div>
        <!-- 流式输出中的气泡 -->
        <div v-if="streamingContent" class="chat-message chat-assistant">
          <div class="chat-avatar">🤖</div>
          <div class="chat-bubble chat-streaming">{{ streamingContent }}</div>
        </div>
        <!-- 空状态引导 -->
        <div v-if="messages.length === 0 && !streamingContent" class="chat-empty">
          <p class="chat-empty-title">告诉我你的想法，或让灵感助手帮你找到方向</p>
          <p class="chat-empty-hint">{{ strategyHint }}</p>
        </div>
      </div>

      <!-- 侧栏：字段预览 -->
      <div class="assist-sidebar">
        <div class="sidebar-title">字段预览</div>
        <div class="field-list">
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
        <n-button
          type="primary"
          block
          :disabled="!hasFields"
          @click="handleFillForm"
          style="margin-top: 16px"
        >
          填充到表单
        </n-button>
        <div v-if="autoExtracting" style="font-size: 11px; color: var(--app-text-muted); margin-top: 8px; text-align: center;">
          提取中...
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
import { ref, computed, watch, nextTick } from 'vue'
import { NModal, NSelect, NInput, NButton, NIcon, useMessage } from 'naive-ui'
import { subscribeAssist, type AssistFieldData, type AssistMessage } from '@/api/assist'

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
const messages = ref<AssistMessage[]>([])
const inputMessage = ref('')
const sending = ref(false)
const streamingContent = ref('')
const fieldData = ref<AssistFieldData>({} as AssistFieldData)
const autoExtracting = ref(false)
const chatContainerRef = ref<HTMLElement | null>(null)

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

async function handleSend() {
  const text = inputMessage.value.trim()
  if (!text || sending.value || autoExtracting.value) return

  inputMessage.value = ''
  sending.value = true
  streamingContent.value = ''

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
      },
      onChatChunk(content) {
        streamingContent.value += content
        scrollToBottom()
      },
      onChatDone() {
        // 将流式内容转为正式消息
        if (streamingContent.value) {
          messages.value.push({
            id: `ai_${Date.now()}`,
            role: 'assistant',
            content: streamingContent.value,
            created_at: new Date().toISOString(),
          })
        }
        streamingContent.value = ''
        sending.value = false
        // 每次 AI 回复后自动提取字段
        autoGenerateFields()
      },
      onError(err) {
        message.error(err)
        sending.value = false
        streamingContent.value = ''
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
  // modal 关闭不做额外操作，会话已持久化
}
</script>

<style scoped>
.assist-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.assist-header-title {
  font-size: 17px;
  font-weight: 700;
}

.assist-body {
  display: flex;
  gap: 16px;
  height: calc(80vh - 160px);
  min-height: 360px;
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
  overflow-y: auto;
}

.sidebar-title {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 12px;
  color: var(--app-text-primary);
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
    height: calc(80vh - 140px);
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
</style>
