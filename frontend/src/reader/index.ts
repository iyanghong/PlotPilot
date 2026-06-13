// frontend/src/reader/index.ts
import type { RouteRecordRaw } from 'vue-router'

/** 懒加载阅读器主视图 */
const ReaderView = () => import('./ReaderView.vue')

/** 阅读器路由：独立页面 + 可选章节号 */
export const readerRoutes: RouteRecordRaw[] = [
  {
    path: '/book/:slug/reader',
    name: 'Reader',
    component: ReaderView,
  },
  {
    path: '/book/:slug/reader/:chapterNum',
    name: 'ReaderChapter',
    component: ReaderView,
  },
]
