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
.stat-card { text-align: center; }
.stat-label { font-size: 13px; color: var(--n-text-color-2); margin-bottom: 6px; }
.stat-value { font-size: 28px; font-weight: 700; }
.stat-unit { font-size: 14px; font-weight: 400; margin-left: 4px; }
</style>
