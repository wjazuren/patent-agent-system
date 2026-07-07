<template>
  <!--
    Markdown渲染组件
    专门用来渲染交底书的Markdown内容
    支持代码高亮、自定义样式
  -->
  <div class="markdown-render">
    <div
      class="markdown-body"
      v-html="renderedHtml"
    ></div>
  </div>
</template>

<script setup lang="ts">
/**
 * Markdown渲染组件逻辑
 * 使用markdown-it解析，配合highlight.js做代码高亮
 */
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

// 定义props - 使用TS泛型语法，类型安全
const props = defineProps<{
  /** Markdown原始内容 */
  content: string
}>()

// 创建markdown-it实例
// 配置：启用html、换行转换、自动链接
const md: MarkdownIt = new MarkdownIt({
  html: true,        // 允许HTML标签
  linkify: true,     // 自动识别链接
  typographer: true, // 美化符号
  breaks: true,      // 换行符转<br>
  // 代码高亮配置
  highlight: function (str: string, lang: string): string {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return '<pre class="hljs"><code>' +
          hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
          '</code></pre>'
      } catch (__) {
        // 高亮失败，继续走兜底逻辑
      }
    }
    // 没有语言或识别失败，返回转义后的纯文本
    return '<pre class="hljs"><code>' + md.utils.escapeHtml(str) + '</code></pre>'
  }
})

// 计算渲染后的HTML
const renderedHtml = computed<string>(() => {
  if (!props.content) return ''
  return md.render(props.content)
})
</script>

<style lang="scss" scoped>
// Markdown样式已经在global.scss里定义了
// 这里可以加一些组件特有的样式
.markdown-render {
  width: 100%;
}
</style>