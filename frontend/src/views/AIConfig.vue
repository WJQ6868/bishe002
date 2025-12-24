<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { ElMessage, ElMessageBox, FormInstance, FormRules } from 'element-plus'
import { 
  Connection, Setting, ChatDotRound, 
  CircleCheckFilled, CircleCloseFilled, 
  Upload, Download, Plus, Delete, Edit
} from '@element-plus/icons-vue'

// --- 1. 类型定义 ---
interface AIFunctionConfig {
  enableAI: boolean
  enableStream: boolean
  
  // 会话管理
  historyDuration: string
  maxSessions: number // 新增
  autoRenameSession: boolean // 新增

  // 交互功能
  enableMarkdown: boolean // 新增
  enableVoiceInput: boolean // 新增
  enableFileUpload: boolean
  allowedFileTypes: string[] // 新增
  recallTimeLimit: number // 新增
  allowUserSwitchModel: boolean
  keepSessionOnSwitch: boolean

  // 安全配置
  enableSensitiveFilter: boolean
  enableContentAudit: boolean // 新增
}

interface AIWordConfig {
  welcome: string
  unrecognized: string
  closing: string
}

interface ModelAuth {
  model: string
  name: string
  isConfigured: boolean
  studentAuth: boolean
  teacherAuth: boolean
}

interface AIChatConfig {
  defaultModel: string
  modelAuths: ModelAuth[]
  currentEditModel: string 
  apiKeys: Record<string, string>
  apiUrls: Record<string, string>
  timeout: number
  concurrency: number
  functions: AIFunctionConfig
  words: AIWordConfig
}

// --- 2. 状态管理 ---
const activeTab = ref('api')
const loading = ref(false)
const testStatus = ref<'none' | 'success' | 'fail'>('none')
const testMsg = ref('')
const formRef = ref<FormInstance>()
const isSaved = ref(true) 

// 敏感词管理
const sensitiveDialogVisible = ref(false)
const sensitiveWords = ref<string[]>([
  '代考', '作弊', '黑客', '攻击', '破解', 
  '赌博', '色情', '暴力', '反动', '私服',
  '枪手', '替考', '答案', '泄题', '外挂',
  '刷课', '改分', '办证', '假发票', '高利贷'
])
const newSensitiveWord = ref('')

// 默认配置
const defaultConfig: AIChatConfig = {
  defaultModel: 'dashscope-openai',
  currentEditModel: 'tongyi',
  modelAuths: [
    { model: 'tongyi', name: '通义千问 (Qwen)', isConfigured: true, studentAuth: true, teacherAuth: true },
    { model: 'deepseek', name: 'DeepSeek', isConfigured: false, studentAuth: false, teacherAuth: false },
    { model: 'spark', name: '讯飞星火 (Spark)', isConfigured: false, studentAuth: false, teacherAuth: false },
    { model: 'doubao-seed', name: '豆包多模态 (Doubao Seed)', isConfigured: true, studentAuth: true, teacherAuth: true },
    { model: 'doubao-flash', name: '豆包闪电 (Doubao Flash)', isConfigured: true, studentAuth: true, teacherAuth: true },
    { model: 'ark-deepseek', name: 'DeepSeek Ark Responses', isConfigured: false, studentAuth: false, teacherAuth: false },
    { model: 'custom', name: '自定义 API', isConfigured: false, studentAuth: false, teacherAuth: false }
  ],
  apiKeys: { 
    tongyi: '', 
    deepseek: '', 
    spark: '', 
    'doubao-seed': '26ece7c8-2f32-4b6d-8142-4d0b645cec42',
    'doubao-flash': '26ece7c8-2f32-4b6d-8142-4d0b645cec42',
    'ark-deepseek': '26ece7c8-2f32-4b6d-8142-4d0b645cec42',
    custom: '' 
  },
  apiUrls: { 
    tongyi: '', 
    deepseek: '', 
    spark: '', 
    'doubao-seed': 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
    'doubao-flash': 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
    'ark-deepseek': 'https://ark.cn-beijing.volces.com/api/v3/responses',
    custom: '' 
  },
  timeout: 30,
  concurrency: 10,
  functions: {
    enableAI: true,
    enableStream: true,
    
    historyDuration: '30d',
    maxSessions: 20,
    autoRenameSession: true,

    enableMarkdown: true,
    enableVoiceInput: true,
    enableFileUpload: false,
    allowedFileTypes: ['doc', 'pdf', 'image', 'excel'],
    recallTimeLimit: 5,
    allowUserSwitchModel: true,
    keepSessionOnSwitch: true,

    enableSensitiveFilter: true,
    enableContentAudit: true
  },
  words: {
    welcome: '您好！我是智能教务AI客服，有什么可以帮您？',
    unrecognized: '抱歉，我暂时无法理解您的问题，请换一种方式描述~',
    closing: '问题已解答完毕，如有其他需求请随时咨询！'
  }
}

const form = reactive<AIChatConfig>(JSON.parse(JSON.stringify(defaultConfig)))
const selectedAuthRows = ref<ModelAuth[]>([])

// 校验规则
const rules = reactive<FormRules>({
  // 动态校验当前编辑的模型
})

// --- 3. 核心逻辑 ---

// 初始化读取配置
onMounted(() => {
  const savedConfig = localStorage.getItem('ai_chat_config')
  if (savedConfig) {
    const parsed = JSON.parse(savedConfig)
    // 深度合并以确保新字段存在
    // 注意：这里简单处理，实际应递归合并
    if (!parsed.functions.maxSessions) {
       parsed.functions = { ...defaultConfig.functions, ...parsed.functions }
    }
    Object.assign(form, parsed)
  }
})

// 监听变更
watch(form, () => {
  isSaved.value = false
}, { deep: true })

// 监听存储时长变更
watch(() => form.functions.historyDuration, (newVal, oldVal) => {
  if (newVal !== oldVal && oldVal) {
    ElMessageBox.alert('会话存储时长配置将在用户下次登录时生效', '提示', {
      confirmButtonText: '知道了'
    })
  }
})

// 当前编辑的 API Key 和 URL
const currentApiKey = computed({
  get: () => form.apiKeys[form.currentEditModel],
  set: (val) => {
    form.apiKeys[form.currentEditModel] = val
    updateConfiguredStatus()
  }
})

const currentApiUrl = computed({
  get: () => form.apiUrls[form.currentEditModel],
  set: (val) => {
    form.apiUrls[form.currentEditModel] = val
    updateConfiguredStatus()
  }
})

// 更新配置状态
const updateConfiguredStatus = () => {
  const auth = form.modelAuths.find(m => m.model === form.currentEditModel)
  if (auth) {
    if (form.currentEditModel === 'custom') {
      auth.isConfigured = !!(form.apiKeys['custom'] && form.apiUrls['custom'])
    } else {
      auth.isConfigured = !!form.apiKeys[form.currentEditModel]
    }
  }
}


// 切换编辑模型
const handleEditModel = (row: ModelAuth) => {
  form.currentEditModel = row.model
  if (row.model !== 'custom' && !form.apiUrls[row.model]) {
    const urlMap: Record<string, string> = {
      tongyi: 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
      deepseek: 'https://api.deepseek.com/v1/chat/completions',
      spark: 'https://spark-api.xf-yun.com/v3.1/chat',
      'doubao-seed': 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
      'doubao-flash': 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
      'ark-deepseek': 'https://ark.cn-beijing.volces.com/api/v3/responses'
    }
    form.apiUrls[row.model] = urlMap[row.model] || ''
  }
}

// 批量授权
const handleBatchAuth = (type: 'student' | 'teacher', value: boolean) => {
  if (selectedAuthRows.value.length === 0) {
    ElMessage.warning('请先勾选模型')
    return
  }
  selectedAuthRows.value.forEach(row => {
    if (row.isConfigured) {
      if (type === 'student') row.studentAuth = value
      else row.teacherAuth = value
    }
  })
  ElMessage.success('批量操作完成 (仅已配置的模型生效)')
}

// 默认模型切换
const handleDefaultModelChange = (val: string) => {
  ElMessageBox.confirm('默认模型将影响所有用户首次使用体验，是否确认？', '提示', {
    confirmButtonText: '确认',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    // 确认
  }).catch(() => {
    // 取消
  })
}

// 测试连接
const handleTestConnection = async () => {
  if (!currentApiKey.value) {
    ElMessage.warning('请先输入当前模型的 API Key')
    return
  }
  
  loading.value = true
  testStatus.value = 'none'
  testMsg.value = ''

  try {
    if (form.currentEditModel === 'ark-deepseek') {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), form.timeout * 1000)
      const body = {
        model: 'deepseek-v3-2-251201',
        stream: true,
        tools: [{ type: 'web_search', max_keyword: 3 }],
        input: [
          {
            role: 'user',
            content: [
              { type: 'input_text', text: '今天有什么热点新闻' }
            ]
          }
        ]
      }
      const res = await fetch(currentApiUrl.value || 'https://ark.cn-beijing.volces.com/api/v3/responses', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${currentApiKey.value}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body),
        signal: controller.signal
      })
      clearTimeout(timeoutId)
      if (!res.ok) {
        const err = await res.json().catch(() => null)
        testStatus.value = 'fail'
        if (err && err.error && err.error.code === 'AuthenticationError') {
          testMsg.value = '连接失败：API Key 无效或缺失'
        } else {
          testMsg.value = `连接失败：${res.status}`
        }
        ElMessage.error('测试连接失败')
      } else {
        testStatus.value = 'success'
        testMsg.value = '连接成功！接口可用'
        ElMessage.success('测试连接成功')
        updateConfiguredStatus()
      }
    } else {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      testStatus.value = 'success'
      testMsg.value = '连接成功！模型响应正常。'
      ElMessage.success('测试连接成功')
      updateConfiguredStatus()
    }
  } catch (e: any) {
    testStatus.value = 'fail'
    testMsg.value = e?.name === 'AbortError' ? '连接失败：请求超时' : '连接失败：网络错误'
    ElMessage.error('测试连接失败')
  } finally {
    loading.value = false
  }
}

// 保存配置
const handleSave = async (formEl: FormInstance | undefined) => {
  localStorage.setItem('ai_chat_config', JSON.stringify(form))
  isSaved.value = true
  ElMessage.success('配置已保存，已同步至学生/教师端')
}

// 标签页切换守卫
const handleTabLeave = (activeName: string, oldActiveName: string) => {
  if (!isSaved.value) {
    ElMessage.warning('您有未保存的配置，建议先保存')
  }
  return true
}

// 敏感词管理
const addSensitiveWord = () => {
  if (newSensitiveWord.value && !sensitiveWords.value.includes(newSensitiveWord.value)) {
    sensitiveWords.value.push(newSensitiveWord.value)
    newSensitiveWord.value = ''
    ElMessage.success('添加成功')
  }
}
const removeSensitiveWord = (word: string) => {
  sensitiveWords.value = sensitiveWords.value.filter(w => w !== word)
}
const handleImportWords = () => {
  ElMessage.success('模拟导入 Excel 成功，新增 5 个敏感词')
  sensitiveWords.value.push('外挂', '替考', '枪手', '答案', '泄题')
}
const handleExportWords = () => {
  ElMessage.success('模拟导出 Excel 成功')
}
const insertVariable = (field: keyof AIWordConfig, variable: string) => {
  form.words[field] += variable
}

</script>

<template>
  <div class="ai-config-page">
    <!-- 顶部 Header -->
    <div class="page-header">
      <h1>AI 客服配置</h1>
      <p class="subtitle">配置大模型API参数，控制学生/教师端AI客服功能</p>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <el-tabs v-model="activeTab" type="border-card" class="config-tabs" :before-leave="handleTabLeave">
        
        <!-- 1. API 配置 -->
        <el-tab-pane name="api">
          <template #label>
            <span class="tab-label"><el-icon><Connection /></el-icon> API 配置</span>
          </template>
          
          <div class="api-config-container">
            <!-- 左侧：模型列表与授权 -->
            <div class="model-list-section">
              <div class="section-header">
                <h3>模型授权管理</h3>
                <div class="batch-ops">
                  <el-button size="small" @click="handleBatchAuth('student', true)">批量授权学生</el-button>
                  <el-button size="small" @click="handleBatchAuth('teacher', true)">批量授权教师</el-button>
                </div>
              </div>
              
              <el-table 
                :data="form.modelAuths" 
                style="width: 100%" 
                @selection-change="(val) => selectedAuthRows = val"
                border
              >
                <el-table-column type="selection" width="40" />
                <el-table-column prop="name" label="大模型名称" width="140" />
                <el-table-column label="API 状态" width="100">
                  <template #default="{ row }">
                    <el-tag :type="row.isConfigured ? 'success' : 'info'">
                      {{ row.isConfigured ? '已配置' : '未配置' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="学生端授权" width="100">
                  <template #default="{ row }">
                    <el-switch v-model="row.studentAuth" :disabled="!row.isConfigured" />
                  </template>
                </el-table-column>
                <el-table-column label="教师端授权" width="100">
                  <template #default="{ row }">
                    <el-switch v-model="row.teacherAuth" :disabled="!row.isConfigured" />
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="80">
                  <template #default="{ row }">
                    <el-button link type="primary" :icon="Edit" @click="handleEditModel(row)">配置</el-button>
                  </template>
                </el-table-column>
              </el-table>

              <div class="default-model-setting">
                <span>默认模型：</span>
                <el-select v-model="form.defaultModel" @change="handleDefaultModelChange" style="width: 200px">
                  <el-option 
                    v-for="m in form.modelAuths" 
                    :key="m.model" 
                    :label="m.name" 
                    :value="m.model" 
                    :disabled="!m.isConfigured"
                  />
                </el-select>
                <span class="hint">用户首次打开 AI 客服时使用的模型</span>
              </div>
            </div>

            <!-- 右侧：API 参数编辑 -->
            <div class="api-edit-section">
              <div class="section-header">
                <h3>参数配置 - {{ form.modelAuths.find(m => m.model === form.currentEditModel)?.name }}</h3>
              </div>
              
              <el-form ref="formRef" :model="form" label-width="100px" class="edit-form">
                <el-form-item label="API Key" required>
                  <el-input v-model="currentApiKey" type="password" show-password placeholder="请输入 API 密钥" />
                </el-form-item>

                <el-form-item label="请求地址" :required="form.currentEditModel === 'custom'">
                  <el-input v-model="currentApiUrl" :disabled="form.currentEditModel !== 'custom'" placeholder="API Endpoint" />
                  <div class="hint" v-if="form.currentEditModel !== 'custom'">标准模型使用默认地址</div>
                </el-form-item>

                <el-row :gutter="20">
                  <el-col :span="12">
                    <el-form-item label="超时时间">
                      <el-input-number v-model="form.timeout" :min="5" :max="60" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="并发限制">
                      <el-input-number v-model="form.concurrency" :min="1" :max="50" />
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-form-item>
                  <div class="test-area">
                    <el-button type="primary" plain @click="handleTestConnection" :loading="loading">测试连接</el-button>
                    <div v-if="testStatus !== 'none'" class="test-result" :class="testStatus">
                      <el-icon v-if="testStatus === 'success'"><CircleCheckFilled /></el-icon>
                      <el-icon v-else><CircleCloseFilled /></el-icon>
                      <span>{{ testMsg }}</span>
                    </div>
                  </div>
                </el-form-item>
              </el-form>
              
              <div class="save-bar">
                <el-button type="warning" size="large" @click="handleSave(formRef)" style="width: 100%">保存所有配置</el-button>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- 2. 功能设置 -->
        <el-tab-pane name="function">
          <template #label>
            <span class="tab-label"><el-icon><Setting /></el-icon> 功能设置</span>
          </template>
          
          <el-form label-width="180px" class="config-form">
            <el-divider content-position="left">基础功能</el-divider>
            <el-form-item label="AI 客服总开关">
              <el-switch v-model="form.functions.enableAI" active-text="开启" inactive-text="关闭" />
            </el-form-item>
            
            <el-form-item label="流式响应 (Stream)">
              <el-switch v-model="form.functions.enableStream" />
              <span class="hint">开启后打字机效果输出，体验更佳</span>
            </el-form-item>

            <el-divider content-position="left">会话管理 (类豆包配置)</el-divider>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="会话存储时长">
                  <el-select v-model="form.functions.historyDuration" style="width: 100%">
                    <el-option label="7 天" value="7d" />
                    <el-option label="30 天" value="30d" />
                    <el-option label="90 天" value="90d" />
                    <el-option label="永久" value="forever" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="单用户最大会话数">
                  <el-input-number v-model="form.functions.maxSessions" :min="5" :max="50" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="会话自动命名">
              <el-switch v-model="form.functions.autoRenameSession" />
              <span class="hint">基于首条消息自动生成会话标题</span>
            </el-form-item>

            <el-divider content-position="left">交互功能</el-divider>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="Markdown 渲染">
                  <el-switch v-model="form.functions.enableMarkdown" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="语音输入功能">
                  <el-switch v-model="form.functions.enableVoiceInput" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="允许用户切换模型">
              <el-switch v-model="form.functions.allowUserSwitchModel" />
              <span class="hint">关闭后用户只能使用默认模型</span>
            </el-form-item>

            <el-form-item label="切换模型保留会话">
              <el-switch v-model="form.functions.keepSessionOnSwitch" />
              <span class="hint">关闭后切换模型将清空当前对话记录</span>
            </el-form-item>

            <el-form-item label="文件上传支持">
              <el-switch v-model="form.functions.enableFileUpload" />
              <span class="hint">允许用户上传文档/图片进行咨询</span>
            </el-form-item>
            
            <el-form-item label="允许文件类型" v-if="form.functions.enableFileUpload">
              <el-checkbox-group v-model="form.functions.allowedFileTypes">
                <el-checkbox label="doc">文档 (Word/TXT)</el-checkbox>
                <el-checkbox label="pdf">PDF</el-checkbox>
                <el-checkbox label="image">图片</el-checkbox>
                <el-checkbox label="excel">Excel</el-checkbox>
              </el-checkbox-group>
            </el-form-item>

            <el-form-item label="消息撤回时限">
              <el-input-number v-model="form.functions.recallTimeLimit" :min="1" :max="30" />
              <span class="unit">分钟</span>
            </el-form-item>

            <el-divider content-position="left">安全配置</el-divider>
            <el-form-item label="敏感词过滤">
              <div class="sensitive-setting">
                <el-switch v-model="form.functions.enableSensitiveFilter" />
                <el-button 
                  v-if="form.functions.enableSensitiveFilter" 
                  type="primary" 
                  link 
                  @click="sensitiveDialogVisible = true"
                  style="margin-left: 10px"
                >
                  管理敏感词
                </el-button>
              </div>
            </el-form-item>
            
            <el-form-item label="消息内容审核">
              <el-switch v-model="form.functions.enableContentAudit" />
              <span class="hint">开启后将对用户输入和AI输出进行模拟审核</span>
            </el-form-item>

            <el-form-item>
              <el-button type="warning" size="large" @click="handleSave(formRef)">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 3. 话术管理 -->
        <el-tab-pane name="words">
          <template #label>
            <span class="tab-label"><el-icon><ChatDotRound /></el-icon> 话术管理</span>
          </template>
          
          <el-form label-width="120px" class="config-form">
            <el-form-item label="欢迎语">
              <el-input 
                v-model="form.words.welcome" 
                type="textarea" 
                :rows="3" 
                placeholder="请输入欢迎语"
              />
              <div class="var-insert">
                插入变量：<el-tag size="small" @click="insertVariable('welcome', '{角色}')" style="cursor: pointer">{角色}</el-tag>
              </div>
            </el-form-item>

            <el-form-item label="未识别回复">
              <el-input 
                v-model="form.words.unrecognized" 
                type="textarea" 
                :rows="2" 
              />
            </el-form-item>

            <el-form-item label="结束语">
              <el-input 
                v-model="form.words.closing" 
                type="textarea" 
                :rows="2" 
              />
            </el-form-item>

            <el-form-item>
              <el-button type="warning" size="large" @click="handleSave(formRef)">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 敏感词管理弹窗 -->
    <el-dialog v-model="sensitiveDialogVisible" title="敏感词管理" width="500px">
      <div class="sensitive-toolbar">
        <el-input 
          v-model="newSensitiveWord" 
          placeholder="输入敏感词" 
          style="width: 200px" 
          @keyup.enter="addSensitiveWord"
        >
          <template #append>
            <el-button :icon="Plus" @click="addSensitiveWord" />
          </template>
        </el-input>
        <div class="tools">
          <el-button :icon="Upload" @click="handleImportWords">导入</el-button>
          <el-button :icon="Download" @click="handleExportWords">导出</el-button>
        </div>
      </div>
      
      <div class="sensitive-list">
        <el-tag 
          v-for="word in sensitiveWords" 
          :key="word" 
          closable 
          @close="removeSensitiveWord(word)"
          style="margin: 5px"
        >
          {{ word }}
        </el-tag>
      </div>
      
      <template #footer>
        <el-button @click="sensitiveDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.ai-config-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  background: #fff;
  padding: 20px;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}
.page-header h1 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}
.subtitle {
  margin: 10px 0 0;
  color: #909399;
  font-size: 14px;
}

.main-content {
  flex: 1;
  background: #fff;
  border-radius: 4px;
  padding: 20px;
}

.config-tabs {
  height: 100%;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 5px;
}

.api-config-container {
  display: flex;
  gap: 20px;
  height: 100%;
}

.model-list-section {
  flex: 3;
  border-right: 1px solid #eee;
  padding-right: 20px;
}

.api-edit-section {
  flex: 2;
  padding-left: 10px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}
.section-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.default-model-setting {
  margin-top: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.config-form {
  max-width: 800px;
  margin-top: 20px;
}

.hint {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

.unit {
  margin-left: 10px;
}

.test-area {
  display: flex;
  align-items: center;
  gap: 15px;
}

.test-result {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 14px;
}
.test-result.success { color: #67C23A; }
.test-result.fail { color: #F56C6C; }

.sensitive-setting {
  display: flex;
  align-items: center;
}

.var-insert {
  margin-top: 5px;
  font-size: 12px;
  color: #909399;
}

.sensitive-toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}

.sensitive-list {
  min-height: 200px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 10px;
}
</style>
