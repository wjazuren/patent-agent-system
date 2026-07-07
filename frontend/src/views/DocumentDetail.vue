<template>
  <!--
    文档详情页
    展示完整的专利交底书，支持预览、导出、复制
  -->
  <div class="document-detail">
    <!-- 加载中 -->
    <div v-if="loading" class="loading-wrap">
      <el-icon class="loading-icon" :size="40">
        <Loading />
      </el-icon>
      <p>加载中...</p>
    </div>

    <!-- 文档内容 -->
    <div v-else-if="docInfo" class="detail-container">
      <!-- 文档头部信息 -->
      <div class="doc-header">
        <div class="header-left">
          <el-button
            link
            @click="goBack"
            class="back-btn"
          >
            <el-icon><ArrowLeft /></el-icon>
            返回列表
          </el-button>
          <h1 class="doc-title">{{ docInfo.title }}</h1>
          <div class="doc-meta">
            <RiskTag :level="docInfo.risk_level" />
            <span class="meta-item">
              <el-icon><Clock /></el-icon>
              {{ formatDateTime(docInfo.created_at) }}
            </span>
            <span class="meta-item">
              <el-icon><RefreshRight /></el-icon>
              迭代 {{ docInfo.iteration_count || 0 }} 轮
            </span>
          </div>
        </div>

        <div class="header-right">
          <el-button @click="handleCopy">
            <el-icon><CopyDocument /></el-icon>
            复制内容
          </el-button>
          <el-button type="primary" @click="handleExport">
            <el-icon><Download /></el-icon>
            导出 Markdown
          </el-button>
        </div>
      </div>

      <!-- 文档正文 -->
      <div class="doc-content">
        <MarkdownRender :content="docInfo.content" />
      </div>

      <!-- Token统计（如果有的话） -->
      <div v-if="docInfo.token_usage" class="token-stats">
        <el-divider content-position="left">Token 消耗统计</el-divider>
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-label">总消耗</div>
            <div class="stat-value">{{ formatTokens(totalTokens) }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">需求对接</div>
            <div class="stat-value">{{ formatTokens(requirementTokens) }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">检索</div>
            <div class="stat-value">{{ formatTokens(searchTokens) }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">撰写</div>
            <div class="stat-value">{{ formatTokens(writerTokens) }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">合规校验</div>
            <div class="stat-value">{{ formatTokens(complianceTokens) }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">质量评审</div>
            <div class="stat-value">{{ formatTokens(reviewTokens) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 加载失败 -->
    <el-empty v-else description="文档加载失败" />
  </div>
</template>

<script setup lang="ts">
/**
 * 文档详情页逻辑
 */
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getDocument } from '@/api/patent'
import { formatDateTime, formatTokens } from '@/utils/format'
import MarkdownRender from '@/components/MarkdownRender.vue'
import RiskTag from '@/components/RiskTag.vue'
import type { PatentDocument, TokenUsage } from '@/types/patent'

const route = useRoute()
const router = useRouter()

// 加载状态
const loading = ref<boolean>(true)
// 文档数据
const docInfo = ref<PatentDocument | null>(null)

// ========== Token统计计算 ==========
const tokenUsage = computed<TokenUsage | undefined>(() => {
  return docInfo.value?.token_usage
})

const requirementTokens = computed<number>(() => {
  const t = tokenUsage.value
  if (!t) return 0
  return t.requirement_prompt + t.requirement_completion
})

const searchTokens = computed<number>(() => {
  const t = tokenUsage.value
  if (!t) return 0
  return t.search_prompt + t.search_completion
})

const writerTokens = computed<number>(() => {
  const t = tokenUsage.value
  if (!t) return 0
  return t.writer_prompt + t.writer_completion
})

const complianceTokens = computed<number>(() => {
  const t = tokenUsage.value
  if (!t) return 0
  return t.compliance_prompt + t.compliance_completion
})

const reviewTokens = computed<number>(() => {
  const t = tokenUsage.value
  if (!t) return 0
  return t.review_prompt + t.review_completion
})

const totalTokens = computed<number>(() => {
  return (
    requirementTokens.value +
    searchTokens.value +
    writerTokens.value +
    complianceTokens.value +
    reviewTokens.value
  )
})

/**
 * 获取文档详情
 */
async function fetchDocument(): Promise<void> {
  const docId: string | string[] | undefined = route.params.id
  if (!docId || typeof docId !== 'string') return

  loading.value = true
  try {
    const result = await getDocument(docId)
    docInfo.value = result
  } catch (error) {
    console.error('获取文档详情失败:', error)
  } finally {
    loading.value = false
  }
}

/**
 * 返回列表
 */
function goBack(): void {
  router.push('/documents')
}

/**
 * 复制内容到剪贴板
 */
async function handleCopy(): Promise<void> {
  if (!docInfo.value?.content) return

  try {
    await navigator.clipboard.writeText(docInfo.value.content)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败')
  }
}

/**
 * 导出Markdown文件
 */
function handleExport(): void {
  if (!docInfo.value?.content) return

  // 创建Blob对象
  const blob: Blob = new Blob([docInfo.value.content], { type: 'text/markdown' })
  // 创建下载链接
  const url: string = URL.createObjectURL(blob)
  const link: HTMLAnchorElement = document.createElement('a')
  link.href = url
  link.download = `${docInfo.value.title || '专利交底书'}.md`
  document.body.appendChild(link)
  link.click()
  // 清理
  document.body.removeChild(link)
  URL.revokeObjectURL(url)

  ElMessage.success('导出成功')
}

onMounted(() => {
  fetchDocument()
})
</script>

<style lang="scss" scoped>
@import '@/assets/styles/variables.scss';

.document-detail {
  width: 100%;
}

.loading-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 100px 0;
  color: $text-secondary;

  .loading-icon {
    color: $primary-color;
    animation: spin 1s linear infinite;
    margin-bottom: 12px;
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.detail-container {
  max-width: 960px;
  margin: 0 auto;
}

// 文档头部
.doc-header {
  background: #fff;
  border-radius: $border-radius-lg;
  padding: 24px 32px;
  margin-bottom: 20px;
  box-shadow: $shadow-sm;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.header-left {
  flex: 1;

  .back-btn {
    margin-bottom: 8px;
    padding: 0;
  }

  .doc-title {
    font-size: 24px;
    font-weight: 600;
    color: $text-primary;
    margin-bottom: 12px;
  }

  .doc-meta {
    display: flex;
    align-items: center;
    gap: 20px;
    color: $text-secondary;
    font-size: 13px;

    .meta-item {
      display: flex;
      align-items: center;
      gap: 4px;
    }
  }
}

.header-right {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

// 文档正文
.doc-content {
  background: #fff;
  border-radius: $border-radius-lg;
  padding: 40px 60px;
  box-shadow: $shadow-sm;
  min-height: 600px;
}

// Token统计
.token-stats {
  background: #fff;
  border-radius: $border-radius-lg;
  padding: 20px 32px;
  margin-top: 20px;
  box-shadow: $shadow-sm;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
  margin-top: 16px;
}

.stat-item {
  text-align: center;
  padding: 12px;
  background: $bg-page;
  border-radius: $border-radius-sm;

  .stat-label {
    font-size: 12px;
    color: $text-secondary;
    margin-bottom: 6px;
  }

  .stat-value {
    font-size: 18px;
    font-weight: 600;
    color: $primary-color;
  }
}
</style>