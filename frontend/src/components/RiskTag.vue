<template>
  <!--
    风险等级标签组件
    根据风险等级显示不同颜色的标签
    在文档列表、详情页等多处复用
  -->
  <el-tag
    :type="tagType"
    :effect="effect"
    :size="size"
    class="risk-tag"
  >
    <el-icon class="tag-icon"><Warning /></el-icon>
    {{ riskText }}
  </el-tag>
</template>

<script setup lang="ts">
/**
 * 风险标签组件逻辑
 * 根据风险等级返回对应的显示文本和标签类型
 */
import { computed } from 'vue'
import type { RiskLevel } from '@/types/common'
import { RISK_LEVEL_TEXT } from '@/utils/constants'

// 定义props - TS泛型语法
interface Props {
  level: 'high' | 'medium' | 'low'
  size?: 'small' | 'default' | 'large'
  effect?: 'dark' | 'light' | 'plain'
}

const props = withDefaults(defineProps<Props>(), {
  size: 'default',
  effect: 'light'
})

// 显示文本
const riskText = computed<string>(() => {
  return RISK_LEVEL_TEXT[props.level] || '未知'
})

// Element Plus标签类型
type TagType = 'success' | 'warning' | 'danger' | 'info'

// 标签类型
const tagType = computed<TagType>(() => {
  const map: Record<RiskLevel, TagType> = {
    low: 'success',
    medium: 'warning',
    high: 'danger'
  }
  return map[props.level] || 'info'
})
</script>

<style lang="scss" scoped>
.risk-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;

  .tag-icon {
    font-size: 12px;
  }
}
</style>