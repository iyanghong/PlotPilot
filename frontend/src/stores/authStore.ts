/** 认证状态管理（RBAC）

local 模式（Tauri 桌面端）：后端自动返回内置管理员，前端无需登录
web 模式（浏览器部署）：需要 JWT Token 登录

作者: Axelton
*/
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiAxios } from '@/api/config'

const TOKEN_KEY = 'plotpilot_token'

export interface UserInfo {
  id: string
  username: string
  role: 'admin' | 'user'
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<UserInfo | null>(null)
  const loading = ref(false)
  const initialized = ref(false)
  /** 是否需要登录（web 模式且未认证） */
  const needsLogin = ref(false)

  const isAuthenticated = computed(() => user.value !== null)
  const isAdmin = computed(() => user.value?.role === 'admin')

  /** 设置 token 并持久化 */
  function setToken(t: string) {
    token.value = t
    localStorage.setItem(TOKEN_KEY, t)
  }

  /** 清除 token */
  function clearToken() {
    token.value = null
    localStorage.removeItem(TOKEN_KEY)
  }

  /** 验证当前认证状态 */
  async function checkAuth(): Promise<boolean> {
    loading.value = true
    try {
      const data = await apiAxios.get('/auth/me') as unknown as UserInfo
      user.value = data
      needsLogin.value = false
      return true
    } catch (e: any) {
      // 401 → web 模式且未登录
      if (e?.response?.status === 401) {
        user.value = null
        needsLogin.value = true
      } else {
        // 其他错误 → 可能是 local 模式后端未就绪，不阻断
        user.value = null
        needsLogin.value = false
      }
      return false
    } finally {
      loading.value = false
      initialized.value = true
    }
  }

  /** 登录 */
  async function login(username: string, password: string): Promise<{ success: boolean; error?: string }> {
    loading.value = true
    try {
      const data = await apiAxios.post('/auth/login', { username, password }) as {
        access_token: string
        username: string
        role: string
      }
      setToken(data.access_token)
      user.value = {
        id: '', // login 响应不含 id，后续 checkAuth 补全
        username: data.username,
        role: data.role as 'admin' | 'user',
      }
      needsLogin.value = false
      return { success: true }
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.message || '登录失败'
      return { success: false, error: detail }
    } finally {
      loading.value = false
    }
  }

  /** 注册 */
  async function register(username: string, password: string): Promise<{ success: boolean; error?: string }> {
    loading.value = true
    try {
      await apiAxios.post('/auth/register', { username, password })
      return { success: true }
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.message || '注册失败'
      return { success: false, error: detail }
    } finally {
      loading.value = false
    }
  }

  /** 登出 */
  function logout() {
    clearToken()
    user.value = null
    needsLogin.value = true
  }

  return {
    token,
    user,
    loading,
    initialized,
    needsLogin,
    isAuthenticated,
    isAdmin,
    setToken,
    clearToken,
    checkAuth,
    login,
    logout,
  }
})
