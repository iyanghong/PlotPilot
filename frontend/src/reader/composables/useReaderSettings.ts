// frontend/src/reader/composables/useReaderSettings.ts
import { reactive, watch } from 'vue'
import { type ReaderSettings, defaultReaderSettings } from '../types'

const STORAGE_KEY_PREFIX = 'plotpilot-reader-settings'

function load(novelId: string): ReaderSettings {
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}-${novelId}`)
    if (raw) {
      const parsed = JSON.parse(raw)
      return { ...defaultReaderSettings(), ...parsed }
    }
  } catch {
    // localStorage 不可用或数据损坏
  }
  return defaultReaderSettings()
}

function save(novelId: string, settings: ReaderSettings): void {
  try {
    localStorage.setItem(`${STORAGE_KEY_PREFIX}-${novelId}`, JSON.stringify(settings))
  } catch {
    // localStorage 满或不可用，静默降级
  }
}

/** 将 ReaderSettings 转为 CSS 变量对象 */
export function settingsToCSSVars(settings: ReaderSettings): Record<string, string> {
  const fontFamilyMap: Record<string, string> = {
    system: 'system-ui, -apple-system, sans-serif',
    serif: 'KaiTi, STKaiti, "Noto Serif CJK SC", "Source Han Serif SC", serif',
    kai: 'KaiTi, STKaiti, serif',
    hei: '"Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif',
  }
  const themeMap: Record<string, { bg: string; text: string }> = {
    day: { bg: '#fafafa', text: '#1a1a1a' },
    night: { bg: '#1a1a1a', text: '#c8c8c8' },
    parchment: { bg: '#f5f0e8', text: '#3d2e22' },
    green: { bg: '#e8f0e3', text: '#2d3a25' },
  }
  const theme = themeMap[settings.theme] || themeMap.day
  return {
    '--reader-font-size': `${settings.fontSize}px`,
    '--reader-line-height': String(settings.lineHeight),
    '--reader-paragraph-spacing': settings.paragraphSpacing,
    '--reader-margin-width': `${settings.marginWidth}px`,
    '--reader-bg': theme.bg,
    '--reader-text': theme.text,
    '--reader-font-family': fontFamilyMap[settings.fontFamily] || fontFamilyMap.system,
  }
}

export function useReaderSettings(novelId: string) {
  const settings = reactive<ReaderSettings>(load(novelId))

  const cssVars = () => settingsToCSSVars(settings)

  watch(
    () => settings,
    (val) => {
      save(novelId, { ...val })
    },
    { deep: true }
  )

  function resetSettings() {
    Object.assign(settings, defaultReaderSettings())
  }

  return { settings, cssVars, resetSettings }
}
