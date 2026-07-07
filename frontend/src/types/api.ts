/**
 * API相关类型定义
 */

/** 健康检查响应 */
export interface HealthResponse {
  status: string
  version: string
  timestamp: string
}