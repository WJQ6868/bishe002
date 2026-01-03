import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    port: 2003,
    strictPort: true,
    host: true,
    // 允许通过域名/IP 访问开发服务器（避免 Vite Host 校验拦截）
    allowedHosts: ['wangjiaqi.me', '47.98.128.206'],
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
