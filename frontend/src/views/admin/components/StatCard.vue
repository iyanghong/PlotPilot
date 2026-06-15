<!-- StatCard.vue — 通用统计数字卡片 — 作者：Axelton -->
<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  unit?: string
  color?: string
}>()
</script>

<template>
  <n-card size="small" :bordered="false" class="stat-card">
    <div class="stat-label">{{ label }}</div>
    <div class="stat-value" :style="{ color: color || 'var(--n-text-color)' }">
      {{ value }}<span v-if="unit" class="stat-unit">{{ unit }}</span>
    </div>
  </n-card>
</template>

<style scoped>
.stat-card { text-align: center; padding: 8px 4px; }
.stat-label { font-size: clamp(11px, 1.4vw, 13px); color: var(--n-text-color-2); margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.stat-value { font-size: clamp(18px, 3vw, 28px); font-weight: 700; line-height: 1.2; }
.stat-unit { font-size: clamp(11px, 1.4vw, 14px); font-weight: 400; margin-left: 2px; }
</style>
