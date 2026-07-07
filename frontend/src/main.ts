/**
 * 应用入口文件
 * 在这里注册所有全局插件：Vue、Pinia、Router、Element Plus等
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import type { Component } from 'vue'

import App from './App.vue'
import router from './router'

// 全局样式
import '@/assets/styles/global.scss'

// 创建Vue应用实例
const app = createApp(App)

// 注册Pinia状态管理
const pinia = createPinia()
app.use(pinia)

// 注册路由
app.use(router)

// 注册Element Plus组件库
app.use(ElementPlus)

// 全局注册Element Plus所有图标组件
// 这样在模板里可以直接用 <el-icon><Edit /></el-icon>
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component as Component)
}

// 挂载到DOM
app.mount('#app')