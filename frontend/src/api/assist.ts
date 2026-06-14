/** 灵感助手 API 封装 — SSE 流式消费 — 作者：Axelton */
import { resolveHttpUrl } from './config'

export interface AssistSessionInfo {
  session_id: string
  strategy: string
}

export interface AssistMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  field_suggestions?: Record<string, unknown>
  created_at: string
}

export interface AssistResumeData {
  session_id: string
  strategy: string
  status: string
  messages: AssistMessage[]
}

export interface AssistFieldData {
  title: string
  premise: string
  genre: string
  world_preset: string
  story_structure: string
  pacing_control: string
  writing_style: string
  special_requirements: string
}

export interface AssistChatHandlers {
  onSessionCreated?: (info: AssistSessionInfo) => void
  onChatChunk?: (content: string) => void
  onChatDone?: (messageId: string) => void
  onFieldsDone?: (fields: AssistFieldData) => void
  onResumeDone?: (data: AssistResumeData) => void
  onConnected?: () => void
  onDisconnected?: () => void
  onStreamEnd?: () => void
  onError?: (error: string) => void
}

/**
 * 发起 SSE 请求到灵感助手
 * 返回 AbortController 用于取消
 */
export function subscribeAssist(
  body: {
    novel_id: string
    session_id?: string
    strategy?: string
    action: 'chat' | 'generate_fields' | 'resume'
    message?: string
  },
  handlers: AssistChatHandlers,
): AbortController {
  const ctrl = new AbortController()

  void (async () => {
    try {
      const url = resolveHttpUrl('/api/v1/assist/inspire')
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
      }
      const token = localStorage.getItem('plotpilot_token')
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      const res = await fetch(url, {
        method: 'POST',
        signal: ctrl.signal,
        headers,
        body: JSON.stringify(body),
      })

      if (!res.ok || !res.body) {
        handlers.onError?.(`HTTP ${res.status}`)
        handlers.onDisconnected?.()
        return
      }

      handlers.onConnected?.()

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      const flushBlocks = (buf: string): string => {
        let sepIdx: number
        let rest = buf
        while ((sepIdx = rest.indexOf('\n\n')) >= 0) {
          const block = rest.slice(0, sepIdx)
          rest = rest.slice(sepIdx + 2)

          let eventType = ''
          let dataStr = ''

          for (const line of block.split('\n')) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7)
            } else if (line.startsWith('data: ')) {
              dataStr = line.slice(6)
            }
          }

          if (!dataStr) continue
          try {
            const payload = JSON.parse(dataStr)

            if (payload.error) {
              handlers.onError?.(payload.error)
              continue
            }

            switch (eventType) {
              case 'session_created':
                handlers.onSessionCreated?.(payload as AssistSessionInfo)
                break
              case 'chat_chunk':
                handlers.onChatChunk?.(payload.content || '')
                break
              case 'chat_done':
                handlers.onChatDone?.(payload.message_id || '')
                break
              case 'fields_done':
                handlers.onFieldsDone?.(payload as AssistFieldData)
                break
              default:
                // resume 的 data 无 event type，直接是 JSON
                if (payload.messages) {
                  handlers.onResumeDone?.(payload as AssistResumeData)
                }
            }
          } catch {
            /* 忽略解析失败的行 */
          }
        }
        return rest
      }

      while (true) {
        const { done, value } = await reader.read()
        if (value) buffer += decoder.decode(value, { stream: true })
        buffer = flushBlocks(buffer)
        if (done) {
          buffer += decoder.decode()
          buffer = flushBlocks(buffer)
          break
        }
      }
      handlers.onStreamEnd?.()
    } catch (e) {
      if (e instanceof Error && e.name === 'AbortError') return
      handlers.onError?.(e instanceof Error ? e.message : '流连接异常')
      handlers.onDisconnected?.()
    }
  })()

  return ctrl
}
