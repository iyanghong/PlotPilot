<!-- QualityPanel.vue — 叙事质量面板 — 作者：Axelton -->
<script setup lang="ts">
import { computed } from 'vue'
import { NCard, NGrid, NGi } from 'naive-ui'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { GaugeChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import StatCard from './StatCard.vue'
import { useIsMobile } from '@/composables/useIsMobile'
import type { DashboardData } from '@/api/admin'

use([GaugeChart, PieChart, GridComponent, TooltipComponent, CanvasRenderer])

const { isMobile } = useIsMobile()
const props = defineProps<{ data: DashboardData['quality'] }>()

const gaugeOption = computed(() => ({
  series: [{
    type: 'gauge',
    startAngle: 200, endAngle: -20,
    min: 0, max: 1,
    progress: { show: true, width: 12, itemStyle: { color: '#1677ff' } },
    axisLine: { lineStyle: { width: 12 } },
    axisTick: { show: false }, axisLabel: { show: false },
    splitLine: { show: false },
    detail: { formatter: '{value}', fontSize: 18, offsetCenter: [0, '60%'] },
    data: [{ value: props.data.foreshadow_closure_rate, name: '伏笔闭合率' }],
  }],
}))

const auditPieOption = computed(() => ({
  tooltip: { trigger: 'item' },
  series: [{
    type: 'pie', radius: ['50%', '75%'],
    data: [
      { name: '通过', value: Math.round(props.data.audit_pass_rate * 100), itemStyle: { color: '#52c41a' } },
      { name: '需修改', value: Math.round((1 - props.data.audit_pass_rate) * 100), itemStyle: { color: '#fa8c16' } },
    ],
    label: { fontSize: 10 },
  }],
}))
</script>

<template>
  <n-card title="叙事质量" size="small" embedded>
    <n-grid :cols="3" :x-gap="12">
      <n-gi><StatCard label="风格评分" :value="(data.avg_style_score * 100).toFixed(0)" unit="分" color="#1677ff" /></n-gi>
      <n-gi><StatCard label="待闭合伏笔" :value="data.open_foreshadows" color="#fa8c16" /></n-gi>
      <n-gi><StatCard label="漂流告警" :value="data.drift_alerts" color="#ff4d4f" /></n-gi>
    </n-grid>
    <n-grid :cols="isMobile ? 1 : 2" style="margin-top:16px">
      <n-gi><v-chart :style="{ height: isMobile ? '180px' : '220px' }" :option="gaugeOption" autoresize /></n-gi>
      <n-gi><v-chart :style="{ height: isMobile ? '180px' : '220px' }" :option="auditPieOption" autoresize /></n-gi>
    </n-grid>
  </n-card>
</template>
