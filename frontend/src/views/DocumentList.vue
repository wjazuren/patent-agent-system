<template>
  <!--
    文档列表页
    展示历史生成的所有文档，支持搜索、筛选、分页
  -->
  <div class="document-list">
    <!-- 搜索筛选区 -->
    <div class="filter-bar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索发明名称..."
        clearable
        style="width: 300px"
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <el-select
        v-model="riskFilter"
        placeholder="风险等级"
        clearable
        style="width: 150px"
        @change="handleSearch"
      >
        <el-option label="低风险" value="low" />
        <el-option label="中风险" value="medium" />
        <el-option label="高风险" value="high" />
      </el-select>

      <el-button type="primary" @click="handleSearch">
        <el-icon><Search /></el-icon>
        搜索
      </el-button>

      <div class="filter-right">
        <el-button @click="handleRefresh">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 文档列表 -->
    <div class="list-container">
      <!-- 加载中 -->
      <div v-if="loading" class="loading-wrap">
        <el-icon class="loading-icon" :size="40">
          <Loading />
        </el-icon>
        <p>加载中...</p>
      </div>

      <!-- 空状态 -->
      <el-empty
        v-else-if="documentList.length === 0"
        description="暂无文档，去生成一份吧"
      >
        <el-button type="primary" @click="goToGenerate">去生成</el-button>
      </el-empty>

      <!-- 文档卡片列表 -->
      <div v-else class="document-cards">
        <div
          v-for="doc in documentList"
          :key="doc.document_id"
          class="doc-card"
          @click="goToDetail(doc.document_id)"
        >
          <!-- 卡片头部 -->
          <div class="card-header">
            <h3 class="doc-title text-ellipsis-2">{{ doc.title }}</h3>
            <RiskTag :level="doc.risk_level" size="small" />
          </div>

          <!-- 卡片内容 -->
          <div class="card-body">
            <p class="doc-abstract text-ellipsis-3">{{ doc.abstract }}</p>
          </div>

          <!-- 卡片底部 -->
          <div class="card-footer">
            <div class="footer-item">
              <el-icon><Clock /></el-icon>
              <span>{{ formatDateTime(doc.created_at, 'MM-DD HH:mm') }}</span>
            </div>
            <div class="footer-item">
              <el-icon><RefreshRight /></el-icon>
              <span>{{ doc.iteration_count || 0 }}轮迭代</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @size-change="handlePageChange"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 文档列表页逻辑
 */
import { ref, onMounted,onActivated } from 'vue'
import { useRouter } from 'vue-router'
import { getDocumentList } from '@/api/patent'
import { formatDateTime } from '@/utils/format'
import RiskTag from '@/components/RiskTag.vue'
import type { DocumentListItem } from '@/types/patent'
import type { RiskLevel } from '@/types/common'

const router = useRouter()

// 搜索关键词
const searchKeyword = ref<string>('')
// 风险筛选
const riskFilter = ref<RiskLevel | ''>('')
// 加载状态
const loading = ref<boolean>(false)
// 文档列表
const documentList = ref<DocumentListItem[]>([])
// 总数
const total = ref<number>(0)
// 当前页
const currentPage = ref<number>(1)
// 每页数量
const pageSize = ref<number>(10)

/**
 * 获取文档列表
 */
async function fetchList(): Promise<void> {
  loading.value = true
  try {
    const offset: number = (currentPage.value - 1) * pageSize.value
    const result = await getDocumentList({
      limit: pageSize.value,
      offset
    })

    total.value = result.total || 0
    documentList.value = result.items || []
  } catch (error) {
    console.error('获取文档列表失败:', error)
  } finally {
    loading.value = false
  }
}

/**
 * 搜索
 */
function handleSearch(): void {
  currentPage.value = 1
  fetchList()
}

/**
 * 分页变化
 */
function handlePageChange(): void {
  fetchList()
}

/**
 * 刷新
 */
function handleRefresh(): void {
  fetchList()
}

/**
 * 跳转到生成页
 */
function goToGenerate(): void {
  router.push('/generate')
}

/**
 * 跳转到详情页
 */
function goToDetail(id: string): void {
  router.push(`/documents/${id}`)
}

// 页面加载时获取列表
onMounted(() => {
  fetchList()
})
// 每次页面被激活获取列表
onActivated(() => {
  fetchList()
})
</script>

<style lang="scss" scoped>
@import '@/assets/styles/variables.scss';

.document-list {
  width: 100%;
}

// 筛选栏
.filter-bar {
  background: #fff;
  padding: 16px 20px;
  border-radius: $border-radius-lg;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: $shadow-sm;

  .filter-right {
    margin-left: auto;
  }
}

// 列表容器
.list-container {
  min-height: 400px;
}

.loading-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
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

// 文档卡片网格
.document-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.doc-card {
  background: #fff;
  border-radius: $border-radius-md;
  padding: 20px;
  box-shadow: $shadow-sm;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;

  &:hover {
    box-shadow: $shadow-md;
    transform: translateY(-2px);
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;

  .doc-title {
    font-size: 16px;
    font-weight: 600;
    color: $text-primary;
    line-height: 1.5;
    flex: 1;
  }
}

.card-body {
  flex: 1;
  margin-bottom: 16px;

  .doc-abstract {
    font-size: 13px;
    color: $text-secondary;
    line-height: 1.6;
  }
}

.card-footer {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-top: 12px;
  border-top: 1px solid $border-color-lighter;
  font-size: 12px;
  color: $text-placeholder;

  .footer-item {
    display: flex;
    align-items: center;
    gap: 4px;
  }
}

// 分页
.pagination-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
</style>