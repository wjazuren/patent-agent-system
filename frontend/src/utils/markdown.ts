/**
 * 补齐 Markdown 内 /static 图片相对路径为后端完整地址
 * 后端只返回 /static/xxx 前端自动拼接后端域名端口
 */
export function convertStaticImgPath(markdownStr: string): string {
  // 后端接口基础地址
  const backendBase = import.meta.env.VITE_API_BASE_URL
  if (!backendBase) return markdownStr

  // 匹配所有 ![xxx](/static/xxx) 图片语法
  const reg = /(!\[.*?\])\(\/static\/([\s\S]*?)\)/g
  return markdownStr.replace(reg, (_, text, path) => {
    return `${text}(${backendBase}/static/${path})`
  })
}