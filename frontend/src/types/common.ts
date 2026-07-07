/**
 * 通用类型定义
 * 定义项目中多处复用的基础类型
 */

/** 风险等级 */
export type RiskLevel = 'low' | 'medium' | 'high'

/** 生成状态 */
export type GenerateStatus = 'pending' | 'running' | 'success' | 'failed'

/** Agent执行状态 */
export type AgentStatus = 'pending' | 'running' | 'done'

/** 分页请求参数 */
export interface PaginationParams {
  /** 每页数量 */
  limit?: number
  /** 偏移量 */
  offset?: number
}

/** 分页响应数据 */
export interface PaginatedResponse<T> {
  /** 数据列表 */
  items: T[]
  /** 总数 */
  total: number
}

/** 通用API响应 */
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}