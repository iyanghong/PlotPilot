import { createRouter, createWebHistory } from 'vue-router'
import { readerRoutes } from '@/reader'

const Home = () => import('../views/Home.vue')
const Workbench = () => import('../views/Workbench.vue')
const Chapter = () => import('../views/Chapter.vue')
const Cast = () => import('../views/Cast.vue')
const CharacterGraph = () => import('../views/CharacterGraph.vue')
const LocationGraph = () => import('../views/LocationGraph.vue')
const CharacterSchedulerSimulator = () =>
  import('../components/debug/CharacterSchedulerSimulator.vue')
const LoginView = () => import('../views/LoginView.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'Login', component: LoginView, meta: { guest: true } },
    { path: '/', name: 'Home', component: Home },
    { path: '/book/:slug/workbench', name: 'Workbench', component: Workbench },
    { path: '/book/:slug/cast', name: 'Cast', component: Cast },
    { path: '/book/:slug/chapter/:id', name: 'Chapter', component: Chapter },
    { path: '/book/:slug/characters', name: 'CharacterGraph', component: CharacterGraph },
    { path: '/book/:slug/location-graph', name: 'LocationGraph', component: LocationGraph },
    {
      path: '/debug/scheduler',
      name: 'CharacterSchedulerSimulator',
      component: CharacterSchedulerSimulator,
    },
    ...readerRoutes,
  ],
})

export default router

// ── 路由守卫：RBAC 认证检查 ──

import { useAuthStore } from '@/stores/authStore'

router.beforeEach(async (to, _from, next) => {
  // 登录页始终允许
  if (to.meta.guest) {
    return next()
  }

  const authStore = useAuthStore()

  // 等待认证初始化完成（main.ts 中异步调用 checkAuth）
  if (!authStore.initialized) {
    await authStore.checkAuth()
  }

  // web 模式且未认证 → 跳转登录页
  if (authStore.needsLogin) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }

  next()
})
