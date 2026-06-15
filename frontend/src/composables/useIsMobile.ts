/** 移动端检测 composable
 *
 * 基于 matchMedia 响应式检测视口宽度，768px 以下为移动端。
 *
 * 作者: Axelton
 */
import { ref, onMounted, onUnmounted } from 'vue'

const MOBILE_BREAKPOINT = 768

/** 是否为移动端视图（< 768px） */
const isMobile = ref(false)

function check() {
  isMobile.value = window.innerWidth < MOBILE_BREAKPOINT
}

export function useIsMobile() {
  onMounted(() => {
    check()
    window.addEventListener('resize', check)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', check)
  })

  return { isMobile }
}
