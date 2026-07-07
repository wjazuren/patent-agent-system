/**
 * 专利相关API接口
 * 封装所有专利相关的后端接口调用
 */
import { get, post } from './index'
import type {
  GeneratePatentRequest,
  GeneratePatentResponse,
  PatentDocument,
  DocumentListResponse,
  PaginationParams
} from '@/types/patent'
import type { HealthResponse } from '@/types/api'

/**
 * 生成专利交底书
 * @param data 请求参数
 * @returns 生成结果
 */
export function generatePatent(data: GeneratePatentRequest): Promise<GeneratePatentResponse> {
  return post<GeneratePatentResponse>('/patent/generate', data)
}

/**
 * 获取文档详情
 * @param documentId 文档ID
 * @returns 文档详情
 */
export function getDocument(documentId: string): Promise<PatentDocument> {
  return get<PatentDocument>(`/patent/${documentId}`)
}

/**
 * 获取文档列表
 * @param params 查询参数
 * @returns 文档列表
 */
export function getDocumentList(params?: PaginationParams): Promise<DocumentListResponse> {
  return get<DocumentListResponse>('/patent/list', params)
}

/**
 * 健康检查
 * @returns 系统状态
 */
export function healthCheck(): Promise<HealthResponse> {
  return get<HealthResponse>('/health')
}