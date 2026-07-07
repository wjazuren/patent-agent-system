/**
 * 统计相关API接口
 */
import { get } from './index'
import type { SystemStats } from '@/types/patent'

/**
 * 获取系统统计信息
 * @returns 统计数据
 */
export function getSystemStats(): Promise<SystemStats> {
  return get<SystemStats>('/stats')
}