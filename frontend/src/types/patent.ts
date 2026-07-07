/**
 * 专利相关类型定义
 * 定义交底书、检索报告、Token统计等数据结构
 */
import type { RiskLevel, PaginatedResponse } from './common'

/** Token消耗统计 */
export interface TokenUsage {
  /** 需求对接 - 输入Token */
  requirement_prompt: number
  /** 需求对接 - 输出Token */
  requirement_completion: number
  /** 检索 - 输入Token */
  search_prompt: number
  /** 检索 - 输出Token */
  search_completion: number
  /** 撰写 - 输入Token */
  writer_prompt: number
  /** 撰写 - 输出Token */
  writer_completion: number
  /** 合规校验 - 输入Token */
  compliance_prompt: number
  /** 合规校验 - 输出Token */
  compliance_completion: number
  /** 质量评审 - 输入Token */
  review_prompt: number
  /** 质量评审 - 输出Token */
  review_completion: number
}

/** 对比专利 */
export interface PriorPatent {
  /** 专利号 */
  patent_number: string
  /** 专利标题 */
  title: string
  /** 相似度 */
  similarity: number
  /** 摘要 */
  abstract?: string
}

/** 现有技术检索报告 */
export interface PriorArtReport {
  /** 风险等级 */
  risk_level: RiskLevel
  /** 对比专利列表 */
  patents: PriorPatent[]
  /** 风险说明 */
  risk_description: string
}

/** 专利交底书全文 */
export interface PatentDocket {
  /** 发明名称 */
  title: string
  /** 技术领域 */
  technical_field: string
  /** 背景技术 */
  background_tech: string
  /** 发明内容 */
  invention_content: string
  /** 附图说明 */
  drawings_description: string
  /** 具体实施方式 */
  detailed_implementation: string
  /** 权利要求书 */
  claims: string
  /** 摘要 */
  abstract: string
}

/** 合规问题 */
export interface ComplianceIssue {
  /** 问题级别 */
  severity: 'minor' | 'major' | 'critical'
  /** 问题描述 */
  description: string
  /** 所在章节 */
  section: string
  /** 修改建议 */
  suggestion?: string
}

/** 合规校验报告 */
export interface ComplianceReport {
  /** 是否通过 */
  passed: boolean
  /** 问题列表 */
  issues: ComplianceIssue[]
  /** 格式得分 */
  format_score: number
  /** 充分性得分 */
  sufficiency_score: number
}

/** 文档详情（完整信息） */
export interface PatentDocument {
  /** 文档ID */
  document_id: string
  /** 发明名称 */
  title: string
  /** 摘要 */
  abstract: string
  /** 风险等级 */
  risk_level: RiskLevel
  /** 迭代次数 */
  iteration_count: number
  /** 创建时间 */
  created_at: string
  /** 更新时间 */
  updated_at: string
  /** Markdown格式的完整内容 */
  content: string
  /** Token消耗统计 */
  token_usage?: TokenUsage
  /** 检索报告 */
  prior_art_report?: PriorArtReport
  /** 合规报告 */
  compliance_report?: ComplianceReport
}

/** 文档列表项（精简信息） */
export interface DocumentListItem {
  /** 文档ID */
  document_id: string
  /** 发明名称 */
  title: string
  /** 摘要 */
  abstract: string
  /** 风险等级 */
  risk_level: RiskLevel
  /** 迭代次数 */
  iteration_count: number
  /** 创建时间 */
  created_at: string
}

/** 文档列表响应 */
export type DocumentListResponse = PaginatedResponse<DocumentListItem>

/** 生成交底书请求参数 */
export interface GeneratePatentRequest {
  /** 用户输入的技术方案描述 */
  user_input: string
  /** 用户ID（可选） */
  user_id?: string
}

/** 生成交底书响应 */
export interface GeneratePatentResponse {
  /** 请求ID */
  request_id: string
  /** 文档ID */
  document_id: string
  /** 状态 */
  status: 'success' | 'failed'
  /** 消息 */
  message?: string
  /** 风险等级 */
  risk_level: RiskLevel
  /** 迭代次数 */
  iteration_count: number
  /** Token消耗 */
  token_usage?: TokenUsage
  /** 执行日志 */
  process_logs?: string[]
}

/** 系统统计数据 */
export interface SystemStats {
  total_documents: number
  total_tokens: number
  today_count: number
  risk_distribution: {
    low: number
    medium: number
    high: number
  }
  trend_dates: string[]
  trend_values: number[]
  // 各阶段真实 Token 消耗
  requirement_tokens: number
  search_tokens: number
  writer_tokens: number
  compliance_tokens: number
  review_tokens: number
  // 真实平均迭代轮次
  avg_iterations: number
}
export interface PaginationParams {
  limit: number
  offset: number
  keyword?: string
  [key: string]: any
}