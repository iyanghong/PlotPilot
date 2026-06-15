<!-- AdminMobileTopBar.vue — 移动端顶栏 — 作者：Axelton -->
<script setup lang="ts">
import { MenuOutline } from '@vicons/ionicons5'

defineEmits<{ (e: 'menu'): void }>()
defineProps<{ title: string }>()
</script>

<template>
  <div class="admin-mobile-topbar">
    <n-button text size="large" @click="$emit('menu')">
      <template #icon><n-icon><menu-outline /></n-icon></template>
    </n-button>
    <span class="admin-mobile-title">{{ title }}</span>
    <div style="width:34px" />
  </div>
</template>

<style scoped>
.admin-mobile-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--n-color);
  border-bottom: 1px solid var(--n-border-color);
  position: sticky;
  top: 0;
  z-index: 10;
}
.admin-mobile-title {
  font-size: 16px;
  font-weight: 600;
}
</style>
