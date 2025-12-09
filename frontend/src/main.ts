import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './styles/theme.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import { vuetify } from './plugins/vuetify'
import router from './router'
import App from './App.vue'
import axios from 'axios'
import { sendLog } from './utils/logger'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.use(vuetify)

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
}

// Axios 全局配置：后端基址与认证头
axios.defaults.baseURL = 'http://localhost:8000'
axios.interceptors.request.use((config) => {
  const t = localStorage.getItem('token')
  if (t) {
    config.headers = config.headers || {}
    ;(config.headers as any)['Authorization'] = `Bearer ${t}`
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
      localStorage.removeItem('token')
      router.push('/login')
    }
    return Promise.reject(err)
  }
)

app.mount('#app')
