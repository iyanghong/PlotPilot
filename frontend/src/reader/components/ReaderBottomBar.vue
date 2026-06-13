<template>
  <div
    class="reader-bottom-bar"
    :class="{ 'bar-visible': isActive }"
    @mouseenter="isHovering = true"
    @mouseleave="isHovering = false"
  >
    <button class="bottom-btn" :disabled="isFirstChapter" @click="$emit('prev')">
      ◀ 上一章
    </button>
    <span class="bottom-progress">
      第 {{ currentNumber }} / {{ totalChapters }} 章
    </span>
    <button class="bottom-btn" :disabled="isLastChapter" @click="$emit('next')">
      下一章 ▶
    </button>
    <button class="bottom-btn bottom-btn-settings" @click="$emit('open-settings')">
      Aa
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  currentNumber: number
  totalChapters: number
  isFirstChapter: boolean
  isLastChapter: boolean
  visible: boolean
}>()

defineEmits<{
  prev: []
  next: []
  'open-settings': []
}>()

/** 鼠标是否悬停在栏位区域 */
const isHovering = ref(false)

/** 有效可见：滚动到底部 或 鼠标悬停 */
const isActive = computed(() => props.visible || isHovering.value)
</script>

<style scoped>
.reader-bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 10px 20px;
  background: transparent;
  border-top: 1px solid transparent;
  color: #5c4a3a;
  opacity: 0;
  pointer-events: none;
  transition: background 0.4s ease, opacity 0.4s ease, border-color 0.4s ease;
}

.reader-bottom-bar.bar-visible {
  background: #f0ece6;
  border-top-color: #e0d8cc;
  opacity: 1;
  pointer-events: auto;
}

.bottom-btn {
  background: transparent;
  border: 1px solid #c4b9a8;
  border-radius: 6px;
  padding: 6px 14px;
  font-size: 13px;
  cursor: pointer;
  color: inherit;
  transition: all 0.15s;
}

.reader-bottom-bar.bar-visible .bottom-btn:hover:not(:disabled) {
  background: #e8e0d4;
  border-color: #8b7355;
}

.bottom-btn:disabled { opacity: 0.35; cursor: default; }

.bottom-progress {
  font-size: 13px;
  font-weight: 600;
  opacity: 0.8;
}

.bottom-btn-settings {
  font-weight: 700;
  font-size: 14px;
  letter-spacing: -0.02em;
}
</style>
