<template>
  <n-drawer
    :show="show"
    placement="right"
    :width="300"
    @update:show="$emit('update:show', $event)"
  >
    <n-drawer-content title="阅读设置" closable>
      <div class="settings-section">
        <label class="settings-label">字号：{{ settings.fontSize }}px</label>
        <input
          type="range"
          class="settings-slider"
          :min="12"
          :max="28"
          :value="settings.fontSize"
          @input="update('fontSize', Number(($event.target as HTMLInputElement).value))"
        />
      </div>

      <div class="settings-section">
        <label class="settings-label">行间距</label>
        <div class="settings-options">
          <button
            v-for="v in [1.5, 1.8, 2.0, 2.5]"
            :key="v"
            class="settings-option"
            :class="{ active: settings.lineHeight === v }"
            @click="update('lineHeight', v)"
          >{{ v }}</button>
        </div>
      </div>

      <div class="settings-section">
        <label class="settings-label">段间距</label>
        <div class="settings-options">
          <button
            v-for="v in ['0.5em', '1em', '1.5em']"
            :key="v"
            class="settings-option"
            :class="{ active: settings.paragraphSpacing === v }"
            @click="update('paragraphSpacing', v)"
          >{{ v }}</button>
        </div>
      </div>

      <div class="settings-section">
        <label class="settings-label">页边距</label>
        <div class="settings-options">
          <button
            v-for="opt in marginOptions"
            :key="opt.value"
            class="settings-option"
            :class="{ active: settings.marginWidth === opt.value }"
            @click="update('marginWidth', opt.value)"
          >{{ opt.label }}</button>
        </div>
      </div>

      <div class="settings-section">
        <label class="settings-label">主题</label>
        <div class="settings-themes">
          <button
            v-for="t in themeOptions"
            :key="t.value"
            class="theme-swatch"
            :class="{ active: settings.theme === t.value }"
            :style="{ background: t.bg, color: t.text }"
            :title="t.label"
            @click="update('theme', t.value)"
          >{{ t.label }}</button>
        </div>
      </div>

      <div class="settings-section">
        <label class="settings-label">字体</label>
        <div class="settings-options">
          <button
            v-for="f in fontOptions"
            :key="f.value"
            class="settings-option"
            :class="{ active: settings.fontFamily === f.value }"
            @click="update('fontFamily', f.value)"
          >{{ f.label }}</button>
        </div>
      </div>

      <div class="settings-section">
        <label class="settings-label">翻页模式</label>
        <div class="settings-options">
          <button
            class="settings-option"
            :class="{ active: settings.pageMode === 'scroll' }"
            @click="update('pageMode', 'scroll' as const)"
          >滚动</button>
          <button
            class="settings-option"
            :class="{ active: settings.pageMode === 'paged' }"
            @click="update('pageMode', 'paged' as const)"
          >分页</button>
        </div>
      </div>

      <div class="settings-section">
        <n-button size="small" quaternary @click="$emit('reset')">
          恢复默认设置
        </n-button>
      </div>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup lang="ts">
import { NDrawer, NDrawerContent, NButton } from 'naive-ui'
import type { ReaderSettings } from '../types'

const props = defineProps<{
  show: boolean
  settings: ReaderSettings
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
  'update:settings': [settings: ReaderSettings]
  reset: []
}>()

/** 页边距选项 */
const marginOptions = [
  { label: '窄', value: 24 },
  { label: '标准', value: 48 },
  { label: '宽', value: 80 },
]

/** 主题选项 */
const themeOptions = [
  { label: '日间', value: 'day', bg: '#fafafa', text: '#1a1a1a' },
  { label: '夜间', value: 'night', bg: '#1a1a1a', text: '#c8c8c8' },
  { label: '羊皮纸', value: 'parchment', bg: '#f5f0e8', text: '#3d2e22' },
  { label: '护眼', value: 'green', bg: '#e8f0e3', text: '#2d3a25' },
] as const

/** 字体选项 */
const fontOptions = [
  { label: '系统', value: 'system' },
  { label: '宋体', value: 'serif' },
  { label: '楷体', value: 'kai' },
  { label: '黑体', value: 'hei' },
]

/** 更新单个设置项并通知父组件 */
function update<K extends keyof ReaderSettings>(key: K, value: ReaderSettings[K]) {
  emit('update:settings', { ...props.settings, [key]: value })
}
</script>

<style scoped>
.settings-section { margin-bottom: 20px; }
.settings-label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 8px; color: #555; }
.settings-slider { width: 100%; }
.settings-options { display: flex; gap: 6px; flex-wrap: wrap; }
.settings-option { padding: 5px 12px; border: 1px solid #ddd; border-radius: 6px; background: #fff; font-size: 13px; cursor: pointer; transition: all 0.15s; }
.settings-option:hover { border-color: #999; }
.settings-option.active { background: #4f46e5; color: #fff; border-color: #4f46e5; }
.settings-themes { display: flex; gap: 8px; }
.theme-swatch { width: 52px; height: 52px; border-radius: 8px; border: 2px solid transparent; font-size: 11px; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.15s; }
.theme-swatch:hover { transform: scale(1.05); }
.theme-swatch.active { border-color: #4f46e5; box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.3); }
</style>
