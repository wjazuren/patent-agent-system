<template>
  <!--
    多Agent生成进度展示组件
    实时展示每个Agent的执行状态，让用户感知多Agent协同过程
    这是前端最有特色的交互之一，体现多Agent的价值
  -->
  <div class="agent-progress">
    <!-- 总进度条 -->
    <div class="progress-header">
      <span class="progress-title">多智能体协同生成中</span>
      <span class="progress-text">{{ currentStep }}/{{ totalSteps }}</span>
    </div>
    <el-progress
      :percentage="progressPercent"
      :status="isFinished ? 'success' : ''"
      :stroke-width="8"
    />

    <!-- Agent执行状态流 -->
    <div class="agent-steps">
      <div
        v-for="(agent, index) in agentList"
        :key="agent.key"
        class="agent-step"
        :class="{
          'is-done': agent.status === 'done',
          'is-running': agent.status === 'running',
          'is-pending': agent.status === 'pending'
        }"
      >
        <!-- 步骤图标 -->
        <div class="step-icon">
          <el-icon v-if="agent.status === 'done'" class="icon-done">
            <CircleCheck />
          </el-icon>
          <el-icon v-else-if="agent.status === 'running'" class="icon-running">
            <Loading />
          </el-icon>
          <span v-else class="icon-number">{{ index + 1 }}</span>
        </div>

        <!-- 步骤信息 -->
        <div class="step-info">
          <div class="step-name">{{ agent.name }}</div>
          <div class="step-desc">{{ agent.description }}</div>
        </div>

        <!-- 连接线 -->
        <div v-if="index < agentList.length - 1" class="step-line"></div>
      </div>
    </div>

    <!-- 当前操作日志 -->
    <div v-if="logs.length > 0" class="process-logs">
      <div class="logs-title">
        <el-icon><List /></el-icon>
        <span>执行日志</span>
      </div>
      <div class="logs-content">
        <div
          v-for="(log, index) in logs"
          :key="index"
          class="log-item"
        >
          <span class="log-dot"></span>
          <span>{{ log }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Agent进度组件逻辑
 * 根据传入的状态数据，展示每个Agent的执行情况
 */
import { computed } from 'vue'
import { AGENT_LIST, TOTAL_AGENT_COUNT } from '@/utils/constants'
import type { AgentStatus } from '@/types/common'

// 定义props - TS泛型语法
const props = defineProps<{
  /** 当前步骤索引（从0开始） */
  currentStepIndex: number
  /** 是否完成 */
  isFinished: boolean
  /** 执行日志列表 */
  logs: string[]
}>()

// Agent信息类型
interface AgentInfo {
  key: string
  name: string
  description: string
  status: AgentStatus
}

// Agent列表 - 从常量映射，加上状态
const agentList = computed<AgentInfo[]>(() => {
  return AGENT_LIST.map((agent, index) => ({
    ...agent,
    status: getStatus(index)
  }))
})

// 总步骤数
const totalSteps: number = TOTAL_AGENT_COUNT

// 当前步骤（显示用，从1开始）
const currentStep = computed<number>(() => {
  if (props.isFinished) return totalSteps
  return props.currentStepIndex + 1
})

// 进度百分比
const progressPercent = computed<number>(() => {
  if (props.isFinished) return 100
  return Math.round((props.currentStepIndex / totalSteps) * 100)
})

/**
 * 根据索引判断状态
 * @param index Agent索引
 * @returns Agent状态
 */
function getStatus(index: number): AgentStatus {
  if (props.isFinished) return 'done'
  if (index < props.currentStepIndex) return 'done'
  if (index === props.currentStepIndex) return 'running'
  return 'pending'
}
</script>

<style lang="scss" scoped>
@import '@/assets/styles/variables.scss';

.agent-progress {
  background: #fff;
  border-radius: $border-radius-lg;
  padding: 24px;
  box-shadow: $shadow-sm;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;

  .progress-title {
    font-size: 16px;
    font-weight: 600;
    color: $text-primary;
  }

  .progress-text {
    font-size: 14px;
    color: $text-secondary;
  }
}

// Agent步骤流
.agent-steps {
  margin-top: 24px;
  position: relative;
}

.agent-step {
  display: flex;
  align-items: flex-start;
  position: relative;
  padding-bottom: 20px;

  &:last-child {
    padding-bottom: 0;

    .step-line {
      display: none;
    }
  }
}

.step-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  z-index: 1;
  background: $border-color-lighter;
  color: $text-placeholder;
  font-size: 14px;
  font-weight: 500;

  .icon-done {
    color: $success-color;
    font-size: 20px;
  }

  .icon-running {
    color: $primary-color;
    font-size: 20px;
    animation: spin 1s linear infinite;
  }
}

// 已完成状态
.is-done .step-icon {
  background: rgba(103, 194, 58, 0.1);
}

// 进行中状态
.is-running .step-icon {
  background: rgba(64, 158, 255, 0.1);
}

.step-info {
  flex: 1;
  margin-left: 12px;
  padding-top: 4px;

  .step-name {
    font-size: 14px;
    font-weight: 500;
    color: $text-primary;
  }

  .step-desc {
    font-size: 12px;
    color: $text-placeholder;
    margin-top: 2px;
  }
}

// 已完成的文字变灰
.is-done .step-info .step-name {
  color: $text-secondary;
}

// 进行中的文字高亮
.is-running .step-info .step-name {
  color: $primary-color;
  font-weight: 600;
}

// 步骤连接线
.step-line {
  position: absolute;
  left: 15px;
  top: 32px;
  bottom: 0;
  width: 2px;
  background: $border-color-lighter;
}

.is-done .step-line {
  background: $success-color;
}

// 旋转动画
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

// 执行日志
.process-logs {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid $border-color-lighter;

  .logs-title {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 14px;
    font-weight: 500;
    color: $text-secondary;
    margin-bottom: 10px;
  }

  .logs-content {
    background: $bg-page;
    border-radius: $border-radius-sm;
    padding: 12px;
    max-height: 150px;
    overflow-y: auto;
    font-size: 12px;
    color: $text-secondary;
    font-family: 'Consolas', monospace;
  }

  .log-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 3px 0;

    .log-dot {
      width: 4px;
      height: 4px;
      border-radius: 50%;
      background: $primary-color;
      flex-shrink: 0;
    }
  }
}
</style>