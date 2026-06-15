<!-- BookListView.vue — 书籍管理卡片布局 — 作者：Axelton -->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NCard, NButton, NPopconfirm, NTag, NSpace, NInput, NGi, NGrid, NEmpty, NSelect, NIcon, useMessage } from 'naive-ui'
import { AddOutline, BookOutline, OpenOutline, TrashOutline } from '@vicons/ionicons5'
import { adminApi, type BookDTO } from '@/api/admin'
import { useIsMobile } from '@/composables/useIsMobile'

const router = useRouter()
const message = useMessage()
const { isMobile } = useIsMobile()

const books = ref<BookDTO[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const search = ref('')
const stageFilter = ref('')

const stageLabels: Record<string, string> = {
  planning: '规划中', writing: '写作中', auditing: '审核中', completed: '已完成',
}
const stageColors: Record<string, string> = {
  planning: 'default', writing: 'info', auditing: 'warning', completed: 'success',
}
const statusLabels: Record<string, string> = {
  running: '运行中', stopped: '已停止', error: '异常', paused: '已暂停',
}
const statusColors: Record<string, string> = {
  running: 'success', stopped: 'default', error: 'error', paused: 'warning',
}

async function loadBooks() {
  loading.value = true
  try {
    const res = await adminApi.listBooks({
      page: page.value,
      page_size: 12,
      search: search.value,
      stage: stageFilter.value,
    })
    books.value = res.data
    total.value = res.total
  } catch (e: any) { message.error('加载书籍列表失败') }
  finally { loading.value = false }
}

async function deleteBook(novelId: string) {
  try {
    await adminApi.deleteBook(novelId)
    message.success('书籍已删除')
    loadBooks()
  } catch (e: any) { message.error('删除失败') }
}

function goWorkbench(book: BookDTO) {
  router.push(`/book/${book.slug}/workbench`)
}

onMounted(loadBooks)
</script>

<template>
  <div>
    <n-space justify="space-between" align="center" style="margin-bottom:16px">
      <h2 style="margin:0">书籍管理</h2>
      <n-space>
        <n-button secondary @click="router.push('/')">
          <template #icon><n-icon><AddOutline /></n-icon></template>
          新建书籍
        </n-button>
        <n-select
          v-model:value="stageFilter"
          placeholder="按阶段筛选"
          clearable
          style="width:140px"
          :options="[
            { label:'全部', value:'' },
            { label:'规划中', value:'planning' },
            { label:'写作中', value:'writing' },
            { label:'审核中', value:'auditing' },
            { label:'已完成', value:'completed' },
          ]"
          @update:value="page=1; loadBooks()"
        />
        <n-input v-model:value="search" placeholder="搜索书名..." clearable style="width:200px"
          @keyup.enter="page=1; loadBooks()" />
        <n-button type="primary" @click="page=1; loadBooks()">搜索</n-button>
      </n-space>
    </n-space>

    <n-empty v-if="!loading && books.length === 0" description="暂无书籍" style="margin-top:80px" />

    <n-grid :cols="isMobile ? 1 : 2" :x-gap="16" :y-gap="16" v-else>
      <n-gi v-for="book in books" :key="book.id">
        <n-card hoverable class="book-card" @click="goWorkbench(book)">
          <div class="book-card-inner">
            <!-- 左侧封面占位 -->
            <div class="book-cover">
              <n-icon :size="36" color="var(--n-text-color-3)">
                <BookOutline />
              </n-icon>
            </div>

            <!-- 右侧信息 -->
            <div class="book-info">
              <div class="book-title" :title="book.title">{{ book.title }}</div>
              <div class="book-meta">
                <span class="book-author">{{ book.author }}</span>
              </div>
              <div class="book-tags">
                <n-tag :type="stageColors[book.stage] || 'default'" size="tiny">
                  {{ stageLabels[book.stage] || book.stage }}
                </n-tag>
                <n-tag :type="statusColors[book.autopilot_status] || 'default'" size="tiny">
                  {{ statusLabels[book.autopilot_status] || book.autopilot_status }}
                </n-tag>
              </div>
              <div class="book-stats">
                <span>{{ book.word_count.toLocaleString() }} 字</span>
                <span class="book-stats-sep">|</span>
                <span>{{ book.chapter_count }} 章</span>
              </div>
            </div>

            <!-- 右侧操作区 -->
            <div class="book-actions" @click.stop>
              <n-button size="tiny" text type="primary" @click="goWorkbench(book)" :title="'打开工作台'">
                <template #icon><n-icon><OpenOutline /></n-icon></template>
              </n-button>
              <n-popconfirm @positive-click="deleteBook(book.id)">
                <template #default>确认删除「{{ book.title.slice(0, 20) }}{{ book.title.length > 20 ? '...' : '' }}」？</template>
                <template #trigger>
                  <n-button size="tiny" text type="error" title="删除">
                    <template #icon><n-icon><TrashOutline /></n-icon></template>
                  </n-button>
                </template>
              </n-popconfirm>
            </div>
          </div>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- 分页 -->
    <n-space v-if="total > 12" justify="center" style="margin-top:16px">
      <n-button :disabled="page <= 1" @click="page--; loadBooks()">上一页</n-button>
      <span style="line-height:34px">{{ page }} / {{ Math.ceil(total / 12) }}</span>
      <n-button :disabled="page >= Math.ceil(total / 12)" @click="page++; loadBooks()">下一页</n-button>
    </n-space>
  </div>
</template>

<style scoped>
.book-card {
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}
.book-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
}
.book-card-inner {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}
.book-cover {
  width: 56px;
  height: 72px;
  border-radius: 6px;
  background: var(--n-color-embedded);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.book-info {
  flex: 1;
  min-width: 0;
}
.book-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.book-meta {
  font-size: 12px;
  color: var(--n-text-color-3);
  margin-bottom: 6px;
}
.book-tags {
  display: flex;
  gap: 4px;
  margin-bottom: 6px;
}
.book-stats {
  font-size: 12px;
  color: var(--n-text-color-2);
}
.book-stats-sep {
  margin: 0 6px;
  color: var(--n-divider-color);
}
.book-actions {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex-shrink: 0;
}
</style>
