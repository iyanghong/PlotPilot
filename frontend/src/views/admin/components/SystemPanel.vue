<!-- SystemPanel.vue — 系统运行面板 — 作者：Axelton -->
<script setup lang="ts">
import { computed, h } from 'vue'
import { NCard, NGrid, NGi, NTag } from 'naive-ui'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import StatCard from './StatCard.vue'
import type { DashboardData } from '@/api/admin'

use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps<{ data: DashboardData['system'] }>()

const errorTrendOption = computed(() => ({
  grid: { left: 40, right: 16, top: 20, bottom: 24 },
  xAxis: { type: 'category', data: props.data.error_rate_24h.map(e => `${e.hour}h`), axisLabel: { fontSize: 10 } },
  yAxis: { type: 'value', axisLabel: { fontSize: 10 } },
  tooltip: { trigger: 'axis' },
  series: [{ type: 'line', data: props.data.error_rate_24h.map(e => e.error_count), areaStyle: { opacity: 0.1 }, itemStyle: { color: '#ff4d4f' } }],
}))

const latencyOption = computed(() => ({
  grid: { left: 40, right: 16, top: 20, bottom: 24 },
  xAxis: { type: 'category', data: ['P50', 'P95', 'P99'], axisLabel: { fontSize: 10 } },
  yAxis: { type: 'value', name: 'ms', axisLabel: { fontSize: 10 } },
  tooltip: { trigger: 'axis' },
  series: [{ type: 'line', data: [props.data.latency_p50, props.data.latency_p95, props.data.latency_p99], smooth: true, itemStyle: { color: '#52c41a' }, areaStyle: { opacity: 0.1 } }],
}))

function healthTag(status: boolean) {
  return status ? h(NTag, { type: 'success', size: 'small' }, { default: () => '正常' })
                : h(NTag, { type: 'error', size: 'small' }, { default: () => '异常' })
}
</script>

<template>
  <n-card title="系统运行" size="small" embedded>
    <n-grid :cols="4" :x-gap="12">
      <n-gi><StatCard label="自动驾驶中" :value="data.autopilot_running" color="#1677ff" /></n-gi>
      <n-gi><StatCard label="错误数" :value="data.autopilot_errors" :color="data.autopilot_errors > 0 ? '#ff4d4f' : '#52c41a'" /></n-gi>
      <n-gi>
        <StatCard label="P95 延迟" :value="data.latency_p95" unit="ms" color="#fa8c16" />
      </n-gi>
      <n-gi>
        <div class="health-cards">
          <component :is="healthTag(data.health.db)" /> DB
          <component :is="healthTag(data.health.chromadb)" /> ChromaDB
          <component :is="healthTag(data.health.llm)" /> LLM
        </div>
      </n-gi>
    </n-grid>
    <n-grid :cols="2" style="margin-top:16px">
      <n-gi><v-chart style="height:200px" :option="errorTrendOption" autoresize /></n-gi>
      <n-gi><v-chart style="height:200px" :option="latencyOption" autoresize /></n-gi>
    </n-grid>
  </n-card>
</template>

<style scoped>
.health-cards { display:flex; gap:8px; flex-wrap:wrap; align-items:center; font-size:12px; }
</style>
