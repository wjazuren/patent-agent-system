<template>
  <div class="markdown-render" ref="renderWrap">
    <!-- 专利附图单独展示区域 -->
    <template v-if="hasDiagram">
      <PatentImagePreview
        v-if="safeDiagramPaths.architecture"
        ref="archImgRef"
        :img-src="fullImgUrl(safeDiagramPaths.architecture)"
        :image-title="`图1 ${safeInventionName}系统架构示意图`"
        class="main-img"
      />
      <PatentImagePreview
        v-if="safeDiagramPaths.flow"
        :img-src="fullImgUrl(safeDiagramPaths.flow)"
        :image-title="`图2 ${safeInventionName}方法流程示意图`"
        class="follow-img"
        :style="{ width: followImgWidth }"
      />
    </template>

    <!-- Markdown正文渲染 -->
    <div class="markdown-body" v-html="renderedHtml"></div>
  </div>
</template>
<script setup lang="ts">
import { computed, ref, onMounted, nextTick, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import PatentImagePreview from './PatentImagePreview.vue'
import { convertStaticImgPath } from '@/utils/markdown'

const props = defineProps<{
  content: string
  inventionName?: string
  diagramPaths?: Record<string, string>
}>()

const renderWrap = ref<HTMLDivElement | null>(null)
const archImgRef = ref<InstanceType<typeof PatentImagePreview> | null>(null)
// 基准最大宽度（和样式统一）
const BASE_MAX_WIDTH = 680
// 图2动态宽度
const followImgWidth = ref('100%')

const safeDiagramPaths = computed(() => props.diagramPaths ?? {})
const safeInventionName = computed(() => props.inventionName ?? '')
const hasDiagram = computed(() => Object.keys(safeDiagramPaths.value).length > 0)

const fullImgUrl = (url: string) => {
  const base = import.meta.env.VITE_API_BASE_URL
  return url.startsWith('/static/') ? `${base}${url}` : url
}

// 计算缩放比例并赋值给图2
const calcScaleRatio = async () => {
  await nextTick()
  if (!archImgRef.value) return
  // 获取图1实际渲染宽度
  const archDom = archImgRef.value.$el as HTMLElement
  const realWidth = archDom?.offsetWidth || BASE_MAX_WIDTH
  // 缩放倍数 = 实际宽度 / 基准最大宽度
  const scaleRatio = realWidth / BASE_MAX_WIDTH
  // 图2设置同比例宽度
  followImgWidth.value = `${scaleRatio * 100}%`
}

// 监听附图出现、窗口变化重新计算
watch(hasDiagram, (val) => {
  if(val) calcScaleRatio()
}, { immediate: true })

onMounted(() => {
  calcScaleRatio()
  window.addEventListener('resize', calcScaleRatio)
})

const md: MarkdownIt = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: true,
  highlight: function (str: string, lang: string): string {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return '<pre class="hljs"><code>' +
          hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
          '</code></pre>'
      } catch (__) {}
    }
    return '<pre class="hljs"><code>' + md.utils.escapeHtml(str) + '</code></pre>'
  }
})

const renderedHtml = computed<string>(() => {
  if (!props.content) return ''
  let fixMd = convertStaticImgPath(props.content)
  let htmlStr = md.render(fixMd)
  htmlStr = htmlStr.replace(/<img\s+src=/gi, '<img style="max-width:680px;width:100%;height:auto;margin:12px auto;display:block;" src=')
  return htmlStr
})
</script>

<style lang="scss" scoped>
.markdown-render {
  width: 100%;
}
.markdown-body {
  width: 100%;
  overflow-x: hidden;
}

// 图1 固定基准最大宽度
:deep(.main-img img) {
  max-width: 680px;
  width: 100%;
  height: auto;
  display: block;
  margin: 10px auto;
}

// 图2 只保留基础布局，宽由JS同比例控制
:deep(.follow-img img) {
  height: auto;
  display: block;
  margin: 10px auto;
}
</style>