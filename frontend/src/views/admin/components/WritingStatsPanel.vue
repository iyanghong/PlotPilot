<!-- WritingStatsPanel.vue — 写作产出面板 — 作者：Axelton -->
<script setup lang="ts">
import { computed } from 'vue'
import { NGrid, NGi, NCard } from 'naive-ui'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart, BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import StatCard from './StatCard.vue'
import { useIsMobile } from '@/composables/useIsMobile'
import type { DashboardData } from '@/api/admin'

use([LineChart, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const { isMobile } = useIsMobile()
const props = defineProps<{ data: DashboardData['writing'] }>()

const dailyTrendOption = computed(() => ({
  grid: { left: 40, right: 16, top: 20, bottom: 24 },
  xAxis: { type: 'category', data: props.data.daily_trend.map(d => d.date.slice(5)), axisLabel: { fontSize: 10 } },
  yAxis: { type: 'value', axisLabel: { fontSize: 10 } },
  tooltip: { trigger: 'axis' },
  series: [{ type: 'line', data: props.data.daily_trend.map(d => d.word_count), smooth: true, areaStyle: { opacity: 0.15 } }],
}))
</script>

<template>
  <n-card title="写作产出" size="small" embedded>
    <n-grid :cols="isMobile ? 2 : 4" :x-gap="12">
      <n-gi><StatCard label="总字数" :value="data.total_words.toLocaleString()" unit="字" color="#1677ff" /></n-gi>
      <n-gi><StatCard label="总章节" :value="data.total_chapters" color="#52c41a" /></n-gi>
      <n-gi><StatCard label="完本" :value="data.completed_novels" unit="本" color="#722ed1" /></n-gi>
      <n-gi><StatCard label="平均章节" :value="data.avg_words_per_chapter" unit="字/章" color="#fa8c16" /></n-gi>
    </n-grid>
    <v-chart :style="{ height: isMobile ? '180px' : '260px', marginTop: '16px' }" :option="dailyTrendOption" autoresize />
  </n-card>
</template>
