/**
 * Vue单文件组件类型声明
 * 让 TypeScript 识别 .vue 文件
 */

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

// markdown-it 类型声明（如果没有安装@types的话）
declare module 'markdown-it' {
  interface MarkdownItOptions {
    html?: boolean
    linkify?: boolean
    typographer?: boolean
    breaks?: boolean
    highlight?: (str: string, lang: string) => string
  }

  class MarkdownIt {
    constructor(options?: MarkdownItOptions)
    render(md: string): string
    utils: {
      escapeHtml(str: string): string
    }
  }

  export default MarkdownIt
}