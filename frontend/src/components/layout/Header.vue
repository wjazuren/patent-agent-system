<template>
  <!--
    顶部栏组件
    展示页面标题、用户信息等
  -->
  <div class="app-header">
    <div class="header-left">
      <span class="page-title">{{ currentPageTitle }}</span>
    </div>

    <div class="header-right">
      <!-- 系统状态指示 -->
      <el-tooltip content="系统运行正常" placement="bottom">
        <span class="status-dot"></span>
      </el-tooltip>

      <!-- 用户信息 -->
      <el-dropdown>
        <span class="user-info">
          <el-avatar :size="32" icon="UserFilled" />
          <span class="username">用户</span>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item>个人中心</el-dropdown-item>
            <el-dropdown-item divided>退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 顶部栏逻辑
 * 动态显示当前页面标题
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

// 当前页面标题
const currentPageTitle = computed<string>(() => {
  return (route.meta?.title as string) || '专利交底书系统'
})
</script>

<style lang="scss" scoped>
@import '@/assets/styles/variables.scss';

.app-header {
  height: $header-height;
  background: #fff;
  border-bottom: 1px solid $border-color-lighter;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: $shadow-sm;
  flex-shrink: 0;
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: $text-primary;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

// 系统状态点
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: $success-color;
  display: inline-block;
  box-shadow: 0 0 0 3px rgba(103, 194, 58, 0.2);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;

  .username {
    font-size: 14px;
    color: $text-secondary;
  }
}
</style>