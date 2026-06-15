<template>
  <div class="mobile-topbar">
    <span class="mobile-topbar-title">{{ title }}</span>
    <n-dropdown trigger="click" placement="bottom-end" :options="menuOptions" @select="handleMenuSelect">
      <div class="mobile-topbar-more" role="button" aria-label="更多">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20">
          <path fill="currentColor" d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/>
        </svg>
      </div>
    </n-dropdown>
  </div>
</template>

<script setup lang="ts">
/** 移动端精简顶栏 — 书名 + 溢出菜单（⋯）
 *
 * 作者: Axelton
 */
import { NDropdown } from 'naive-ui'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import { useAppSettingsShellStore } from '@/stores/appSettingsShellStore'

defineProps<{
  title: string
}>()

const router = useRouter()
const authStore = useAuthStore()
const appSettingsShell = useAppSettingsShellStore()

const menuOptions = [
  { label: 'AI 控制台', key: 'llm', type: 'option' as const },
  { label: '提示词广场', key: 'plaza', type: 'option' as const },
  { label: '在线预览', key: 'reader', type: 'option' as const },
  { label: '应用设置', key: 'settings', type: 'option' as const },
  { label: '退出登录', key: 'logout', type: 'option' as const },
]

function handleMenuSelect(key: string) {
  switch (key) {
    case 'llm':
      // 触发全局 LLM 按钮
      document.querySelector<HTMLButtonElement>('.global-llm-main button')?.click()
      break
    case 'plaza':
      document.querySelector<HTMLButtonElement>('.plaza-main button')?.click()
      break
    case 'reader':
      router.push(`/book/${window.location.pathname.split('/')[2]}/reader`)
      break
    case 'settings':
      appSettingsShell.open()
      break
    case 'logout':
      authStore.logout()
      router.push('/login')
      break
  }
}
</script>

<style scoped>
.mobile-topbar {
  height: 44px;
  min-height: 44px;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  flex-shrink: 0;
}

.mobile-topbar-title {
  font-size: 15px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.mobile-topbar-more {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-radius: 8px;
  flex-shrink: 0;
  margin-left: 8px;
}

.mobile-topbar-more:active {
  background: rgba(255, 255, 255, 0.2);
}
</style>
