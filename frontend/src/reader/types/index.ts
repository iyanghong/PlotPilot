// frontend/src/reader/types/index.ts

/** 章节目录项（轻量，来自 GET /novels/{id}/chapters 列表） */
export interface ChapterMeta {
  id: string
  number: number
  title: string
  word_count: number
}

/** 章节正文（来自 GET /novels/{id}/chapters/{num}） */
export interface ChapterContent {
  id: string
  number: number
  title: string
  content: string
  word_count: number
}

/** 阅读进度（存 localStorage） */
export interface ReadingProgress {
  novelId: string
  chapterNumber: number
  scrollTop: number
  updatedAt: number // Date.now()
}

/** 阅读设置（存 localStorage） */
export interface ReaderSettings {
  fontSize: number // 默认 16
  lineHeight: number // 默认 2.0
  paragraphSpacing: string // 默认 '1em'
  marginWidth: number // 默认 48
  theme: 'day' | 'night' | 'parchment' | 'green'
  fontFamily: 'system' | 'serif' | 'kai' | 'hei'
  pageMode: 'scroll' | 'paged'
}

/** 书签 */
export interface Bookmark {
  chapterNumber: number
  chapterTitle: string
  createdAt: number // Date.now()
}

/** 默认阅读设置 */
export function defaultReaderSettings(): ReaderSettings {
  return {
    fontSize: 16,
    lineHeight: 2.0,
    paragraphSpacing: '1em',
    marginWidth: 48,
    theme: 'day',
    fontFamily: 'system',
    pageMode: 'scroll',
  }
}
