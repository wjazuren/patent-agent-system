/**
 * 专利相关状态管理
 * 管理当前生成状态、当前文档等跨页面共享的数据
 *
 * Pinia + TypeScript 最佳实践：
 * 1. 用 ref 定义 state（自动推导类型）
 * 2. 用 computed 定义 getters
 * 3. 用普通函数定义 actions
 * 4. 返回的所有东西都有完整的类型提示
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { PatentDocument, TokenUsage } from '@/types/patent'

export const usePatentStore = defineStore('patent', () => {
  // ========== State 状态定义 ==========

  /** 当前生成的请求ID */
  const currentRequestId = ref<string>('')

  /** 当前查看的文档ID */
  const currentDocumentId = ref<string>('')

  /** 生成是否进行中 */
  const isGenerating = ref<boolean>(false)

  /** 生成进度（0-5，对应6个Agent） */
  const currentStepIndex = ref<number>(0)

  /** 生成过程日志 */
  const processLogs = ref<string[]>([])

  /** 最后生成的文档数据 */
  const lastGeneratedDocument = ref<PatentDocument | null>(null)

  // ========== Getters 计算属性 ==========

  /** 是否有生成结果 */
  const hasResult = computed<boolean>(() => {
    return !!lastGeneratedDocument.value
  })

  /** 总Token消耗（计算属性示例） */
  const totalTokens = computed<number>(() => {
    const usage: TokenUsage | undefined = lastGeneratedDocument.value?.token_usage
    if (!usage) return 0
    return (
      usage.requirement_prompt + usage.requirement_completion +
      usage.search_prompt + usage.search_completion +
      usage.writer_prompt + usage.writer_completion +
      usage.compliance_prompt + usage.compliance_completion +
      usage.review_prompt + usage.review_completion
    )
  })

  // ========== Actions 方法定义 ==========

  /**
   * 开始生成
   * @param requestId 请求ID
   */
  function startGeneration(requestId: string): void {
    currentRequestId.value = requestId
    isGenerating.value = true
    currentStepIndex.value = 0
    processLogs.value = ['工作流启动']
    lastGeneratedDocument.value = null
  }

  /**
   * 更新生成进度
   * @param stepIndex 当前步骤索引
   * @param logs 新的日志列表（可选）
   */
  function updateProgress(stepIndex: number, logs?: string[]): void {
    currentStepIndex.value = stepIndex
    if (logs && logs.length > 0) {
      processLogs.value = [...logs]
    }
  }

  /**
   * 添加一条日志
   * @param log 日志内容
   */
  function addLog(log: string): void {
    processLogs.value.push(log)
  }

  /**
   * 生成完成
   * @param document 生成的文档数据
   */
  function finishGeneration(document: PatentDocument): void {
    isGenerating.value = false
    currentStepIndex.value = 6
    lastGeneratedDocument.value = document
    currentDocumentId.value = document.document_id
  }

  /**
   * 生成失败
   * @param errorMsg 错误信息
   */
  function failGeneration(errorMsg: string): void {
    isGenerating.value = false
    processLogs.value.push(`错误: ${errorMsg}`)
  }

  /**
   * 重置状态
   */
  function reset(): void {
    currentRequestId.value = ''
    currentDocumentId.value = ''
    isGenerating.value = false
    currentStepIndex.value = 0
    processLogs.value = []
    lastGeneratedDocument.value = null
  }

  // 返回所有状态和方法
  return {
    // state
    currentRequestId,
    currentDocumentId,
    isGenerating,
    currentStepIndex,
    processLogs,
    lastGeneratedDocument,
    // getters
    hasResult,
    totalTokens,
    // actions
    startGeneration,
    updateProgress,
    addLog,
    finishGeneration,
    failGeneration,
    reset
  }
})