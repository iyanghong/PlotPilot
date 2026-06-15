/** 后台管理 API 封装 — 作者：Axelton */
import { apiClient } from './config'

export interface DashboardData {
  writing: {
    total_words: number
    total_chapters: number
    completed_novels: number
    avg_words_per_chapter: number
    daily_trend: Array<{ date: string; word_count: number }>
  }
  ai_usage: {
    total_calls: number
    total_tokens: number
    today_calls: number
    today_tokens: number
    avg_latency_ms: number
    by_model: Array<{ model: string; calls: number; tokens: number }>
    daily_trend: Array<{ date: string; call_count: number }>
  }
  books: {
    total: number
    active_this_week: number
    by_stage: { planning: number; writing: number; auditing: number; completed: number }
    weekly_new_trend: Array<{ week: string; count: number }>
  }
  quality: {
    foreshadow_closure_rate: number
    avg_style_score: number
    audit_pass_rate: number
    drift_alerts: number
    open_foreshadows: number
  }
  cast_foreshadow: {
    avg_characters_per_novel: number
    total_foreshadows: number
    by_status: { planted: number; triggered: number; closed: number }
    character_type_distribution: { protagonist: number; supporting: number; minor: number }
    top_novels_by_characters: Array<{ novel_id: string; title: string; character_count: number }>
    top_novels_by_foreshadows: Array<{ novel_id: string; title: string; foreshadow_count: number }>
  }
  system: {
    autopilot_running: number
    autopilot_waiting: number
    autopilot_errors: number
    error_rate_24h: Array<{ hour: string; error_count: number }>
    latency_p50: number
    latency_p95: number
    latency_p99: number
    health: { db: boolean; chromadb: boolean; llm: boolean }
  }
}

export interface UserDTO {
  id: string
  username: string
  role: string
}

export interface BookDTO {
  id: string
  title: string
  author: string
  stage: string
  autopilot_status: string
  user_id: string
  word_count: number
  chapter_count: number
}

export interface PaginatedData<T> {
  success: boolean
  data: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export const adminApi = {
  /** 获取仪表盘聚合数据 */
  async getDashboard(scope: 'all' | 'user' = 'all'): Promise<DashboardData> {
    const res = await apiClient.get<{ success: boolean; data: DashboardData }>(
      `/admin/dashboard?scope=${scope}`
    )
    return res.data
  },

  /** 列出用户（分页、搜索） */
  async listUsers(params: { page?: number; page_size?: number; search?: string } = {}): Promise<PaginatedData<UserDTO>> {
    return apiClient.get<PaginatedData<UserDTO>>('/admin/users', { params })
  },

  /** 创建用户 */
  async createUser(body: { username: string; password: string; role?: string }) {
    const res = await apiClient.post<{ success: boolean }>('/admin/users', body)
    return res
  },

  /** 更新用户信息 */
  async updateUser(userId: string, body: { role?: string; password?: string }) {
    const res = await apiClient.patch<{ success: boolean }>(`/admin/users/${userId}`, body)
    return res
  },

  /** 删除用户 */
  async deleteUser(userId: string) {
    const res = await apiClient.delete<{ success: boolean }>(`/admin/users/${userId}`)
    return res
  },

  /** 列出书籍（分页、筛选） */
  async listBooks(params: { page?: number; page_size?: number; search?: string; user_id?: string; stage?: string } = {}): Promise<PaginatedData<BookDTO>> {
    return apiClient.get<PaginatedData<BookDTO>>('/admin/books', { params })
  },

  /** 删除书籍 */
  async deleteBook(novelId: string) {
    const res = await apiClient.delete<{ success: boolean }>(`/admin/books/${novelId}`)
    return res
  },

  /** 转移书籍所有权 */
  async transferBookOwner(novelId: string, userId: string) {
    const res = await apiClient.patch<{ success: boolean }>(`/admin/books/${novelId}/owner`, { user_id: userId })
    return res
  },
}
