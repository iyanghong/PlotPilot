<!-- VersionPanel.vue — 版本更新面板 — 作者：Axelton -->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NButton, NTag, NSpace, NSpin, useMessage } from 'naive-ui'
import { adminApi, type VersionStatus, type UpdateResult } from '@/api/admin'

const message = useMessage()

const loading = ref(true)
const updating = ref(false)
const status = ref<VersionStatus | null>(null)

async function fetchStatus() {
  loading.value = true
  try {
    status.value = await adminApi.getVersionStatus()
  } catch (e: any) {
    message.error('获取版本状态失败: ' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

async function handleUpdate() {
  updating.value = true
  try {
    const result: UpdateResult = await adminApi.triggerUpdate()
    if (result.success) {
      message.success(result.message)
      // 刷新状态
      await fetchStatus()
    } else {
      message.error(result.message)
    }
  } catch (e: any) {
    message.error('更新失败: ' + (e.message || '未知错误'))
  } finally {
    updating.value = false
  }
}

onMounted(() => {
  fetchStatus()
})
</script>

<template>
  <n-card title="版本更新" size="small" embedded>
    <n-spin :show="loading">
      <div v-if="status" class="version-content">
        <!-- 版本号 & 分支 -->
        <div class="version-row">
          <span class="version-label">版本</span>
          <span class="version-value">v{{ status.current_version }}</span>
          <n-tag size="small" :bordered="false">{{ status.git_branch }}</n-tag>
        </div>

        <!-- 提交 & 构建 -->
        <div class="version-row version-row-muted">
          <span class="version-label">提交</span>
          <code class="version-commit">{{ status.git_commit }}</code>
          <span class="version-sep">·</span>
          <span class="version-build">{{ status.build_id }}</span>
        </div>

        <!-- 状态指示 -->
        <div class="version-status-row">
          <!-- 更新状态 -->
          <n-tag v-if="status.update_available" type="warning" size="small">
            有 {{ status.commits_behind }} 个新提交待拉取
          </n-tag>
          <n-tag v-else type="success" size="small">
            已是最新版本
          </n-tag>

          <!-- 本地改动 -->
          <n-tag v-if="status.has_local_changes" type="error" size="small">
            有未提交的本地改动
          </n-tag>
        </div>

        <!-- 操作按钮 -->
        <div class="version-actions">
          <n-button
            size="small"
            type="primary"
            :disabled="!status.update_available || status.has_local_changes"
            :loading="updating"
            @click="handleUpdate"
          >
            {{ status.has_local_changes ? '请先提交本地改动' : status.update_available ? '立即更新' : '已是最新' }}
          </n-button>
          <n-button
            size="small"
            quaternary
            :loading="loading"
            @click="fetchStatus"
          >
            刷新状态
          </n-button>
        </div>
      </div>
    </n-spin>
  </n-card>
</template>

<style scoped>
.version-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.version-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.version-row-muted {
  color: var(--n-text-color-3, #999);
}

.version-label {
  font-weight: 600;
  color: var(--n-text-color-2, #666);
  min-width: 32px;
}

.version-value {
  font-weight: 600;
  color: var(--n-text-color, #333);
}

.version-commit {
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 12px;
  background: var(--n-action-color, rgba(0,0,0,0.04));
  padding: 1px 6px;
  border-radius: 4px;
}

.version-sep {
  color: var(--n-text-color-3, #ccc);
}

.version-build {
  font-size: 11px;
}

.version-status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.version-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}
</style>
