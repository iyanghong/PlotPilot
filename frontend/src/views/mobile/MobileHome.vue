<template>
  <div class="mobile-home">
    <div class="mobile-home-list">
      <div v-if="loading" class="mobile-home-loading">
        <n-spin size="medium" />
      </div>

      <template v-else-if="books.length">
        <div
          v-for="book in books"
          :key="book.slug"
          class="mobile-book-card"
          @click="enterNovel(book.slug)"
        >
          <div class="mobile-book-top">
            <span class="mobile-book-dot" :class="`dot-${book.stage}`"></span>
            <span class="mobile-book-title">{{ book.title }}</span>
          </div>
          <div class="mobile-book-meta">
            <n-tag :type="getStageType(book.stage)" size="small" round>
              {{ book.stage_label }}
            </n-tag>
            <span v-if="book.genre" class="mobile-book-genre">{{ book.genre }}</span>
          </div>
        </div>
      </template>

      <div v-else class="mobile-home-empty">
        <p>暂无书目</p>
        <n-button type="primary" size="small" @click="goHomeFull">去电脑版新建</n-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/** 移动端首页 Tab — 书目列表
 *
 * 作者: Axelton
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NSpin, NTag, NButton } from 'naive-ui'
import { novelApi, type NovelDTO } from '@/api/novel'
import { getNovelStageLabel, getNovelStageTagType } from '@/domain/novel'

const props = defineProps<{
  slug: string
}>()

defineEmits<{
  'enter-novel': [slug: string]
}>()

const router = useRouter()
const loading = ref(false)
const books = ref<{ slug: string; title: string; stage: string; stage_label: string; genre: string }[]>([])

function getStageType(stage: string) {
  return getNovelStageTagType(stage)
}

function enterNovel(slug: string) {
  router.push(`/book/${slug}/workbench`)
}

function goHomeFull() {
  router.push('/')
}

onMounted(async () => {
  loading.value = true
  try {
    const novels = await novelApi.listNovels()
    books.value = novels.map((n: NovelDTO) => ({
      slug: n.id,
      title: n.title,
      stage: n.stage,
      stage_label: getNovelStageLabel(n.stage),
      genre: n.locked_genre?.trim() || '',
    }))
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.mobile-home {
  height: 100%;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.mobile-home-list {
  padding: 12px;
}

.mobile-home-loading {
  display: flex;
  justify-content: center;
  padding-top: 48px;
}

.mobile-home-empty {
  text-align: center;
  padding-top: 48px;
  color: var(--app-text-muted);
}

.mobile-book-card {
  padding: 14px;
  background: var(--app-surface, #fff);
  border-radius: 10px;
  margin-bottom: 8px;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.mobile-book-card:active {
  background: var(--app-surface-subtle, #f1f5f9);
}

.mobile-book-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.mobile-book-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-planning { background: #3b82f6; }
.dot-writing { background: #f59e0b; }
.dot-reviewing { background: #8b5cf6; }
.dot-completed { background: #10b981; }

.mobile-book-title {
  font-size: 15px;
  font-weight: 650;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mobile-book-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mobile-book-genre {
  font-size: 11px;
  color: var(--app-text-muted);
}
</style>
