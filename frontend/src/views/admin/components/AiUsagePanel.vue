<!-- AiUsagePanel.vue — AI 调用面板 — 作者：Axelton -->
<script setup lang="ts">
import { computed } from 'vue'
import { NCard, NGrid, NGi } from 'naive-ui'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart, BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import StatCard from './StatCard.vue'
import type { DashboardData } from '@/api/admin'

use([LineChart, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{ data: DashboardData['ai_usage'] }>()

const trendOption = computed(() => ({
  grid: { left: 40, right: 16, top: 20, bottom: 24 },
  xAxis: { type: 'category', data: props.data.daily_trend.map(d => d.date.slice(5)), axisLabel: { fontSize: 10 } },
  yAxis: { type: 'value', axisLabel: { fontSize: 10 } },
  tooltip: { trigger: 'axis' },
  series: [{ type: 'line', data: props.data.daily_trend.map(d => d.call_count), smooth: true, areaStyle: { opacity: 0.2 }, itemStyle: { color: '#1677ff' } }],
}))

const modelPieOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, textStyle: { fontSize: 10 } },
  series: [{
    type: 'pie', radius: ['45%', '70%'],
    data: props.data.by_model.map(m => ({ name: m.model, value: m.calls })),
    label: { fontSize: 10 },
  }],
}))
</script>

<template>
  <n-card title="AI 调用" size="small" embedded>
    <n-grid :cols="4" :x-gap="12">
      <n-gi><StatCard label="今日调用" :value="data.today_calls" color="#1677ff" /></n-gi>
      <n-gi><StatCard label="今日 Token" :value="data.today_tokens.toLocaleString()" color="#52c41a" /></n-gi>
      <n-gi><StatCard label="总调用" :value="data.total_calls.toLocaleString()" color="#722ed1" /></n-gi>
      <n-gi><StatCard label="平均延迟" :value="data.avg_latency_ms" unit="ms" color="#fa8c16" /></n-gi>
    </n-grid>
    <n-grid :cols="2" style="margin-top:16px">
      <n-gi><v-chart style="height:240px" :option="trendOption" autoresize /></n-gi>
      <n-gi><v-chart style="height:240px" :option="modelPieOption" autoresize /></n-gi>
    </n-grid>
  </n-card>
</template>
