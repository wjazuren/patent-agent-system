/**
 * Axios 请求封装
 * 统一处理请求拦截、响应拦截、错误提示、Token等
 */
import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'

// 创建axios实例
const request: AxiosInstance = axios.create({
  // 基础URL，从环境变量取
  baseURL: import.meta.env.VITE_API_BASE_URL,
  // 请求超时时间（毫秒）
  timeout: 600000, // 专利生成可能比较慢，超时设长一点
  // 请求头
  headers: {
    'Content-Type': 'application/json'
  }
})

// ========== 请求拦截器 ==========
// 在请求发送前做一些处理，比如加Token、加时间戳等
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 这里可以加Token（如果后端需要鉴权的话）
    // const token = localStorage.getItem('token')
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }

    // 开发环境打印请求日志
    if (import.meta.env.VITE_DEBUG === 'true') {
      console.log('[Request]', config.method?.toUpperCase(), config.url)
    }

    return config
  },
  (error: unknown) => {
    // 请求错误处理
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// ========== 响应拦截器 ==========
// 在响应返回后做统一处理，比如错误提示、数据格式转换
request.interceptors.response.use(
  (response: AxiosResponse) => {
    // 开发环境打印响应日志
    if (import.meta.env.VITE_DEBUG === 'true') {
      console.log('[Response]', response.config.url, response.data)
    }

    // 直接返回数据（后端FastAPI直接返回数据，没有统一code包装）
    // 如果后端有统一的code/message/data结构，这里可以统一处理
    // const res = response.data as ApiResponse<T>
    // if (res.code !== 200) {
    //   ElMessage.error(res.message || '请求失败')
    //   return Promise.reject(new Error(res.message))
    // }
    // return res.data

    return response.data
  },
  (error: any) => {
    // 响应错误处理
    console.error('响应错误:', error)

    // 根据错误状态码给不同提示
    let message: string = '网络请求失败，请稍后重试'

    if (error.response) {
      const status: number = error.response.status
      switch (status) {
        case 400:
          message = error.response.data?.detail || '请求参数错误'
          break
        case 401:
          message = '未授权，请先登录'
          break
        case 404:
          message = '请求的资源不存在'
          break
        case 500:
          message = '服务器内部错误'
          break
        default:
          message = `请求失败 (${status})`
      }
    } else if (error.request) {
      // 请求发出但没有收到响应
      message = '网络连接失败，请检查网络'
    }

    // 统一错误提示
    ElMessage.error(message)

    return Promise.reject(error)
  }
)

/**
 * 封装GET请求
 * @param url 请求地址
 * @param params 查询参数
 * @param config 额外配置
 * @returns Promise<T>
 */
export function get<T = unknown>(
  url: string,
  params?: Record<string, unknown>,
  config?: AxiosRequestConfig
): Promise<T> {
  return request.get(url, { params, ...config })
}

/**
 * 封装POST请求
 * @param url 请求地址
 * @param data 请求体数据
 * @param config 额外配置
 * @returns Promise<T>
 */
export function post<T = unknown>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig
): Promise<T> {
  return request.post(url, data, config)
}

export default request