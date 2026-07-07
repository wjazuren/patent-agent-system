/**
 * 格式化工具函数
 * 统一的日期、数字、文本格式化
 */
import dayjs from 'dayjs'
import type { RiskLevel } from '@/types/common'
import { RISK_LEVEL_TEXT } from './constants'

/**
 * 格式化日期时间
 * @param date 日期（字符串/Date）
 * @param format 格式
 * @returns 格式化后的日期字符串
 */
export function formatDateTime(
  date: string | Date | undefined | null,
  format: string = 'YYYY-MM-DD HH:mm:ss'
): string {
  if (!date) return '-'
  return dayjs(date).format(format)
}

/**
 * 格式化日期（只到天）
 * @param date 日期
 * @returns 格式化后的日期字符串
 */
export function formatDate(date: string | Date | undefined | null): string {
  return formatDateTime(date, 'YYYY-MM-DD')
}

/**
 * 格式化数字（加千分位）
 * @param num 数字
 * @returns 格式化后的字符串
 */
export function formatNumber(num: number | undefined | null): string {
  if (num === null || num === undefined || isNaN(num)) return '0'
  return num.toLocaleString()
}

/**
 * 格式化Token数量
 * @param tokens Token数量
 * @returns 格式化后的字符串
 */
export function formatTokens(tokens: number | undefined | null): string {
  if (!tokens) return '0'
  if (tokens >= 10000) {
    return (tokens / 1000).toFixed(1) + 'k'
  }
  return formatNumber(tokens)
}

/**
 * 截断文本
 * @param text 原始文本
 * @param maxLength 最大长度
 * @returns 截断后的文本
 */
export function truncateText(text: string, maxLength: number = 100): string {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '...'
}

/**
 * 获取风险等级文本
 * @param level 风险等级
 * @returns 风险等级文本
 */
export function getRiskLevelText(level: RiskLevel | string): string {
  return RISK_LEVEL_TEXT[level] || '未知'
}