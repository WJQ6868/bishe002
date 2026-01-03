import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus, { ElMessage } from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './styles/theme.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import router from './router'
import App from './App.vue'
import axios from 'axios'
import { sendLog } from './utils/logger'
import { clearAuthState } from './utils/auth'

const app = createApp(App)

// 统一日期/时间�?Element Plus 组件语言为中�?dayjs.locale('zh-cn')

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// Axios 全局配置：后端基址与认证头
axios.defaults.baseURL = import.meta.env.VITE_API_BASE_URL || '/api'
axios.interceptors.request.use((config) => {
  const t = localStorage.getItem('token')
  if (t) {
    config.headers = config.headers || {}
      ; (config.headers as any)['Authorization'] = `Bearer ${t}`
  }
  sendLog('info', `Request Start: ${config.method?.toUpperCase()} ${config.url}`, { params: config.params, data: config.data })
  return config
})
axios.interceptors.response.use(
  (res) => {
    sendLog('info', `Request Success: ${res.config.method?.toUpperCase()} ${res.config.url}`, { status: res.status })
    return res
  },
  (err) => {
    sendLog('error', `Request Failed: ${err.config?.url}`, { status: err.response?.status, message: err.message })
    if (err?.response?.status === 401) {
      clearAuthState()
      ElMessage.warning('登录状态已过期，请重新登录')
      router.push('/login')
    }
    return Promise.reject(err)
  }
)

app.mount('#app')

