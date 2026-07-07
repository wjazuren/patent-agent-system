/**
 * 路由配置
 * 定义所有页面的路由规则
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

// 路由配置数组
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    // 重定向到生成页（首页）
    redirect: '/generate'
  },
  {
    path: '/generate',
    name: 'Generate',
    component: () => import('@/views/GenerateView.vue'),
    meta: {
      title: '生成交底书',
      // 是否需要在侧边栏高亮
      activeMenu: '/generate'
    }
  },
  {
    path: '/documents',
    name: 'DocumentList',
    component: () => import('@/views/DocumentList.vue'),
    meta: {
      title: '文档管理',
      activeMenu: '/documents'
    }
  },
  {
    path: '/documents/:id',
    name: 'DocumentDetail',
    component: () => import('@/views/DocumentDetail.vue'),
    meta: {
      title: '文档详情',
      activeMenu: '/documents',
      hideInBreadcrumb: false
    }
  },
  {
    path: '/stats',
    name: 'Stats',
    component: () => import('@/views/StatsView.vue'),
    meta: {
      title: '数据统计',
      activeMenu: '/stats'
    }
  },
  {
    // 404页面
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: {
      title: '页面不存在'
    }
  }
]

// 创建路由实例
const router = createRouter({
  // 使用HTML5 history模式（URL更美观，没有#）
  history: createWebHistory(),
  routes
})

// 路由守卫：每次路由跳转前执行
router.beforeEach((to, _from, next) => {
  // 设置页面标题
  const pageTitle = to.meta?.title as string | undefined
  if (pageTitle) {
    document.title = `${pageTitle} - ${import.meta.env.VITE_APP_TITLE}`
  } else {
    document.title = import.meta.env.VITE_APP_TITLE
  }
  next()
})

export default router