import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  // 使用Vue插件
  plugins: [vue()],

  // 路径别名：@ 指向 src 目录，导入文件更方便
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  css: {
    preprocessorOptions: {
      scss: {
        // 静默 @import 弃用警告
        silenceDeprecations: ['import'],
        // 可选：同时静默全局内置函数的弃用警告
        // silenceDeprecations: ['import', 'global-builtin'],
        
      }
    }
  },

  // 开发服务器配置
  server: {
    // 端口号
    port: 5173,
    // 自动打开浏览器
    open: true,
    // 代理配置：解决跨域问题
    // 前端请求 /api 开头的接口，会自动转发到后端
    proxy: {
      '/api': {
        // 后端服务地址
        target: 'http://localhost:8000',
        // 允许跨域
        changeOrigin: true,
        // 路径重写：去掉 /api 前缀
        rewrite: (pathStr: string) => pathStr.replace(/^\/api/, '')
      }
    }
  },

  // 构建配置
  build: {
    // 输出目录
    outDir: 'dist',
    // 构建时是否生成source map
    sourcemap: false,
    // 打包后静态资源目录
    assetsDir: 'static',
    // chunk大小警告限制（kb）
    chunkSizeWarningLimit: 1500,
    // rollup打包配置
    rollupOptions: {
      output: {
        // 静态资源按类型分文件夹
        chunkFileNames: 'static/js/[name]-[hash].js',
        entryFileNames: 'static/js/[name]-[hash].js',
        assetFileNames: 'static/[ext]/[name]-[hash].[ext]'
      }
    }
  }
})