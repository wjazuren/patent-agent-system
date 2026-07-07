<template>
  <!--
    侧边栏导航组件
    展示系统菜单，点击切换页面
  -->
  <div class="sidebar">
    <!-- Logo区域 -->
    <div class="logo">
      <el-icon :size="24" color="#409eff">
        <Document />
      </el-icon>
      <span class="logo-text">专利智能助手</span>
    </div>

    <!-- 导航菜单 -->
    <el-menu
      :default-active="activeMenu"
      class="sidebar-menu"
      background-color="#001529"
      text-color="#ffffffa6"
      active-text-color="#ffffff"
      router
    >
      <!-- 生成页 -->
      <el-menu-item index="/generate">
        <el-icon><EditPen /></el-icon>
        <span>生成交底书</span>
      </el-menu-item>

      <!-- 文档管理 -->
      <el-menu-item index="/documents">
        <el-icon><Files /></el-icon>
        <span>文档管理</span>
      </el-menu-item>

      <!-- 数据统计 -->
      <el-menu-item index="/stats">
        <el-icon><DataAnalysis /></el-icon>
        <span>数据统计</span>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<script setup lang="ts">
/**
 * 侧边栏逻辑
 * 根据当前路由高亮对应的菜单项
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

// 当前激活的菜单，从路由meta中取
// 详情页也高亮文档管理菜单
const activeMenu = computed<string>(() => {
  return (route.meta?.activeMenu as string) || route.path
})
</script>

<style lang="scss" scoped>
@import '@/assets/styles/variables.scss';

.sidebar {
  width: $sidebar-width;
  height: 100%;
  background: #001529; // 深蓝黑背景，专业感
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.logo {
  height: $header-height;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);

  .logo-text {
    color: #fff;
    font-size: 16px;
    font-weight: 600;
    letter-spacing: 1px;
  }
}

.sidebar-menu {
  flex: 1;
  border-right: none;

  // 菜单项高度
  :deep(.el-menu-item) {
    height: 50px;
    line-height: 50px;

    &:hover {
      background: rgba(255, 255, 255, 0.08);
    }
  }

  // 激活项背景
  :deep(.el-menu-item.is-active) {
    background: $primary-color;
  }
}
</style>