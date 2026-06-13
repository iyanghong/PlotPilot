<template>
  <div class="reader-top-bar">
    <button class="top-btn" @click="$emit('back')">
      ← 返回工作台
    </button>
    <span class="top-title">{{ title }}</span>
    <div class="top-right">
      <button class="top-btn" @click="$emit('toggle-toc')">
        ☰ 目录
      </button>
      <button
        class="top-btn"
        :class="{ bookmarked: isBookmarked }"
        @click="$emit('toggle-bookmark')"
      >
        {{ isBookmarked ? '🔖' : '🏷' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  isBookmarked: boolean
}>()

defineEmits<{
  back: []
  'toggle-toc': []
  'toggle-bookmark': []
}>()
</script>

<style scoped>
.reader-top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 20px;
  background: #f0ece6;
  border-bottom: 1px solid #e0d8cc;
  color: #5c4a3a;
}

.top-title {
  font-size: 15px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 50%;
}

.top-btn {
  background: transparent;
  border: none;
  padding: 4px 10px;
  font-size: 13px;
  cursor: pointer;
  color: inherit;
  border-radius: 4px;
  transition: background 0.15s;
}

.top-btn:hover { background: #e8e0d4; }
.top-right { display: flex; gap: 4px; }
.bookmarked { color: #d4a017; }
</style>
