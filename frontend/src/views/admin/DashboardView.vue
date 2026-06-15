<!-- DashboardView.vue — 驾驶舱大屏 — 作者：Axelton -->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NSpin, useMessage } from 'naive-ui'
import { adminApi, type DashboardData } from '@/api/admin'
import { useAuthStore } from '@/stores/authStore'
import WritingStatsPanel from './components/WritingStatsPanel.vue'
import AiUsagePanel from './components/AiUsagePanel.vue'
import UserBookPanel from './components/UserBookPanel.vue'
import QualityPanel from './components/QualityPanel.vue'
import CharacterForeshadowPanel from './components/CharacterForeshadowPanel.vue'
import TokenRankingPanel from './components/TokenRankingPanel.vue'
import SystemPanel from './components/SystemPanel.vue'

const authStore = useAuthStore()
const message = useMessage()

const loading = ref(true)
const dashboardData = ref<DashboardData | null>(null)

onMounted(async () => {
  try {
    const scope = authStore.isAdmin ? 'all' : 'user'
    dashboardData.value = await adminApi.getDashboard(scope)
  } catch (e: any) {
    message.error('加载驾驶舱数据失败: ' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <h2 style="margin:0 0 16px">驾驶舱</h2>
    <n-spin :show="loading">
      <div v-if="dashboardData" class="dashboard-grid">
        <WritingStatsPanel :data="dashboardData.writing" />
        <AiUsagePanel :data="dashboardData.ai_usage" />
        <UserBookPanel :data="dashboardData.books" />
        <QualityPanel :data="dashboardData.quality" />
        <CharacterForeshadowPanel :data="dashboardData.cast_foreshadow" />
        <TokenRankingPanel :data="dashboardData.token_ranking" />
        <SystemPanel :data="dashboardData.system" />
      </div>
    </n-spin>
  </div>
</template>

<style scoped>
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
@media (max-width: 1599px) {
  .dashboard-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 767px) {
  .dashboard-grid { grid-template-columns: 1fr; }
}
</style>
