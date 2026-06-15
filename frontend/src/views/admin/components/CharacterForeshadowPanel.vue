<!-- CharacterForeshadowPanel.vue — 人物 & 伏笔面板 — 作者：Axelton -->
<script setup lang="ts">
import { computed } from 'vue'
import { NCard, NGrid, NGi } from 'naive-ui'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import StatCard from './StatCard.vue'
import { useIsMobile } from '@/composables/useIsMobile'
import type { DashboardData } from '@/api/admin'

use([BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const { isMobile } = useIsMobile()
const props = defineProps<{ data: DashboardData['cast_foreshadow'] }>()

const statusBarOption = computed(() => ({
  grid: { left: 40, right: 16, top: 20, bottom: 24 },
  xAxis: { type: 'category', data: ['planted', 'triggered', 'closed'], axisLabel: { fontSize: 10 } },
  yAxis: { type: 'value', axisLabel: { fontSize: 10 } },
  tooltip: { trigger: 'axis' },
  color: ['#1677ff', '#fa8c16', '#52c41a'],
  series: [{ type: 'bar', data: [
    props.data.by_status.planted,
    props.data.by_status.triggered,
    props.data.by_status.closed,
  ], stack: 'total' }],
}))

const charTypePieOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, textStyle: { fontSize: 10 } },
  series: [{
    type: 'pie', radius: ['45%', '70%'],
    data: [
      { name: '主角', value: props.data.character_type_distribution.protagonist },
      { name: '配角', value: props.data.character_type_distribution.supporting },
      { name: '龙套', value: props.data.character_type_distribution.minor },
    ],
    label: { fontSize: 10 },
  }],
}))
</script>

<template>
  <n-card title="人物 & 伏笔" size="small" embedded>
    <n-grid :cols="2" :x-gap="12">
      <n-gi><StatCard label="平均人物/书" :value="data.avg_characters_per_novel" unit="人" color="#1677ff" /></n-gi>
      <n-gi><StatCard label="总伏笔" :value="data.total_foreshadows" color="#722ed1" /></n-gi>
    </n-grid>
    <n-grid :cols="isMobile ? 1 : 2" style="margin-top:16px">
      <n-gi><v-chart :style="{ height: isMobile ? '180px' : '200px' }" :option="statusBarOption" autoresize /></n-gi>
      <n-gi><v-chart :style="{ height: isMobile ? '180px' : '200px' }" :option="charTypePieOption" autoresize /></n-gi>
    </n-grid>
  </n-card>
</template>
