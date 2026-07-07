/**
 * 常量定义
 * 定义项目中使用的固定常量
 */

/** Agent列表定义 */
export const AGENT_LIST = [
  {
    key: 'requirement',
    name: '需求对接Agent',
    description: '解析技术方案，提取创新点'
  },
  {
    key: 'search',
    name: '现有技术检索Agent',
    description: '检索对比专利，评估新颖性'
  },
  {
    key: 'writer',
    name: '交底书撰写Agent',
    description: '生成完整交底书初稿'
  },
  {
    key: 'compliance',
    name: '合规校验Agent',
    description: '格式与法条合规性检查'
  },
  {
    key: 'review',
    name: '质量评审Agent',
    description: '综合质量评审与打回'
  },
  {
    key: 'output',
    name: '文档输出Agent',
    description: '生成标准文档并归档'
  }
] as const

/** Agent总数 */
export const TOTAL_AGENT_COUNT = AGENT_LIST.length

/** 最大迭代次数 */
export const MAX_ITERATION_COUNT = 3

/** 每页默认数量 */
export const DEFAULT_PAGE_SIZE = 10

/** 风险等级文本映射 */
export const RISK_LEVEL_TEXT: Record<string, string> = {
  low: '低风险',
  medium: '中风险',
  high: '高风险'
}

/** 风险等级颜色映射 */
export const RISK_LEVEL_COLOR: Record<string, string> = {
  low: '#67c23a',
  medium: '#e6a23c',
  high: '#f56c6c'
}