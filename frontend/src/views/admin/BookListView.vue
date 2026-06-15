<!-- BookListView.vue — 书籍管理页 — 作者：Axelton -->
<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NCard, NDataTable, NButton, NPopconfirm, NTag, NSpace, NInput, useMessage } from 'naive-ui'
import { adminApi, type BookDTO } from '@/api/admin'

const message = useMessage()
const books = ref<BookDTO[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const search = ref('')

const stageLabels: Record<string, string> = {
  planning: '规划中', writing: '写作中', auditing: '审核中', completed: '已完成',
}

const columns = [
  { title: '书名', key: 'title', ellipsis: { tooltip: true } },
  { title: '作者', key: 'author', width: 100 },
  {
    title: '阶段', key: 'stage', width: 80,
    render(row: BookDTO) {
      const type = row.stage === 'completed' ? 'success' : row.stage === 'writing' ? 'info' : 'default'
      return h(NTag, { type, size: 'small' }, { default: () => stageLabels[row.stage] || row.stage })
    },
  },
  { title: '字数', key: 'word_count', width: 80, render(row: BookDTO) { return row.word_count.toLocaleString() } },
  { title: '章节', key: 'chapter_count', width: 60 },
  {
    title: '操作', key: 'actions', width: 80,
    render(row: BookDTO) {
      return h(NPopconfirm, { onPositiveClick: () => deleteBook(row.id) }, {
        default: () => '确认删除？',
        trigger: () => h(NButton, { size: 'small', type: 'error', text: true }, { default: () => '删除' }),
      })
    },
  },
]

async function loadBooks() {
  loading.value = true
  try {
    const res = await adminApi.listBooks({ page: page.value, page_size: 20, search: search.value })
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

onMounted(loadBooks)
</script>

<template>
  <div>
    <h2 style="margin:0 0 16px">书籍管理</h2>
    <n-card>
      <n-space style="margin-bottom:12px">
        <n-input v-model:value="search" placeholder="搜索书名..." clearable style="width:240px" @keyup.enter="loadBooks" />
        <n-button type="primary" @click="loadBooks">搜索</n-button>
      </n-space>
      <n-dataTable :columns="columns" :data="books" :loading="loading" :pagination="{ page: page, pageSize: 20, itemCount: total }" />
    </n-card>
  </div>
</template>
