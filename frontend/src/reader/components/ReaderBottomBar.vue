<template>
  <div class="reader-bottom-bar">
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
defineProps<{
  currentNumber: number
  totalChapters: number
  isFirstChapter: boolean
  isLastChapter: boolean
}>()

defineEmits<{
  prev: []
  next: []
  'open-settings': []
}>()
</script>

<style scoped>
.reader-bottom-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 10px 20px;
  background: #f0ece6;
  border-top: 1px solid #e0d8cc;
  color: #5c4a3a;
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

.bottom-btn:hover:not(:disabled) {
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
