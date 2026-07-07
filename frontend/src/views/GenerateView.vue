<template>
  <!--
    生成页 - 系统核心页面
    用户输入技术方案，点击生成，实时展示多Agent进度
  -->
  <div class="generate-view">
    <div class="generate-container">
      <!-- 左侧：输入区 -->
      <div class="input-section">
        <div class="section-title">
          <el-icon><EditPen /></el-icon>
          <span>技术方案描述</span>
        </div>

        <div class="input-tip">
          <el-icon><InfoFilled /></el-icon>
          <span>请详细描述您的技术方案，包括技术领域、核心创新点、解决的问题、实现方式等。描述越详细，生成的交底书质量越高。</span>
        </div>

        <el-input
          v-model="userInput"
          type="textarea"
          :rows="12"
          placeholder="例如：我想申请一个关于多智能体协同的专利，主要是用多个AI Agent分工合作来完成复杂任务..."
          maxlength="5000"
          show-word-limit
          :disabled="patentStore.isGenerating"
        />

        <!-- 快捷示例按钮 -->
        <div class="example-buttons">
          <span class="example-label">快速填充示例：</span>
          <el-button
            v-for="example in examples"
            :key="example.title"
            size="small"
            type="primary"
            plain
            @click="fillExample(example.content)"
            :disabled="patentStore.isGenerating"
          >
            {{ example.title }}
          </el-button>
        </div>

        <!-- 生成按钮 -->
        <div class="generate-btn-area">
          <el-button
            type="primary"
            size="large"
            :loading="patentStore.isGenerating"
            :disabled="!canGenerate"
            @click="handleGenerate"
          >
            <el-icon><MagicStick /></el-icon>
            <span>{{ patentStore.isGenerating ? '生成中...' : '生成专利交底书' }}</span>
          </el-button>

          <el-button
            v-if="patentStore.isGenerating"
            size="large"
            @click="handleReset"
          >
            重新生成
          </el-button>
        </div>
      </div>

      <!-- 右侧：进度展示区 -->
      <div class="progress-section">
        <!-- 未生成时显示占位 -->
        <div v-if="!patentStore.isGenerating && !patentStore.hasResult" class="empty-state">
          <el-empty description="输入技术方案后点击生成">
            <template #image>
              <el-icon :size="80" color="#dcdfe6">
                <DocumentAdd />
              </el-icon>
            </template>
          </el-empty>
        </div>

        <!-- 生成中：展示Agent进度 -->
        <AgentProgress
          v-if="patentStore.isGenerating"
          :current-step-index="patentStore.currentStepIndex"
          :is-finished="false"
          :logs="patentStore.processLogs"
        />

        <!-- 生成完成：展示结果摘要 -->
        <div v-if="patentStore.hasResult && !patentStore.isGenerating" class="result-summary">
          <div class="result-header">
            <el-icon class="success-icon"><CircleCheckFilled /></el-icon>
            <span class="result-title">生成完成！</span>
          </div>

          <div class="result-info">
            <div class="info-item">
              <span class="label">发明名称：</span>
              <span class="value text-ellipsis">{{ patentStore.lastGeneratedDocument?.title }}</span>
            </div>
            <div class="info-item">
              <span class="label">风险等级：</span>
              <RiskTag :level="patentStore.lastGeneratedDocument?.risk_level || 'low'" />
            </div>
            <div class="info-item">
              <span class="label">迭代次数：</span>
              <span class="value">{{ patentStore.lastGeneratedDocument?.iteration_count || 0 }} 轮</span>
            </div>
          </div>

          <div class="result-actions">
            <el-button type="primary" @click="goToDetail">
              查看完整文档
              <el-icon><ArrowRight /></el-icon>
            </el-button>
            <el-button @click="handleReset">
              重新生成
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 生成页逻辑
 * 核心功能：
 * 1. 接收用户输入
 * 2. 调用后端生成接口
 * 3. 模拟/展示生成进度
 * 4. 生成完成后跳转详情页
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { usePatentStore } from '@/stores/patent'
import { generatePatent } from '@/api/patent'
import AgentProgress from '@/components/AgentProgress.vue'
import RiskTag from '@/components/RiskTag.vue'
import type { PatentDocument } from '@/types/patent'

const router = useRouter()
const patentStore = usePatentStore()

// ========== 示例数据类型 ==========
interface ExampleItem {
  title: string
  content: string
}

// 用户输入
const userInput = ref<string>('')

// 是否可以点击生成（输入长度至少10个字）
const canGenerate = computed<boolean>(() => {
  return userInput.value.trim().length >= 10
})

// 快捷示例
const examples: ExampleItem[] = [
  {
    title: '多智能体系统',
    content: '我想申请一个关于多智能体协同的专利，主要是用多个AI Agent分工合作来完成复杂任务，每个Agent有不同的专业角色，比如有的负责检索，有的负责撰写，有的负责审核，通过调度器协调它们的工作，形成反馈闭环，提高输出质量。'
  },
  {
    title: '向量检索优化',
    content: '一种向量检索优化方法，通过对向量索引进行分层构建，结合查询向量的动态权重调整，在保证检索精度的同时大幅提升检索速度。适用于大规模向量数据库的快速检索场景。'
  },
  {
    title: '智能客服系统',
    content: '基于大语言模型的智能客服系统，支持多轮对话、意图识别、知识库检索和人工转接。系统能够自动理解用户问题，从企业知识库中检索相关内容，生成准确的回答，并对无法回答的问题自动转人工。'
  }
]

// 定时器ID（用于清理）
let simulateTimer: number | null = null

/**
 * 填充示例内容
 */
function fillExample(content: string): void {
  userInput.value = content
}

/**
 * 触发生成
 */
async function handleGenerate(): Promise<void> {
  if (!canGenerate.value) {
    ElMessage.warning('请输入至少10个字的技术方案描述')
    return
  }

  try {
    // 重置状态，开始生成
    patentStore.startGeneration('pending')

    // 模拟逐步推进的进度（提升用户体验）
    // 因为后端是同步返回，前端用定时器模拟Agent逐步执行的效果
    startSimulateProgress()

    // 调用后端接口
    const result = await generatePatent({
      user_input: userInput.value
    })

    // 停止模拟
    stopSimulateProgress()

    // 生成完成
    if (result.status === 'success' && result.document_id) {
      // 构造文档对象
      const document: PatentDocument = {
        document_id: result.document_id,
        title: result.document_id, // 详情页再取完整标题
        abstract: '',
        risk_level: result.risk_level,
        iteration_count: result.iteration_count,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        content: '',
        token_usage: result.token_usage
      }

      patentStore.finishGeneration(document)
      ElMessage.success('生成成功！')

      // 自动跳转到详情页
      setTimeout(() => {
        router.push(`/documents/${result.document_id}`)
      }, 1000)
    } else {
      patentStore.failGeneration(result.message || '生成失败')
      ElMessage.error(result.message || '生成失败')
    }
  } catch (error) {
    stopSimulateProgress()
    console.error('生成失败:', error)
    const errorMsg = error instanceof Error ? error.message : '网络错误'
    patentStore.failGeneration(errorMsg)
  }
}

/**
 * 开始模拟进度推进
 * 因为后端是一次性返回结果，前端用定时器模拟每个Agent的执行过程
 * 让用户能看到多Agent的工作流，提升感知
 */
function startSimulateProgress(): void {
  const steps: string[] = [
    '需求对接Agent正在解析技术方案...',
    '现有技术检索Agent正在检索对比专利...',
    '交底书撰写Agent正在生成初稿...',
    '合规校验Agent正在检查格式与法条...',
    '质量评审Agent正在进行综合评审...',
    '文档输出Agent正在生成最终文档...'
  ]

  let step: number = 0

  simulateTimer = window.setInterval(() => {
    if (step >= 5) {
      stopSimulateProgress()
      return
    }

    // 如果已经生成完成了，就不再模拟了
    if (!patentStore.isGenerating) {
      stopSimulateProgress()
      return
    }

    step++
    patentStore.updateProgress(step, [...steps.slice(0, step + 1)])
  }, 2000) // 每2秒推进一个步骤
}

/**
 * 停止模拟
 */
function stopSimulateProgress(): void {
  if (simulateTimer !== null) {
    clearInterval(simulateTimer)
    simulateTimer = null
  }
}

/**
 * 重置，重新生成
 */
function handleReset(): void {
  stopSimulateProgress()
  patentStore.reset()
}

/**
 * 跳转到详情页
 */
function goToDetail(): void {
  if (patentStore.currentDocumentId) {
    router.push(`/documents/${patentStore.currentDocumentId}`)
  }
}
</script>

<style lang="scss" scoped>
@import '@/assets/styles/variables.scss';

.generate-view {
  width: 100%;
}

.generate-container {
  display: flex;
  gap: 20px;
  height: calc(100vh - #{$header-height} - 80px);
}

// 左侧输入区
.input-section {
  flex: 1;
  background: #fff;
  border-radius: $border-radius-lg;
  padding: 24px;
  box-shadow: $shadow-sm;
  display: flex;
  flex-direction: column;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 12px;
}

.input-tip {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 10px 12px;
  background: #ecf5ff;
  border-radius: $border-radius-sm;
  color: $text-secondary;
  font-size: 13px;
  margin-bottom: 16px;
  line-height: 1.6;

  .el-icon {
    color: $primary-color;
    flex-shrink: 0;
    margin-top: 2px;
  }
}

.example-buttons {
  margin-top: 12px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;

  .example-label {
    font-size: 13px;
    color: $text-secondary;
    margin-right: 4px;
  }
}

.generate-btn-area {
  margin-top: auto;
  padding-top: 20px;
  display: flex;
  gap: 12px;
  justify-content: center;
}

// 右侧进度区
.progress-section {
  width: 420px;
  flex-shrink: 0;
}

.empty-state {
  background: #fff;
  border-radius: $border-radius-lg;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: $shadow-sm;
}

// 生成结果
.result-summary {
  background: #fff;
  border-radius: $border-radius-lg;
  padding: 24px;
  box-shadow: $shadow-sm;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;

  .success-icon {
    font-size: 28px;
    color: $success-color;
  }

  .result-title {
    font-size: 18px;
    font-weight: 600;
    color: $text-primary;
  }
}

.result-info {
  .info-item {
    display: flex;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid $border-color-lighter;

    .label {
      color: $text-secondary;
      width: 80px;
      flex-shrink: 0;
    }

    .value {
      flex: 1;
      color: $text-primary;
    }
  }
}

.result-actions {
  margin-top: 20px;
  display: flex;
  gap: 12px;
  justify-content: center;
}
</style>