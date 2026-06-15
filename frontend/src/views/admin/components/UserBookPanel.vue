<!-- UserBookPanel.vue — 用户 & 书籍面板 — 作者：Axelton -->
<script setup lang="ts">
import { computed } from 'vue'
import { NCard, NGrid, NGi } from 'naive-ui'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import StatCard from './StatCard.vue'
import type { DashboardData } from '@/api/admin'

use([LineChart, BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps<{ data: DashboardData['books'] }>()

const stageBarOption = computed(() => ({
  grid: { left: 70, right: 16, top: 8, bottom: 8 },
  xAxis: { type: 'value', axisLabel: { fontSize: 10 } },
  yAxis: { type: 'category', data: ['规划中', '写作中', '审核中', '已完成'], axisLabel: { fontSize: 10 } },
  tooltip: { trigger: 'axis' },
  series: [{
    type: 'bar',
    data: [
      props.data.by_stage.planning,
      props.data.by_stage.writing,
      props.data.by_stage.auditing,
      props.data.by_stage.completed,
    ],
    itemStyle: { borderRadius: [0, 4, 4, 0] },
    label: { show: true, position: 'right', fontSize: 10 },
  }],
}))

const weeklyOption = computed(() => ({
  grid: { left: 40, right: 16, top: 20, bottom: 24 },
  xAxis: { type: 'category', data: props.data.weekly_new_trend.map(w => w.week.slice(-2)), axisLabel: { fontSize: 10 } },
  yAxis: { type: 'value', axisLabel: { fontSize: 10 } },
  tooltip: { trigger: 'axis' },
  series: [{ type: 'line', data: props.data.weekly_new_trend.map(w => w.count), itemStyle: { color: '#52c41a' } }],
}))
</script>

<template>
  <n-card title="用户 & 书籍" size="small" embedded>
    <n-grid :cols="2" :x-gap="12">
      <n-gi><StatCard label="总书籍" :value="data.total" color="#1677ff" /></n-gi>
      <n-gi><StatCard label="本周活跃" :value="data.active_this_week" unit="本" color="#52c41a" /></n-gi>
    </n-grid>
    <n-grid :cols="2" style="margin-top:16px">
      <n-gi><v-chart style="height:200px" :option="stageBarOption" autoresize /></n-gi>
      <n-gi><v-chart style="height:200px" :option="weeklyOption" autoresize /></n-gi>
    </n-grid>
  </n-card>
</template>
