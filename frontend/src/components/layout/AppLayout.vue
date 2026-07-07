<template>
  <!--
    整体布局组件
    结构：顶部栏 + 侧边栏 + 主内容区
    所有页面都嵌套在这个布局里面
  -->
  <div class="app-layout">
    <!-- 顶部栏 -->
    <AppHeader />

    <div class="layout-body">
      <!-- 侧边栏 -->
      <AppSidebar />

      <!-- 主内容区 -->
      <div class="main-content">
        <!-- 面包屑导航 -->
        <el-breadcrumb class="breadcrumb" separator="/">
          <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
          <el-breadcrumb-item v-if="!$route.meta?.hideInBreadcrumb">
            {{ $route.meta?.title }}
          </el-breadcrumb-item>
        </el-breadcrumb>

        <!-- 页面内容，由路由渲染 -->
        <div class="page-container">
          <router-view v-slot="{ Component }">
            <transition name="fade">
              <component :is="Component" :key="$route.fullPath" />
            </transition>
          </router-view>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 布局组件逻辑
 * 这里只是组合子组件，没有太多业务逻辑
 */
import AppHeader from './Header.vue'
import AppSidebar from './Sidebar.vue'
</script>

<style lang="scss" scoped>
@import '@/assets/styles/variables.scss';

.app-layout {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.layout-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.main-content {
  flex: 1;
  // 内容区可滚动
  overflow-y: auto;
  padding: $content-padding;
  background: $bg-page;
}

.breadcrumb {
  margin-bottom: 16px;
}

.page-container {
  min-height: calc(100% - 40px); // 减去面包屑高度
}

// 页面切换淡入淡出动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>