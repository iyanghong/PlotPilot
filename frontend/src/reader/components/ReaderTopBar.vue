<template>
  <div
    class="reader-top-bar"
    :class="{ 'bar-visible': isActive }"
    @mouseenter="isHovering = true"
    @mouseleave="isHovering = false"
  >
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
import { ref, computed } from 'vue'

const props = defineProps<{
  title: string
  isBookmarked: boolean
  visible: boolean
}>()

defineEmits<{
  back: []
  'toggle-toc': []
  'toggle-bookmark': []
}>()

/** 鼠标是否悬停在栏位区域 */
const isHovering = ref(false)

/** 有效可见：滚动到顶部 或 鼠标悬停 */
const isActive = computed(() => props.visible || isHovering.value)
</script>

<style scoped>
.reader-top-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 20px;
  background: transparent;
  border-bottom: 1px solid transparent;
  color: #5c4a3a;
  opacity: 0.35;
  transition: background 0.4s ease, opacity 0.4s ease, border-color 0.4s ease;
}

.reader-top-bar.bar-visible {
  background: #f0ece6;
  border-bottom-color: #e0d8cc;
  opacity: 1;
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

.reader-top-bar.bar-visible .top-btn:hover { background: #e8e0d4; }
.top-right { display: flex; gap: 4px; }
.bookmarked { color: #d4a017; }
</style>
