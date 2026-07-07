<template>
  <!--
    数据统计看板页
    展示系统运行数据：生成数量、Token消耗、风险分布等
  -->
  <div class="stats-view">
    <!-- 顶部数据卡片 -->
    <div class="stats-cards">
      <div class="stat-card">
        <div class="card-icon icon-blue">
          <el-icon><Document /></el-icon>
        </div>
        <div class="card-info">
          <div class="card-value">{{ formatNumber(stats.total_documents) }}</div>
          <div class="card-label">累计生成文档</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="card-icon icon-green">
          <el-icon><Coin /></el-icon>
        </div>
        <div class="card-info">
          <div class="card-value">{{ formatTokens(totalTokens) }}</div>
          <div class="card-label">累计Token消耗</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="card-icon icon-orange">
          <el-icon><Warning /></el-icon>
        </div>
        <div class="card-info">
          <div class="card-value">{{ highRiskCount }}</div>
          <div class="card-label">高风险文档</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="card-icon icon-purple">
          <el-icon><RefreshRight /></el-icon>
        </div>
        <div class="card-info">
          <div class="card-value">{{ avgIterations }}</div>
          <div class="card-label">平均迭代轮次</div>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-row">
      <!-- 风险等级分布 -->
      <div class="chart-card">
        <div class="chart-title">风险等级分布</div>
        <div ref="riskChartRef" class="chart-container"></div>
      </div>

      <!-- Token消耗分布 -->
      <div class="chart-card">
        <div class="chart-title">各环节Token消耗占比</div>
        <div ref="tokenChartRef" class="chart-container"></div>
      </div>
    </div>

    <!-- 生成趋势图 -->
    <div class="chart-card full-width">
      <div class="chart-title">近7日生成趋势</div>
      <div ref="trendChartRef" class="chart-container trend-chart"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { ECharts } from 'echarts'
import { getSystemStats } from '@/api/stats'
import { formatNumber, formatTokens } from '@/utils/format'
import type { SystemStats } from '@/types/patent'

// 统计数据 - 完整初始兜底，杜绝渲染期 undefined 报错
const stats = ref<SystemStats>({
  total_documents: 0,
  total_tokens: 0,
  today_count: 0,
  risk_distribution: { low: 0, medium: 0, high: 0 },
  trend_dates: [],
  trend_values: [],
  requirement_tokens: 0,
  search_tokens: 0,
  writer_tokens: 0,
  compliance_tokens: 0,
  review_tokens: 0,
  avg_iterations: 0
})

const loading = ref<boolean>(true)

// 图表DOM引用
const riskChartRef = ref<HTMLDivElement | null>(null)
const tokenChartRef = ref<HTMLDivElement | null>(null)
const trendChartRef = ref<HTMLDivElement | null>(null)

// 图表实例
let riskChart: ECharts | null = null
let tokenChart: ECharts | null = null
let trendChart: ECharts | null = null

// ========== 计算属性（全部来自后端真实数据） ==========
const totalTokens = computed<number>(() => stats.value.total_tokens)
const highRiskCount = computed<number>(() => stats.value.risk_distribution.high)
const avgIterations = computed<number>(() => stats.value.avg_iterations)

// Token 占比饼图数据（完全真实，无估算）
const tokenBreakdown = computed(() => [
  { value: stats.value.requirement_tokens, name: '需求对接' },
  { value: stats.value.search_tokens, name: '现有技术检索' },
  { value: stats.value.writer_tokens, name: '交底书撰写' },
  { value: stats.value.compliance_tokens, name: '合规校验' },
  { value: stats.value.review_tokens, name: '质量评审' }
])

// ========== 图表初始化与更新 ==========
function initRiskChart(): void {
  if (!riskChartRef.value) return
  riskChart = echarts.init(riskChartRef.value)
  updateRiskChart()
}

function updateRiskChart(): void {
  if (!riskChart) return
  const { low, medium, high } = stats.value.risk_distribution
  riskChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, left: 'center' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 20, fontWeight: 'bold' } },
      labelLine: { show: false },
      data: [
        { value: low, name: '低风险', itemStyle: { color: '#67c23a' } },
        { value: medium, name: '中风险', itemStyle: { color: '#e6a23c' } },
        { value: high, name: '高风险', itemStyle: { color: '#f56c6c' } }
      ]
    }]
  })
}

function initTokenChart(): void {
  if (!tokenChartRef.value) return
  tokenChart = echarts.init(tokenChartRef.value)
  updateTokenChart()
}

function updateTokenChart(): void {
  if (!tokenChart) return
  tokenChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, left: 'center' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      labelLine: { show: false },
      data: tokenBreakdown.value
    }]
  })
}

function initTrendChart(): void {
  if (!trendChartRef.value) return
  trendChart = echarts.init(trendChartRef.value)
  updateTrendChart()
}

function updateTrendChart(): void {
  if (!trendChart) return
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: stats.value.trend_dates.map(d => d.slice(5))
    },
    yAxis: { type: 'value', name: '生成数量' },
    series: [{
      name: '生成数量',
      type: 'line',
      smooth: true,
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
          { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
        ])
      },
      lineStyle: { color: '#409eff', width: 2 },
      itemStyle: { color: '#409eff' },
      data: stats.value.trend_values
    }]
  })
}

// ========== 数据拉取 ==========
async function fetchStats(): Promise<void> {
  loading.value = true
  try {
    const result = await getSystemStats()
    stats.value = result
    // 数据更新后刷新所有图表
    await nextTick()
    updateRiskChart()
    updateTokenChart()
    updateTrendChart()
  } catch (error) {
    console.error('获取统计数据失败:', error)
  } finally {
    loading.value = false
  }
}

function handleResize(): void {
  riskChart?.resize()
  tokenChart?.resize()
  trendChart?.resize()
}

onMounted(async () => {
  await fetchStats()
  setTimeout(() => {
    initRiskChart()
    initTokenChart()
    initTrendChart()
  }, 100)
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  riskChart?.dispose()
  tokenChart?.dispose()
  trendChart?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<style lang="scss" scoped>
@import '@/assets/styles/variables.scss';

.stats-view {
  width: 100%;
}

// 顶部统计卡片
.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: #fff;
  border-radius: $border-radius-lg;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: $shadow-sm;
  transition: all 0.2s;

  &:hover {
    box-shadow: $shadow-md;
    transform: translateY(-2px);
  }
}

.card-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: #fff;
  flex-shrink: 0;

  &.icon-blue {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  }

  &.icon-green {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  }

  &.icon-orange {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  }

  &.icon-purple {
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  }
}

.card-info {
  flex: 1;

  .card-value {
    font-size: 24px;
    font-weight: 700;
    color: $text-primary;
    margin-bottom: 4px;
  }

  .card-label {
    font-size: 13px;
    color: $text-secondary;
  }
}

// 图表行
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

.chart-card {
  background: #fff;
  border-radius: $border-radius-lg;
  padding: 20px;
  box-shadow: $shadow-sm;

  &.full-width {
    grid-column: 1 / -1;
  }
}

.chart-title {
  font-size: 15px;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 16px;
}

.chart-container {
  width: 100%;
  height: 280px;
}

.trend-chart {
  height: 320px;
}
</style>