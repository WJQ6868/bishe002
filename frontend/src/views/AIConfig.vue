<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Connection, Setting, Document, DataLine, Tickets, Warning,
  Plus, Edit, Delete, Check, Refresh, View, Download
} from '@element-plus/icons-vue'

type FeatureKey = 'customer' | 'course' | 'lesson'
type TestStatus = 'none' | 'pending' | 'success' | 'fail'

interface ApiItem {
  id: string
  feature: FeatureKey
  name: string
  model: string
  endpoint: string
  apiKey: string
  headers: string
  timeout: number
  retry: number
  rateLimit: number
  concurrency: number
  enabled: boolean
  isDefault: boolean
  lastTest: TestStatus
  testMsg?: string
}

interface FeatureConfig {
  enabled: boolean
  defaultApiId: string
  timeout: number
  retry: number
  rateLimit: number
  concurrency: number
  analytics: {
    todayCalls: number
    successRate: number
    errorRate: number
  }
  rules: Record<string, any>
}

interface OperationLog {
  id: string
  action: string
  operator: string
  time: string
  detail: string
}

const activeTab = ref('overview')
const STORAGE_KEY = 'ai_feature_configs'
const apiDialogVisible = ref(false)
const apiDialogMode = ref<'create' | 'edit'>('create')
const apiDialogFeature = ref<FeatureKey>('customer')
const apiForm = reactive<ApiItem>({
  id: '',
  feature: 'customer',
  name: '',
  model: '',
  endpoint: '',
  apiKey: '',
  headers: '',
  timeout: 30,
  retry: 2,
  rateLimit: 100,
  concurrency: 10,
  enabled: true,
  isDefault: false,
  lastTest: 'none',
  testMsg: ''
})

const apiList = ref<ApiItem[]>([
  {
    id: 'api-cs-1',
    feature: 'customer',
    name: '通义千问 (Qwen)',
    model: 'qwen-max',
    endpoint: 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
    apiKey: '',
    headers: 'Content-Type: application/json',
    timeout: 30,
    retry: 2,
    rateLimit: 500,
    concurrency: 20,
    enabled: true,
    isDefault: true,
    lastTest: 'none'
  },
  {
    id: 'api-ca-1',
    feature: 'course',
    name: 'DeepSeek 检索',
    model: 'deepseek-r1',
    endpoint: 'https://api.deepseek.com/v1/chat/completions',
    apiKey: '',
    headers: 'Content-Type: application/json',
    timeout: 30,
    retry: 2,
    rateLimit: 300,
    concurrency: 10,
    enabled: true,
    isDefault: true,
    lastTest: 'none'
  },
  {
    id: 'api-lp-1',
    feature: 'lesson',
    name: '豆包生成',
    model: 'doubao-pro',
    endpoint: 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
    apiKey: '',
    headers: 'Content-Type: application/json',
    timeout: 45,
    retry: 2,
    rateLimit: 200,
    concurrency: 8,
    enabled: true,
    isDefault: true,
    lastTest: 'none'
  }
])

const featureConfigs: Record<FeatureKey, FeatureConfig> = reactive({
  customer: {
    enabled: true,
    defaultApiId: 'api-cs-1',
    timeout: 30,
    retry: 2,
    rateLimit: 500,
    concurrency: 20,
    analytics: { todayCalls: 126, successRate: 0.97, errorRate: 0.01 },
    rules: {
      knowledgeBase: true,
      kbTrigger: '关键词+FAQ 匹配',
      responseTemplate: '尊敬的{用户角色}，针对您咨询的“{问题}”，处理结果如下：{答案}'
    }
  },
  course: {
    enabled: true,
    defaultApiId: 'api-ca-1',
    timeout: 30,
    retry: 2,
    rateLimit: 200,
    concurrency: 10,
    analytics: { todayCalls: 64, successRate: 0.94, errorRate: 0.03 },
    rules: {
      reviewRequired: true,
      subjectScopes: ['数学', '英语', '物理'],
      responseFormat: 'concise',
      teacherDailyLimit: 200,
      subjectDailyLimit: 500
    }
  },
  lesson: {
    enabled: true,
    defaultApiId: 'api-lp-1',
    timeout: 45,
    retry: 2,
    rateLimit: 120,
    concurrency: 8,
    analytics: { todayCalls: 21, successRate: 0.91, errorRate: 0.06 },
    rules: {
      template: '通用教学模板',
      maxSlides: 25,
      wordLimit: 3000,
      scheduleWindow: '08:00-22:00',
      enableExport: true
    }
  }
})

const operationLogs = ref<OperationLog[]>([])
const apiTestLoading = ref(false)

const overviewCards = computed(() => {
  const map: Record<FeatureKey, string> = {
    customer: 'AI客服管理',
    course: 'AI课程助手管理',
    lesson: '智能教案工具管理'
  }
  return (['customer', 'course', 'lesson'] as FeatureKey[]).map(key => {
    const cfg = featureConfigs[key]
    return {
      key,
      title: map[key],
      enabled: cfg.enabled,
      calls: cfg.analytics.todayCalls,
      success: Math.round(cfg.analytics.successRate * 100),
      error: Math.round(cfg.analytics.errorRate * 100)
    }
  })
})

const allApis = computed(() => apiList.value)
const apiByFeature = (feature: FeatureKey) => computed(() => apiList.value.filter(a => a.feature === feature))

const persistState = () => {
  const payload = {
    apis: apiList.value,
    features: featureConfigs
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
}

const loadState = () => {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (!saved) return
  try {
    const parsed = JSON.parse(saved)
    if (Array.isArray(parsed.apis)) {
      apiList.value = parsed.apis
    }
    if (parsed.features) {
      (['customer','course','lesson'] as FeatureKey[]).forEach(key => {
        if (parsed.features[key]) {
          Object.assign(featureConfigs[key], parsed.features[key])
        }
      })
    }
  } catch (e) {
    console.warn('Failed to load saved AI config', e)
  }
}
loadState()

const pushLog = (action: string, detail: string) => {
  const log: OperationLog = {
    id: `${Date.now()}`,
    action,
    operator: '管理员',
    time: new Date().toLocaleString(),
    detail
  }
  operationLogs.value.unshift(log)
}

const resetApiForm = (feature: FeatureKey) => {
  apiForm.id = ''
  apiForm.feature = feature
  apiForm.name = ''
  apiForm.model = ''
  apiForm.endpoint = ''
  apiForm.apiKey = ''
  apiForm.headers = 'Content-Type: application/json'
  apiForm.timeout = 30
  apiForm.retry = 2
  apiForm.rateLimit = 100
  apiForm.concurrency = 10
  apiForm.enabled = true
  apiForm.isDefault = false
  apiForm.lastTest = 'none'
  apiForm.testMsg = ''
}

const openApiDialog = (mode: 'create' | 'edit', feature: FeatureKey, apiId?: string) => {
  apiDialogMode.value = mode
  apiDialogFeature.value = feature
  if (mode === 'create') {
    resetApiForm(feature)
  } else if (apiId) {
    const target = apiList.value.find(a => a.id === apiId)
    if (target) Object.assign(apiForm, target)
  }
  apiDialogVisible.value = true
}

const saveApi = async () => {
  if (!apiForm.name || !apiForm.endpoint || !apiForm.apiKey) {
    ElMessage.warning('请完整填写 API 名称、地址与密钥')
    return
  }
  if (apiDialogMode.value === 'create') {
    apiForm.id = `api-${Date.now()}`
    apiList.value.push({ ...apiForm })
    if (apiForm.isDefault || !featureConfigs[apiForm.feature].defaultApiId) {
      featureConfigs[apiForm.feature].defaultApiId = apiForm.id
      apiList.value.forEach(a => { if (a.feature === apiForm.feature) a.isDefault = a.id === apiForm.id })
    }
    pushLog('新增API', `${apiForm.name} (${apiForm.feature})`)
    ElMessage.success('API 已新增')
  } else {
    const idx = apiList.value.findIndex(a => a.id === apiForm.id)
    if (idx !== -1) {
      apiList.value[idx] = { ...apiForm }
      if (apiForm.isDefault) {
        featureConfigs[apiForm.feature].defaultApiId = apiForm.id
        apiList.value.forEach(a => { if (a.feature === apiForm.feature) a.isDefault = a.id === apiForm.id })
      }
      pushLog('编辑API', `${apiForm.name} (${apiForm.feature})`)
      ElMessage.success('API 已更新')
    }
  }
  persistState()
  apiDialogVisible.value = false
}

const deleteApi = (api: ApiItem) => {
  ElMessageBox.confirm(`确认删除 API【${api.name}】?`, '提示', { type: 'warning' }).then(() => {
    apiList.value = apiList.value.filter(a => a.id !== api.id)
    if (featureConfigs[api.feature].defaultApiId === api.id) {
      featureConfigs[api.feature].defaultApiId = apiByFeature(api.feature).value[0]?.id || ''
      apiByFeature(api.feature).value.forEach(a => a.isDefault = a.id === featureConfigs[api.feature].defaultApiId)
    }
    pushLog('删除API', `${api.name} (${api.feature})`)
    ElMessage.success('已删除')
    persistState()
  })
}

const setDefaultApi = (feature: FeatureKey, apiId: string) => {
  ElMessageBox.confirm('设为默认后将作为该功能的首选调用接口，是否继续？', '确认', { type: 'warning' }).then(() => {
    featureConfigs[feature].defaultApiId = apiId
    apiList.value.forEach(a => {
      if (a.feature === feature) a.isDefault = a.id === apiId
    })
    pushLog('设为默认', `功能 ${feature} -> ${apiId}`)
    ElMessage.success('已设为默认')
    persistState()
  })
}

const toggleFeature = (feature: FeatureKey, val: boolean) => {
  ElMessageBox.confirm(val ? '确认启用该功能？' : '确认禁用该功能？', '二次确认', { type: 'warning' }).then(() => {
    featureConfigs[feature].enabled = val
    pushLog(val ? '启用功能' : '禁用功能', `功能 ${feature}`)
    ElMessage.success(val ? '已启用' : '已禁用')
    persistState()
  }).catch(() => {
    featureConfigs[feature].enabled = !val
  })
}

const toggleApi = (api: ApiItem) => {
  ElMessageBox.confirm(api.enabled ? '确认禁用该 API？' : '确认启用该 API？', '二次确认', { type: 'warning' }).then(() => {
    api.enabled = !api.enabled
    pushLog(api.enabled ? '启用API' : '禁用API', api.name)
    persistState()
  }).catch(() => {
    api.enabled = api.enabled
  })
}

const testApi = async (api: ApiItem) => {
  apiTestLoading.value = true
  api.lastTest = 'pending'
  api.testMsg = ''
  try {
    await new Promise(resolve => setTimeout(resolve, 800))
    api.lastTest = 'success'
    api.testMsg = '连接成功，返回示例正常'
    pushLog('测试API', api.name)
    ElMessage.success('测试连接成功')
  } catch (e) {
    api.lastTest = 'fail'
    api.testMsg = '连接失败：网络异常'
    ElMessage.error('测试连接失败')
  } finally {
    apiTestLoading.value = false
    persistState()
  }
}

const saveFeatureConfig = (feature: FeatureKey) => {
  pushLog('保存配置', `功能 ${feature}`)
  ElMessage.success('配置已保存（示例存储）')
  persistState()
}

const exportLogs = () => {
  ElMessage.success('已导出操作日志 (模拟)')
}

const featureName = (key: FeatureKey) => {
  const map: Record<FeatureKey, string> = {
    customer: 'AI客服管理',
    course: 'AI课程助手管理',
    lesson: '智能教案工具管理'
  }
  return map[key]
}
</script>

<template>
  <div class="ai-settings-page">
    <div class="page-header">
      <div>
        <h1>AI设置</h1>
        <p class="subtitle">统一管理 AI 客服、AI 课程助手与智能教案工具的 API 配置与权限</p>
      </div>
      <el-button type="primary" :icon="Refresh" @click="() => ElMessage.success('已刷新概览数据（示例）')">刷新概览</el-button>
    </div>

    <div class="overview-card" v-if="activeTab === 'overview'">
      <div class="overview-grid">
        <el-card v-for="card in overviewCards" :key="card.key" shadow="hover">
          <div class="card-head">
            <div>
              <p class="card-title">{{ card.title }}</p>
              <p class="card-sub">今日调用 {{ card.calls }} 次</p>
            </div>
            <el-tag :type="card.enabled ? 'success' : 'info'">{{ card.enabled ? '已启用' : '未启用' }}</el-tag>
          </div>
          <div class="card-metrics">
            <div>
              <p class="metric-value">{{ card.success }}%</p>
              <p class="metric-label">成功率</p>
            </div>
            <div>
              <p class="metric-value warn">{{ card.error }}%</p>
              <p class="metric-label">异常率</p>
            </div>
          </div>
          <div class="card-actions">
            <el-button type="primary" link @click="activeTab = card.key">进入配置</el-button>
            <el-button link @click="activeTab = 'apis'">查看API</el-button>
          </div>
        </el-card>
      </div>
    </div>

    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane name="overview">
        <template #label>
          <span class="tab-label"><el-icon><View /></el-icon> API 调用总览</span>
        </template>
        <div class="overview-card">
          <div class="overview-grid">
            <el-card v-for="card in overviewCards" :key="card.key" shadow="hover">
              <div class="card-head">
                <div>
                  <p class="card-title">{{ card.title }}</p>
                  <p class="card-sub">今日调用 {{ card.calls }} 次</p>
                </div>
                <el-tag :type="card.enabled ? 'success' : 'info'">{{ card.enabled ? '已启用' : '未启用' }}</el-tag>
              </div>
              <div class="card-metrics">
                <div>
                  <p class="metric-value">{{ card.success }}%</p>
                  <p class="metric-label">成功率</p>
                </div>
                <div>
                  <p class="metric-value warn">{{ card.error }}%</p>
                  <p class="metric-label">异常率</p>
                </div>
              </div>
              <div class="card-actions">
                <el-button type="primary" link @click="activeTab = card.key">进入配置</el-button>
                <el-button link @click="activeTab = 'apis'">查看API</el-button>
              </div>
            </el-card>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane name="customer">
        <template #label>
          <span class="tab-label"><el-icon><Connection /></el-icon> AI 客服管理</span>
        </template>
        <div class="feature-header">
          <div class="title-block">
            <h3>面向学生的知识问答</h3>
            <p>配置 API、知识库规则、阈值与日志导出</p>
          </div>
          <el-switch v-model="featureConfigs.customer.enabled" @change="(val) => toggleFeature('customer', val as boolean)" />
        </div>
        <div class="feature-body">
          <el-card shadow="never" class="config-card">
            <template #header>
              <div class="card-header">
                <div>
                  <div class="card-title-row">API 配置</div>
                  <p class="hint">统一面板：新增/编辑/删除/设为默认/测试连接</p>
                </div>
                <el-button type="primary" :icon="Plus" @click="openApiDialog('create','customer')">新增 API</el-button>
              </div>
            </template>
            <el-table :data="apiByFeature('customer').value" border style="width: 100%">
              <el-table-column prop="name" label="名称" width="180" />
              <el-table-column prop="model" label="模型" width="160" />
              <el-table-column label="状态" width="120">
                <template #default="{ row }">
                  <el-switch v-model="row.enabled" @change="() => toggleApi(row)" />
                </template>
              </el-table-column>
              <el-table-column label="默认" width="80">
                <template #default="{ row }">
                  <el-tag v-if="row.isDefault" type="success" size="small">默认</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="endpoint" label="请求地址" min-width="220" show-overflow-tooltip />
              <el-table-column label="限流" width="120">
                <template #default="{ row }">{{ row.rateLimit }}/h</template>
              </el-table-column>
              <el-table-column label="并发" width="100">
                <template #default="{ row }">{{ row.concurrency }}</template>
              </el-table-column>
              <el-table-column label="操作" width="260" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" link @click="testApi(row)" :loading="apiTestLoading">测试连接</el-button>
                  <el-button size="small" link type="primary" @click="setDefaultApi('customer', row.id)" :disabled="row.id === featureConfigs.customer.defaultApiId">设为默认</el-button>
                  <el-button size="small" link type="primary" :icon="Edit" @click="openApiDialog('edit','customer', row.id)">编辑</el-button>
                  <el-button size="small" link type="danger" :icon="Delete" @click="deleteApi(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-card shadow="never" class="config-card">
            <template #header>
              <div class="card-header"><el-icon><Setting /></el-icon><span>功能与阈值</span></div>
            </template>
            <el-form label-width="160px" class="config-form">
              <el-form-item label="知识库管理">
                <el-switch v-model="featureConfigs.customer.rules.knowledgeBase" />
                <span class="hint">自定义 FAQ 与意图触发规则</span>
              </el-form-item>
              <el-form-item label="触发规则">
                <el-input v-model="featureConfigs.customer.rules.kbTrigger" placeholder="关键词/意图匹配策略" />
              </el-form-item>
              <el-form-item label="话术模板">
                <el-input type="textarea" v-model="featureConfigs.customer.rules.responseTemplate" :rows="3" />
              </el-form-item>
              <el-form-item label="超时时间 (秒)">
                <el-input-number v-model="featureConfigs.customer.timeout" :min="5" :max="120" />
              </el-form-item>
              <el-form-item label="重试次数">
                <el-input-number v-model="featureConfigs.customer.retry" :min="0" :max="5" />
              </el-form-item>
              <el-form-item label="频次限制 / 小时">
                <el-input-number v-model="featureConfigs.customer.rateLimit" :min="10" :max="2000" />
              </el-form-item>
              <el-form-item label="并发限制">
                <el-input-number v-model="featureConfigs.customer.concurrency" :min="1" :max="100" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :icon="Check" @click="saveFeatureConfig('customer')">保存配置</el-button>
                <el-button :icon="Download" @click="exportLogs">导出交互数据</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane name="course">
        <template #label>
          <span class="tab-label"><el-icon><Document /></el-icon> AI 课程助手管理</span>
        </template>
        <div class="feature-header">
          <div class="title-block">
            <h3>面向教师的资料检索问答</h3>
            <p>配置检索 API、资料审核、权限与频次</p>
          </div>
          <el-switch v-model="featureConfigs.course.enabled" @change="(val) => toggleFeature('course', val as boolean)" />
        </div>
        <div class="feature-body">
          <el-card shadow="never" class="config-card">
            <template #header>
              <div class="card-header">
                <div>
                  <div class="card-title-row">API 配置</div>
                  <p class="hint">检索类模型：支持新增/编辑/删除/设为默认/测试连接</p>
                </div>
                <el-button type="primary" :icon="Plus" @click="openApiDialog('create','course')">新增 API</el-button>
              </div>
            </template>
            <el-table :data="apiByFeature('course').value" border style="width: 100%">
              <el-table-column prop="name" label="名称" width="180" />
              <el-table-column prop="model" label="模型" width="160" />
              <el-table-column label="状态" width="120">
                <template #default="{ row }">
                  <el-switch v-model="row.enabled" @change="() => toggleApi(row)" />
                </template>
              </el-table-column>
              <el-table-column label="默认" width="80">
                <template #default="{ row }">
                  <el-tag v-if="row.isDefault" type="success" size="small">默认</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="endpoint" label="请求地址" min-width="220" show-overflow-tooltip />
              <el-table-column label="限流" width="120">
                <template #default="{ row }">{{ row.rateLimit }}/h</template>
              </el-table-column>
              <el-table-column label="并发" width="100">
                <template #default="{ row }">{{ row.concurrency }}</template>
              </el-table-column>
              <el-table-column label="操作" width="260" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" link @click="testApi(row)" :loading="apiTestLoading">测试连接</el-button>
                  <el-button size="small" link type="primary" @click="setDefaultApi('course', row.id)" :disabled="row.id === featureConfigs.course.defaultApiId">设为默认</el-button>
                  <el-button size="small" link type="primary" :icon="Edit" @click="openApiDialog('edit','course', row.id)">编辑</el-button>
                  <el-button size="small" link type="danger" :icon="Delete" @click="deleteApi(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-card shadow="never" class="config-card">
            <template #header>
              <div class="card-header"><el-icon><Setting /></el-icon><span>资料与权限</span></div>
            </template>
            <el-form label-width="180px" class="config-form">
              <el-form-item label="资料审核">
                <el-switch v-model="featureConfigs.course.rules.reviewRequired" />
                <span class="hint">开启后教师上传资料需审核后才能检索</span>
              </el-form-item>
              <el-form-item label="学科/年级权限">
                <el-select v-model="featureConfigs.course.rules.subjectScopes" multiple style="width: 100%" placeholder="选择可用范围">
                  <el-option v-for="sub in ['数学','英语','物理','化学','历史','生物']" :key="sub" :label="sub" :value="sub" />
                </el-select>
              </el-form-item>
              <el-form-item label="结果呈现">
                <el-radio-group v-model="featureConfigs.course.rules.responseFormat">
                  <el-radio label="concise">精简模式</el-radio>
                  <el-radio label="detail">详细模式</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="教师日调用上限">
                <el-input-number v-model="featureConfigs.course.rules.teacherDailyLimit" :min="50" :max="2000" />
              </el-form-item>
              <el-form-item label="学科日调用上限">
                <el-input-number v-model="featureConfigs.course.rules.subjectDailyLimit" :min="100" :max="5000" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :icon="Check" @click="saveFeatureConfig('course')">保存配置</el-button>
                <el-button :icon="Tickets" @click="exportLogs">导出调用日志</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane name="lesson">
        <template #label>
          <span class="tab-label"><el-icon><DataLine /></el-icon> 智能教案工具管理</span>
        </template>
        <div class="feature-header">
          <div class="title-block">
            <h3>面向教师的教案转 PPT</h3>
            <p>配置生成类 API、模板与频次限制</p>
          </div>
          <el-switch v-model="featureConfigs.lesson.enabled" @change="(val) => toggleFeature('lesson', val as boolean)" />
        </div>
        <div class="feature-body">
          <el-card shadow="never" class="config-card">
            <template #header>
              <div class="card-header">
                <div>
                  <div class="card-title-row">API 配置</div>
                  <p class="hint">生成类模型：支持新增/编辑/删除/设为默认/测试连接</p>
                </div>
                <el-button type="primary" :icon="Plus" @click="openApiDialog('create','lesson')">新增 API</el-button>
              </div>
            </template>
            <el-table :data="apiByFeature('lesson').value" border style="width: 100%">
              <el-table-column prop="name" label="名称" width="180" />
              <el-table-column prop="model" label="模型" width="160" />
              <el-table-column label="状态" width="120">
                <template #default="{ row }">
                  <el-switch v-model="row.enabled" @change="() => toggleApi(row)" />
                </template>
              </el-table-column>
              <el-table-column label="默认" width="80">
                <template #default="{ row }">
                  <el-tag v-if="row.isDefault" type="success" size="small">默认</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="endpoint" label="请求地址" min-width="220" show-overflow-tooltip />
              <el-table-column label="限流" width="120">
                <template #default="{ row }">{{ row.rateLimit }}/h</template>
              </el-table-column>
              <el-table-column label="并发" width="100">
                <template #default="{ row }">{{ row.concurrency }}</template>
              </el-table-column>
              <el-table-column label="操作" width="260" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" link @click="testApi(row)" :loading="apiTestLoading">测试连接</el-button>
                  <el-button size="small" link type="primary" @click="setDefaultApi('lesson', row.id)" :disabled="row.id === featureConfigs.lesson.defaultApiId">设为默认</el-button>
                  <el-button size="small" link type="primary" :icon="Edit" @click="openApiDialog('edit','lesson', row.id)">编辑</el-button>
                  <el-button size="small" link type="danger" :icon="Delete" @click="deleteApi(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-card shadow="never" class="config-card">
            <template #header>
              <div class="card-header"><el-icon><Setting /></el-icon><span>模板与规则</span></div>
            </template>
            <el-form label-width="180px" class="config-form">
              <el-form-item label="PPT 模板">
                <el-select v-model="featureConfigs.lesson.rules.template" style="width: 260px">
                  <el-option label="通用教学模板" value="通用教学模板" />
                  <el-option label="理科模板" value="理科模板" />
                  <el-option label="文科模板" value="文科模板" />
                </el-select>
                <span class="hint">可上传校级/学科模板后选择使用</span>
              </el-form-item>
              <el-form-item label="最大页数">
                <el-input-number v-model="featureConfigs.lesson.rules.maxSlides" :min="10" :max="40" />
              </el-form-item>
              <el-form-item label="生成字数上限">
                <el-input-number v-model="featureConfigs.lesson.rules.wordLimit" :min="1000" :max="6000" />
              </el-form-item>
              <el-form-item label="可用时段">
                <el-input v-model="featureConfigs.lesson.rules.scheduleWindow" placeholder="如 08:00-22:00" />
              </el-form-item>
              <el-form-item label="允许导出 PPT">
                <el-switch v-model="featureConfigs.lesson.rules.enableExport" />
              </el-form-item>
              <el-form-item label="频次限制 / 教师">
                <el-input-number v-model="featureConfigs.lesson.rateLimit" :min="10" :max="500" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :icon="Check" @click="saveFeatureConfig('lesson')">保存配置</el-button>
                <el-button :icon="Warning" @click="exportLogs">导出生成日志</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane name="apis">
        <template #label>
          <span class="tab-label"><el-icon><Connection /></el-icon> API 配置列表</span>
        </template>
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <div>
                <h3>统一 API 配置面板</h3>
                <p class="hint">新增/编辑/删除/设为默认/测试连接；示例说明：API 密钥来自模型服务商，请勿泄露；调用频次限制为单小时最大调用次数。</p>
              </div>
              <el-button type="primary" :icon="Plus" @click="openApiDialog('create','customer')">新增 API</el-button>
            </div>
          </template>

          <el-table :data="allApis" border style="width: 100%">
            <el-table-column prop="name" label="API 名称" width="180" />
            <el-table-column prop="model" label="模型" width="160" />
            <el-table-column label="所属功能" width="160">
              <template #default="{ row }">
                <el-tag size="small">{{ featureName(row.feature) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="endpoint" label="请求地址" min-width="200" show-overflow-tooltip />
            <el-table-column label="超时/重试" width="140">
              <template #default="{ row }">{{ row.timeout }}s / {{ row.retry }}</template>
            </el-table-column>
            <el-table-column label="频次/并发" width="140">
              <template #default="{ row }">{{ row.rateLimit }}/h / {{ row.concurrency }}</template>
            </el-table-column>
            <el-table-column label="默认" width="80">
              <template #default="{ row }">
                <el-tag v-if="row.isDefault" type="success" size="small">默认</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-switch v-model="row.enabled" @change="() => toggleApi(row)" />
              </template>
            </el-table-column>
            <el-table-column label="上次测试" width="120">
              <template #default="{ row }">
                <el-tag v-if="row.lastTest === 'success'" type="success" size="small">成功</el-tag>
                <el-tag v-else-if="row.lastTest === 'fail'" type="danger" size="small">失败</el-tag>
                <span v-else>未测试</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="280" fixed="right">
              <template #default="{ row }">
                <el-button size="small" link @click="testApi(row)" :loading="apiTestLoading">测试连接</el-button>
                <el-button size="small" link type="primary" @click="setDefaultApi(row.feature, row.id)">设为默认</el-button>
                <el-button size="small" link type="primary" @click="openApiDialog('edit', row.feature, row.id)" :icon="Edit">编辑</el-button>
                <el-button size="small" link type="danger" :icon="Delete" @click="deleteApi(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane name="logs">
        <template #label>
          <span class="tab-label"><el-icon><Tickets /></el-icon> 操作日志</span>
        </template>
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <div>
                <h3>操作审计</h3>
                <p class="hint">添加/修改/启用/禁用均需记录操作人、时间与内容</p>
              </div>
              <el-button :icon="Download" @click="exportLogs">导出日志</el-button>
            </div>
          </template>
          <el-table :data="operationLogs" border>
            <el-table-column prop="time" label="时间" width="180" />
            <el-table-column prop="operator" label="操作人" width="120" />
            <el-table-column prop="action" label="动作" width="140" />
            <el-table-column prop="detail" label="详情" />
          </el-table>
          <div v-if="operationLogs.length === 0" class="empty-log">暂无操作，所有关键操作将自动记录</div>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="apiDialogVisible" :title="apiDialogMode === 'create' ? '新增 API' : '编辑 API'" width="640px">
      <el-form label-width="140px" class="config-form">
        <el-form-item label="所属功能">
          <el-tag>{{ featureName(apiDialogFeature) }}</el-tag>
        </el-form-item>
        <el-form-item label="API 名称" required>
          <el-input v-model="apiForm.name" placeholder="如 Qwen 问答" />
        </el-form-item>
        <el-form-item label="模型标识" required>
          <el-input v-model="apiForm.model" placeholder="模型名称或版本" />
        </el-form-item>
        <el-form-item label="请求地址" required>
          <el-input v-model="apiForm.endpoint" placeholder="API Endpoint" />
        </el-form-item>
        <el-form-item label="API 密钥" required>
          <el-input v-model="apiForm.apiKey" type="password" show-password placeholder="请输入密钥" />
          <div class="hint">API密钥：模型服务商提供的调用凭证，请勿泄露</div>
        </el-form-item>
        <el-form-item label="请求头">
          <el-input v-model="apiForm.headers" placeholder="k:v 多项用逗号分隔" />
        </el-form-item>
        <el-row :gutter="10">
          <el-col :span="12">
            <el-form-item label="超时时间 (秒)">
              <el-input-number v-model="apiForm.timeout" :min="5" :max="120" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="重试次数">
              <el-input-number v-model="apiForm.retry" :min="0" :max="5" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="10">
          <el-col :span="12">
            <el-form-item label="调用频次 / 小时">
              <el-input-number v-model="apiForm.rateLimit" :min="10" :max="5000" />
              <div class="hint">调用频次限制：单小时最大调用次数</div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="并发限制">
              <el-input-number v-model="apiForm.concurrency" :min="1" :max="200" />
              <div class="hint">并发限制：同时发起的最大请求数</div>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="设为默认">
          <el-switch v-model="apiForm.isDefault" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="apiForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="apiDialogVisible = false">取消</el-button>
        <el-button type="primary" :icon="Check" @click="saveApi">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
export default defineComponent({ name: 'AIConfig' })
</script>

<style scoped>
.ai-settings-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  padding: 16px 20px;
  border-radius: 6px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}
.page-header h1 { margin: 0; font-size: 22px; }
.subtitle { margin: 6px 0 0; color: #909399; font-size: 13px; }
.overview-card { margin-bottom: 10px; }
.overview-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.card-head { display: flex; justify-content: space-between; align-items: center; }
.card-title { margin: 0; font-size: 16px; font-weight: 600; }
.card-sub { margin: 6px 0 0; color: #909399; font-size: 13px; }
.card-metrics { display: flex; gap: 24px; margin: 14px 0; }
.metric-value { margin: 0; font-size: 22px; font-weight: bold; }
.metric-value.warn { color: #F56C6C; }
.metric-label { margin: 4px 0 0; color: #909399; font-size: 12px; }
.card-actions { display: flex; gap: 10px; }
.tab-label { display: inline-flex; align-items: center; gap: 6px; }
.feature-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.title-block h3 { margin: 0 0 4px; }
.title-block p { margin: 0; color: #909399; }
.feature-body { display: flex; flex-direction: column; gap: 12px; }
.config-card { width: 100%; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-title-row { font-weight: 600; }
.config-form { padding: 10px 0 0; }
.hint { color: #909399; font-size: 12px; margin-left: 6px; }
.empty-log { text-align: center; padding: 20px; color: #909399; }
</style>
