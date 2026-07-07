<template>
  <!--
    404页面
    用户访问不存在的路由时显示
  -->
  <div class="not-found">
    <div class="content">
      <h1 class="code">404</h1>
      <p class="title">页面不存在</p>
      <p class="desc">抱歉，您访问的页面不存在或已被删除</p>
      <el-button type="primary" @click="goHome">
        <el-icon><House /></el-icon>
        返回首页
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goHome(): void {
  router.push('/')
}
</script>

<style lang="scss" scoped>
@import '@/assets/styles/variables.scss';

.not-found {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: $bg-page;
}

.content {
  text-align: center;

  .code {
    font-size: 120px;
    font-weight: 700;
    color: $primary-color;
    line-height: 1;
    margin-bottom: 20px;
  }

  .title {
    font-size: 24px;
    font-weight: 600;
    color: $text-primary;
    margin-bottom: 12px;
  }

  .desc {
    font-size: 14px;
    color: $text-secondary;
    margin-bottom: 30px;
  }
}
</style>