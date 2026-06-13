<template>
  <canvas
    ref="canvasRef"
    class="page-flip-canvas"
    @mousedown="onPointerDown"
    @mousemove="onPointerMove"
    @mouseup="onPointerUp"
    @mouseleave="onPointerUp"
    @touchstart.prevent="onTouchStart"
    @touchmove.prevent="onTouchMove"
    @touchend="onPointerUp"
  />
</template>

<script setup lang="ts">
/**
 * PageFlipCanvas — Canvas 仿真翻页组件
 * @author Axelton
 */
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import type { ReaderSettings } from '../types'

const props = defineProps<{
  content: string
  settings: ReaderSettings
  /** 当前章节号（用于章末翻页判断） */
  isLastChapter: boolean
}>()

const emit = defineEmits<{
  /** 翻到上一章 */
  'prev-chapter': []
  /** 翻到下一章 */
  'next-chapter': []
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)

// ---- 分页状态 ----
/** 每页文本行数组 */
const pages = ref<string[][]>([])
/** 当前页码（0-based） */
const currentPage = ref(0)
/** 显示两页展开（桌面端） */
const showSpread = ref(true)

// ---- 交互状态 ----
const isDragging = ref(false)
const dragX = ref(0)
const dragY = ref(0)
/** 翻页方向：1=向前（从右翻），-1=向后（从左翻） */
const flipDirection = ref(0)
/** 卷曲进度 0~1，1 表示完全翻过 */
const curlProgress = ref(0)
/** 是否为自动动画中 */
const isAnimating = ref(false)

// ---- 尺寸 ----
let canvasWidth = 0
let canvasHeight = 0
let pageWidth = 0
let pageHeight = 0
/** 页边距 */
const PADDING = 32
/** 翻页阈值 */
const FLIP_THRESHOLD = 0.35

// ---- 离屏 canvas 用于文本测量 ----
let measureCtx: CanvasRenderingContext2D | null = null

// ---- 动画 ----
let animFrameId = 0
let animStartTime = 0
let animFromProgress = 0
let animToProgress = 0
const ANIM_DURATION = 400 // ms

/** 获取字体描述字符串 */
function getFontString(): string {
  const fontMap: Record<string, string> = {
    system: 'system-ui, -apple-system, sans-serif',
    serif: 'KaiTi, STKaiti, "Noto Serif CJK SC", serif',
    kai: 'KaiTi, STKaiti, serif',
    hei: '"Microsoft YaHei", "PingFang SC", sans-serif',
  }
  const family = fontMap[props.settings.fontFamily] || fontMap.system
  return `${props.settings.fontSize}px ${family}`
}

/** 测量行高 */
function getLineHeight(): number {
  return props.settings.fontSize * props.settings.lineHeight
}

/** 将段落文本按宽度折行 */
function wrapText(text: string, maxWidth: number): string[] {
  if (!measureCtx) return [text]
  const lines: string[] = []
  // 首行缩进 2em
  const firstIndent = props.settings.fontSize * 2
  let isFirstLine = true

  for (const paragraph of text.split('\n')) {
    const trimmed = paragraph.trim()
    if (!trimmed) {
      lines.push('')
      continue
    }
    const indent = isFirstLine ? firstIndent : 0
    let currentLine = ''
    for (const char of trimmed) {
      const testLine = currentLine + char
      const width = measureCtx.measureText(testLine).width + indent
      if (width > maxWidth && currentLine.length > 0) {
        lines.push(currentLine)
        currentLine = char
      } else {
        currentLine = testLine
      }
    }
    if (currentLine) lines.push(currentLine)
    isFirstLine = false
  }
  return lines
}

/** 分割内容为多页 */
function paginateContent(): void {
  const canvas = canvasRef.value
  if (!canvas || !measureCtx) return

  const font = getFontString()
  measureCtx.font = font
  const lineHeight = getLineHeight()
  const usableWidth = pageWidth - PADDING * 2
  const usableHeight = pageHeight - PADDING * 2
  const maxLinesPerPage = Math.floor(usableHeight / lineHeight)

  const allLines = wrapText(props.content, usableWidth)

  const result: string[][] = []
  for (let i = 0; i < allLines.length; i += maxLinesPerPage) {
    result.push(allLines.slice(i, i + maxLinesPerPage))
  }

  pages.value = result.length > 0 ? result : [[]]
  currentPage.value = 0
}

/** 设置 canvas 尺寸 */
function resizeCanvas(): void {
  const canvas = canvasRef.value
  if (!canvas) return

  const parent = canvas.parentElement
  if (!parent) return

  const rect = parent.getBoundingClientRect()
  const dpr = window.devicePixelRatio || 1

  canvasWidth = rect.width
  canvasHeight = rect.height
  canvas.width = canvasWidth * dpr
  canvas.height = canvasHeight * dpr
  canvas.style.width = canvasWidth + 'px'
  canvas.style.height = canvasHeight + 'px'

  const ctx = canvas.getContext('2d')
  if (ctx) ctx.scale(dpr, dpr)

  // 更新页面尺寸
  showSpread.value = canvasWidth > 700
  pageWidth = showSpread.value ? canvasWidth / 2 : canvasWidth
  pageHeight = canvasHeight

  paginateContent()
}

// ---- 渲染 ----

/** 绘制单页内容 */
function drawPage(ctx: CanvasRenderingContext2D, pageIndex: number, offsetX: number): void {
  if (pageIndex < 0 || pageIndex >= pages.value.length) return

  const lines = pages.value[pageIndex]
  const bgColor = getBgColor()
  const textColor = getTextColor()
  const font = getFontString()
  const lineHeight = getLineHeight()

  // 背景
  ctx.fillStyle = bgColor
  ctx.fillRect(offsetX, 0, pageWidth, pageHeight)

  // 文字
  ctx.fillStyle = textColor
  ctx.font = font
  ctx.textBaseline = 'top'
  const startY = PADDING

  for (let i = 0; i < lines.length; i++) {
    const indent = i === 0 ? props.settings.fontSize * 2 : 0
    ctx.fillText(lines[i], offsetX + PADDING + indent, startY + i * lineHeight)
  }

  // 页码
  ctx.fillStyle = '#999'
  ctx.font = `${props.settings.fontSize * 0.75}px system-ui`
  ctx.textAlign = 'center'
  ctx.fillText(`${pageIndex + 1} / ${pages.value.length}`, offsetX + pageWidth / 2, pageHeight - 24)
  ctx.textAlign = 'start'
}

/** 绘制卷曲阴影（沿折线渐变） */
function drawCurlShadow(
  ctx: CanvasRenderingContext2D,
  x1: number, y1: number, x2: number, y2: number,
  direction: number
): void {
  // 折线一侧的渐变阴影
  ctx.save()
  ctx.beginPath()
  if (direction > 0) {
    // 向前翻：折线从右下角
    ctx.moveTo(x1, y1)
    ctx.lineTo(x2, y2)
    ctx.lineTo(x2, pageHeight)
    ctx.lineTo(pageWidth, pageHeight)
    ctx.lineTo(pageWidth, 0)
  } else {
    // 向后翻：折线从左下角
    ctx.moveTo(x1, y1)
    ctx.lineTo(x2, y2)
    ctx.lineTo(x2, pageHeight)
    ctx.lineTo(0, pageHeight)
    ctx.lineTo(0, 0)
  }
  ctx.closePath()
  ctx.clip()

  // 线性渐变模拟折痕阴影
  const grad = ctx.createLinearGradient(x1, y1, x2, y2)
  grad.addColorStop(0, 'rgba(0,0,0,0.25)')
  grad.addColorStop(0.5, 'rgba(0,0,0,0.08)')
  grad.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.fillStyle = grad
  ctx.fillRect(0, 0, pageWidth, pageHeight)
  ctx.restore()
}

/** 绘制卷曲区域下面的下一页内容 */
function drawNextPageUnderCurl(
  ctx: CanvasRenderingContext2D,
  x1: number, y1: number, x2: number, y2: number,
  direction: number
): void {
  const nextPageIdx = currentPage.value + (direction > 0 ? 1 : -1)
  if (nextPageIdx < 0 || nextPageIdx >= pages.value.length) return

  ctx.save()
  ctx.beginPath()
  if (direction > 0) {
    ctx.moveTo(x1, y1)
    ctx.lineTo(x2, y2)
    ctx.lineTo(x2, pageHeight)
    ctx.lineTo(pageWidth, pageHeight)
    ctx.lineTo(pageWidth, 0)
  } else {
    ctx.moveTo(x1, y1)
    ctx.lineTo(x2, y2)
    ctx.lineTo(x2, pageHeight)
    ctx.lineTo(0, pageHeight)
    ctx.lineTo(0, 0)
  }
  ctx.closePath()
  ctx.clip()

  drawPage(ctx, nextPageIdx, 0)
  ctx.restore()
}

/** 主渲染函数 */
function render(): void {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.clearRect(0, 0, canvasWidth, canvasHeight)

  // 绘制背景
  ctx.fillStyle = getBgColor()
  ctx.fillRect(0, 0, canvasWidth, canvasHeight)

  if (pages.value.length === 0) return

  const cp = currentPage.value

  if (showSpread.value && cp + 1 < pages.value.length) {
    // 双页展开：左页 = cp，右页 = cp+1
    drawPage(ctx, cp, 0)
    drawPage(ctx, cp + 1, pageWidth)
  } else if (showSpread.value) {
    // 最后一页单页
    drawPage(ctx, cp, 0)
  } else {
    // 单页模式
    drawPage(ctx, cp, 0)
  }

  // 卷曲效果
  if (isDragging.value && flipDirection.value !== 0 && curlProgress.value > 0) {
    const dir = flipDirection.value
    const progress = curlProgress.value

    // 折线端点：从拖动点向对边延伸
    let foldStartX: number, foldStartY: number
    let foldEndX: number, foldEndY: number

    if (dir > 0) {
      // 向前翻（从右）：折线从右下向左边延伸
      foldStartX = pageWidth
      foldStartY = pageHeight
      foldEndX = pageWidth * (1 - progress)
      foldEndY = 0
    } else {
      // 向后翻（从左）：折线从左下向右边延伸
      foldStartX = 0
      foldStartY = pageHeight
      foldEndX = pageWidth * progress
      foldEndY = 0
    }

    // 下一层：卷曲下的内容
    drawNextPageUnderCurl(ctx, foldStartX, foldStartY, foldEndX, foldEndY, dir)
    // 阴影层
    drawCurlShadow(ctx, foldStartX, foldStartY, foldEndX, foldEndY, dir)
  }
}

/** 获取主题背景色 */
function getBgColor(): string {
  const themeMap: Record<string, string> = {
    day: '#fafafa',
    night: '#1a1a1a',
    parchment: '#f5f0e8',
    green: '#e8f0e3',
  }
  return themeMap[props.settings.theme] || '#fafafa'
}

/** 获取主题文字色 */
function getTextColor(): string {
  const themeMap: Record<string, string> = {
    day: '#1a1a1a',
    night: '#c8c8c8',
    parchment: '#3d2e22',
    green: '#2d3a25',
  }
  return themeMap[props.settings.theme] || '#1a1a1a'
}

// ---- 动画循环 ----
function startAnimLoop(): void {
  function loop() {
    if (isAnimating.value) {
      const elapsed = Date.now() - animStartTime
      const t = Math.min(elapsed / ANIM_DURATION, 1)
      // easeInOutCubic
      const eased = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
      curlProgress.value = animFromProgress + (animToProgress - animFromProgress) * eased
      render()
      if (t >= 1) {
        finishFlip()
      }
    }
    if (!isDragging.value && !isAnimating.value) {
      render()
    }
    animFrameId = requestAnimationFrame(loop)
  }
  animFrameId = requestAnimationFrame(loop)
}

/** 完成翻页 */
function finishFlip(): void {
  isAnimating.value = false

  if (curlProgress.value > FLIP_THRESHOLD) {
    // 翻页
    const dir = flipDirection.value
    const cp = currentPage.value
    const step = showSpread.value ? 2 : 1
    const newPage = cp + dir * step

    if (newPage < 0) {
      // 已是第一页，尝试翻到上一章
      emit('prev-chapter')
      currentPage.value = 0
    } else if (newPage >= pages.value.length) {
      // 已是最后一页
      if (props.isLastChapter) {
        currentPage.value = cp // 保持当前
      } else {
        emit('next-chapter')
        currentPage.value = 0
      }
    } else {
      currentPage.value = newPage
    }
  }

  curlProgress.value = 0
  flipDirection.value = 0
  render()
}

/** 开始自动翻页动画 */
function animateFlip(from: number, to: number, dir: number): void {
  animFromProgress = from
  animToProgress = to
  flipDirection.value = dir
  isAnimating.value = true
  animStartTime = Date.now()
}

// ---- 事件处理 ----
function getPos(e: MouseEvent | Touch): { x: number; y: number } {
  const canvas = canvasRef.value!
  const rect = canvas.getBoundingClientRect()
  return { x: e.clientX - rect.left, y: e.clientY - rect.top }
}

function onPointerDown(e: MouseEvent): void {
  if (isAnimating.value) return
  const { x, y } = getPos(e)
  const w = showSpread.value ? pageWidth * 2 : pageWidth
  dragX.value = x
  dragY.value = y

  // 判断方向：点击右侧 40% 区域为向前翻，左侧 40% 为向后翻
  if (x > w * 0.6) {
    flipDirection.value = 1
  } else if (x < w * 0.4) {
    flipDirection.value = -1
  } else {
    return
  }
  isDragging.value = true
  curlProgress.value = 0
}

function onPointerMove(e: MouseEvent): void {
  if (!isDragging.value || isAnimating.value) return
  const { x, y } = getPos(e)
  dragX.value = x
  dragY.value = y

  const w = showSpread.value ? pageWidth * 2 : pageWidth
  const dx = Math.abs(x - (flipDirection.value > 0 ? w : 0))
  curlProgress.value = Math.min(dx / (w * 0.8), 0.95)
  render()
}

function onPointerUp(): void {
  if (!isDragging.value) return
  isDragging.value = false

  if (curlProgress.value > FLIP_THRESHOLD) {
    animateFlip(curlProgress.value, 1, flipDirection.value)
  } else {
    animateFlip(curlProgress.value, 0, flipDirection.value)
  }
}

function onTouchStart(e: TouchEvent): void {
  if (isAnimating.value) return
  const touch = e.touches[0]
  if (!touch) return
  const { x, y } = getPos(touch)
  const w = showSpread.value ? pageWidth * 2 : pageWidth
  dragX.value = x
  dragY.value = y

  if (x > w * 0.6) {
    flipDirection.value = 1
  } else if (x < w * 0.4) {
    flipDirection.value = -1
  } else {
    return
  }
  isDragging.value = true
  curlProgress.value = 0
}

function onTouchMove(e: TouchEvent): void {
  if (!isDragging.value || isAnimating.value) return
  const touch = e.touches[0]
  if (!touch) return
  const { x, y } = getPos(touch)
  dragX.value = x
  dragY.value = y

  const w = showSpread.value ? pageWidth * 2 : pageWidth
  const dx = Math.abs(x - (flipDirection.value > 0 ? w : 0))
  curlProgress.value = Math.min(dx / (w * 0.8), 0.95)
  render()
}

// ---- 生命周期 ----
onMounted(async () => {
  await nextTick()
  // 创建测量 canvas
  const mCanvas = document.createElement('canvas')
  mCanvas.width = 800
  mCanvas.height = 100
  measureCtx = mCanvas.getContext('2d')

  resizeCanvas()
  startAnimLoop()
  window.addEventListener('resize', resizeCanvas)
})

onUnmounted(() => {
  cancelAnimationFrame(animFrameId)
  window.removeEventListener('resize', resizeCanvas)
})

// 设置变化时重新分页
watch(() => props.settings, () => {
  paginateContent()
}, { deep: true })

// 内容变化时重新分页
watch(() => props.content, () => {
  paginateContent()
})

/** 暴露翻页方法供外部调用（键盘导航等） */
defineExpose({
  /** 翻到上一页 */
  prevPage() {
    if (isAnimating.value || isDragging.value) return
    const cp = currentPage.value
    const step = showSpread.value ? 2 : 1
    if (cp <= 0) {
      emit('prev-chapter')
    } else {
      animateFlip(0, 1, -1)
      // 在动画完成时翻页
      const origCp = cp
      setTimeout(() => {
        if (currentPage.value === origCp) {
          currentPage.value = Math.max(0, cp - step)
        }
      }, ANIM_DURATION)
    }
  },
  /** 翻到下一页 */
  nextPage() {
    if (isAnimating.value || isDragging.value) return
    const cp = currentPage.value
    const step = showSpread.value ? 2 : 1
    if (cp + step >= pages.value.length) {
      if (!props.isLastChapter) {
        emit('next-chapter')
      }
    } else {
      animateFlip(0, 1, 1)
      const origCp = cp
      setTimeout(() => {
        if (currentPage.value === origCp) {
          currentPage.value = cp + step
        }
      }, ANIM_DURATION)
    }
  },
  /** 设置页码 */
  setPage(page: number) {
    currentPage.value = page
    paginateContent()
  },
})
</script>

<style scoped>
.page-flip-canvas {
  width: 100%;
  height: 100%;
  display: block;
  cursor: pointer;
  user-select: none;
  -webkit-user-select: none;
  touch-action: none;
}
</style>
