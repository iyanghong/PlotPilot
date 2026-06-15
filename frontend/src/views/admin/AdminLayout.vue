<!-- AdminLayout.vue — 后台管理响应式布局壳 — 作者：Axelton -->
<script setup lang="ts">
import { ref, computed, h, type Component } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NIcon, NLayout, NLayoutSider, NLayoutContent, NMenu } from 'naive-ui'
import {
  AnalyticsOutline,
  PeopleOutline,
  BookOutline,
} from '@vicons/ionicons5'
import { useAuthStore } from '@/stores/authStore'
import { useIsMobile } from '@/composables/useIsMobile'
import AdminMobileTopBar from './components/AdminMobileTopBar.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const { isMobile } = useIsMobile()

const drawerOpen = ref(false)

interface MenuItem {
  label: string
  key: string
  icon: Component
  adminOnly?: boolean
}

const menuItems = computed<MenuItem[]>(() => {
  const items: MenuItem[] = [
    { label: '驾驶舱', key: '/admin/dashboard', icon: AnalyticsOutline },
  ]
  if (authStore.isAdmin) {
    items.push(
      { label: '用户管理', key: '/admin/users', icon: PeopleOutline, adminOnly: true },
      { label: '书籍管理', key: '/admin/books', icon: BookOutline, adminOnly: true },
    )
  }
  return items
})

const currentTitle = computed(() => {
  const item = menuItems.value.find(m => m.key === route.path)
  return item?.label || '后台管理'
})

function onMenuClick(key: string) {
  drawerOpen.value = false
  router.push(key)
}

function renderIcon(icon: Component) {
  return () => h(NIcon, null, { default: () => h(icon) })
}
</script>

<template>
  <!-- 桌面端 -->
  <n-layout v-if="!isMobile" has-sider position="absolute" style="top:0;bottom:0;left:0;right:0">
    <n-layout-sider bordered width="200">
      <div class="admin-logo">后台管理</div>
      <n-menu
        :value="route.path"
        :options="menuItems.map(m => ({
          label: m.label, key: m.key,
          icon: renderIcon(m.icon),
        }))"
        @update:value="onMenuClick"
      />
    </n-layout-sider>
    <n-layout-content>
      <div class="admin-content">
        <router-view />
      </div>
    </n-layout-content>
  </n-layout>

  <!-- 移动端 -->
  <div v-else class="admin-mobile">
    <AdminMobileTopBar :title="currentTitle" @menu="drawerOpen = true" />
    <n-drawer v-model:show="drawerOpen" placement="left" :width="220">
      <n-drawer-content title="后台管理" closable>
        <n-menu
          :value="route.path"
          :options="menuItems.map(m => ({
            label: m.label, key: m.key,
            icon: renderIcon(m.icon),
          }))"
          @update:value="onMenuClick"
        />
      </n-drawer-content>
    </n-drawer>
    <div class="admin-content-mobile">
      <router-view />
    </div>
  </div>
</template>

<style scoped>
.admin-logo {
  padding: 16px;
  font-size: 18px;
  font-weight: 700;
  text-align: center;
  border-bottom: 1px solid var(--n-border-color);
}
.admin-content {
  padding: 24px;
  height: 100%;
  overflow-y: auto;
}
.admin-content-mobile {
  padding: 12px;
}
.admin-mobile {
  min-height: 100dvh;
  background: var(--n-color);
}
</style>
