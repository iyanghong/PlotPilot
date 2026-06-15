<!-- TokenRankingPanel.vue — Token 消耗排行面板 — 作者：Axelton -->
<script setup lang="ts">
import { computed } from 'vue'
import { NCard } from 'naive-ui'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useIsMobile } from '@/composables/useIsMobile'
import type { DashboardData } from '@/api/admin'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const { isMobile } = useIsMobile()
const props = defineProps<{ data: DashboardData['token_ranking'] }>()

/** 格式化 token 数值：大于 1M 显示 M，大于 1K 显示 K */
function formatTokens(v: number): string {
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(1) + 'M'
  if (v >= 1_000) return (v / 1_000).toFixed(1) + 'K'
  return String(v)
}

/** 截断过长标题 */
function truncateTitle(title: string, max = 10): string {
  return title.length > max ? title.slice(0, max) + '…' : title
}

const barOption = computed(() => {
  const items = [...props.data.top_novels_by_tokens].reverse()
  return {
    grid: { left: 8, right: 52, top: 8, bottom: 8, containLabel: true },
    xAxis: {
      type: 'value',
      axisLabel: {
        fontSize: 10,
        formatter: (v: number) => formatTokens(v),
      },
      splitLine: { lineStyle: { type: 'dashed' } },
    },
    yAxis: {
      type: 'category',
      data: items.map((r) => truncateTitle(r.title, isMobile ? 6 : 10)),
      axisLabel: { fontSize: 10 },
      inverse: true,
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const d = items[params[0]?.dataIndex]
        if (!d) return ''
        return `${d.title}<br/>Token 消耗：${d.total_tokens.toLocaleString()}`
      },
    },
    series: [{
      type: 'bar',
      data: items.map((r) => r.total_tokens),
      barMaxWidth: 28,
      itemStyle: {
        borderRadius: [0, 4, 4, 0],
        color: '#fa8c16',
      },
    }],
  }
})
</script>

<template>
  <n-card title="📊 Token 消耗排行 (Top 10)" size="small" embedded>
    <v-chart
      :style="{ height: isMobile ? '220px' : '260px' }"
      :option="barOption"
      autoresize
    />
  </n-card>
</template>
