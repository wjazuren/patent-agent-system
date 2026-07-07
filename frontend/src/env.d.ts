/**
 * 环境变量类型声明
 * 让 import.meta.env 有完整的类型提示
 */

/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 页面标题 */
  readonly VITE_APP_TITLE: string
  /** API基础路径 */
  readonly VITE_API_BASE_URL: string
  /** 是否开启调试 */
  readonly VITE_DEBUG: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}