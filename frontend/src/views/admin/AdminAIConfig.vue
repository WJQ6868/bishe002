<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Delete, Edit, Link } from '@element-plus/icons-vue'
import type {
  AiKbDocument,
  AiKnowledgeBaseItem,
  AiModelApiCreate,
  AiModelApiItem,
  AiWorkflowAppItem
} from '@/api/adminAi'
import { adminAiApi } from '@/api/adminAi'

type AppCode = string

const activeTab = ref<'models' | 'kb' | 'apps'>('models')
const loading = ref(false)

const modelApis = ref<AiModelApiItem[]>([])
const modelDialogVisible = ref(false)
const modelDialogMode = ref<'create' | 'edit'>('create')
const editingModelId = ref<number | null>(null)
const modelForm = reactive<AiModelApiCreate>({
  name: '',
  provider: 'dashscope_openai',
  provider_brand: 'OpenAI',
  model_name: '',
  endpoint: '',
  api_key: '',
  api_header: '',
  api_version: '',
  timeout_seconds: 30,
  quota_per_hour: 0,
  temperature: 0.7,
  max_output_tokens: 2048,
  enabled: true,
  is_default: false
})

const resetModelForm = () => {
  Object.assign(modelForm, {
    name: '',
    provider: 'dashscope_openai',
    provider_brand: 'OpenAI',
    model_name: '',
    endpoint: '',
    api_key: '',
    api_header: '',
    api_version: '',
    timeout_seconds: 30,
    quota_per_hour: 0,
    temperature: 0.7,
    max_output_tokens: 2048,
    enabled: true,
    is_default: false
  })
}

const workflowKbs = ref<AiKnowledgeBaseItem[]>([])
const selectedKbId = ref<number | null>(null)
const workflowDocs = ref<AiKbDocument[]>([])

const kbDialogVisible = ref(false)
const kbDialogMode = ref<'create' | 'edit'>('create')
const kbForm = reactive({
  id: 0,
  name: '',
  description: '',
  feature: 'course_assistant',
  is_default: false
})

const uploadDialogVisible = ref(false)
const uploadTitle = ref('')
const uploadFile = ref<File | null>(null)
const workflowApps = ref<AiWorkflowAppItem[]>([])
const editingAppCode = ref<AppCode>('customer_service')
const appForm = reactive({
  name: '',
  knowledge_base_id: null as number | null,
  model_api_id: null as number | null,
  status: 'enabled',
  welcome_str: '',
  search_placeholder: '',
  system_prompt_template: '',
  recommend_text: ''
})

// 新建工作流
const newAppDialogVisible = ref(false)
const newAppForm = reactive({
  code: '',
  name: '',
  type: 'customer_service'
})

// 模型手工测试
const testDialogVisible = ref(false)
const testPrompt = ref('你好，请自我介绍一下。')
const testResult = ref('')
const testApiKey = ref('')
const testLoading = ref(false)
const testingModel = ref<AiModelApiItem | null>(null)

const currentApp = computed(() => workflowApps.value.find(app => app.code === editingAppCode.value))
const showCustomerFields = computed(() => (currentApp.value?.type || editingAppCode.value) === 'customer_service')
const kbNameById = (id?: number | null) => workflowKbs.value.find(k => k.id === id)?.name || '未绑定'
const modelNameById = (id?: number | null) => modelApis.value.find(m => m.id === id)?.name || '未绑定'
const typeLabel = (t: string) => {
  if (t === 'customer_service') return 'AI 客服'
  if (t === 'course_assistant') return 'AI 课程助手'
  if (t === 'lesson_plan') return '智能教案'
  return t
}

const syncCurrentApp = () => {
  const app = currentApp.value
  if (!app) {
    appForm.name = ''
    appForm.knowledge_base_id = null
    appForm.model_api_id = null
    appForm.status = 'enabled'
    appForm.welcome_str = ''
    appForm.search_placeholder = ''
    appForm.system_prompt_template = ''
    appForm.recommend_text = ''
    return
  }
  appForm.name = app.name
  appForm.knowledge_base_id = app.knowledge_base_id ?? null
  appForm.model_api_id = app.model_api_id ?? null
  appForm.status = app.status || 'enabled'
  const settings = app.settings || {}
  appForm.welcome_str = settings.welcome_str || ''
  appForm.search_placeholder = settings.search_placeholder || ''
  appForm.system_prompt_template = settings.system_prompt_template || ''
  const recommend = Array.isArray(settings.recommend_questions) ? settings.recommend_questions : []
  appForm.recommend_text = (recommend as string[]).join('\n')
}

watch(currentApp, () => syncCurrentApp(), { immediate: true })
watch(selectedKbId, async (id) => {
  if (id) {
    workflowDocs.value = await adminAiApi.listWorkflowDocuments(id)
  } else {
    workflowDocs.value = []
  }
})

const loadModelApis = async () => {
  modelApis.value = await adminAiApi.listModelApis()
}

const loadWorkflowDocs = async (kbId: number) => {
  workflowDocs.value = await adminAiApi.listWorkflowDocuments(kbId)
}

const refreshWorkflow = async () => {
  workflowKbs.value = await adminAiApi.listWorkflowKnowledgeBases()
  if (!workflowKbs.value.length) {
    selectedKbId.value = null
    workflowDocs.value = []
  } else if (!workflowKbs.value.some(kb => kb.id === selectedKbId.value)) {
    selectedKbId.value = workflowKbs.value[0].id
  } else if (selectedKbId.value) {
    await loadWorkflowDocs(selectedKbId.value)
  }
  workflowApps.value = await adminAiApi.listWorkflowApps()
  if (!workflowApps.value.some(a => a.code === editingAppCode.value) && workflowApps.value.length) {
    editingAppCode.value = workflowApps.value[0].code
  }
  syncCurrentApp()
}
const refreshAll = async () => {
  loading.value = true
  try {
    await loadModelApis()
    await refreshWorkflow()
    if (selectedKbId.value) {
      await loadWorkflowDocs(selectedKbId.value)
    }
  } finally {
    loading.value = false
  }
}

onMounted(refreshAll)

const openCreateModel = () => {
  modelDialogMode.value = 'create'
  editingModelId.value = null
  resetModelForm()
  modelDialogVisible.value = true
}

const openEditModel = (row: AiModelApiItem) => {
  modelDialogMode.value = 'edit'
  editingModelId.value = row.id
  Object.assign(modelForm, {
    name: row.name,
    provider: row.provider,
    provider_brand: row.provider_brand || 'OpenAI',
    model_name: row.model_name,
    endpoint: row.endpoint,
    api_key: '',
    api_header: row.api_header || '',
    api_version: row.api_version || '',
    timeout_seconds: row.timeout_seconds,
    quota_per_hour: row.quota_per_hour,
    temperature: row.temperature ?? 0.7,
    max_output_tokens: row.max_output_tokens ?? 2048,
    enabled: row.enabled,
    is_default: row.is_default
  })
  modelDialogVisible.value = true
}

const saveModel = async () => {
  if (!modelForm.name.trim()) {
    ElMessage.error('请输入模型名称')
    return
  }
  if (!modelForm.model_name.trim()) {
    ElMessage.error('请输入模型标识')
    return
  }
  if (!modelForm.endpoint.trim()) {
    ElMessage.error('请输入接口地址')
    return
  }
  if (modelDialogMode.value === 'create' && !modelForm.api_key.trim()) {
    ElMessage.error('请输入 API Key')
    return
  }
  loading.value = true
  try {
    if (modelDialogMode.value === 'create') {
      await adminAiApi.createModelApi(modelForm)
      ElMessage.success('已新增模型')
    } else {
      const payload: Partial<AiModelApiCreate> = { ...modelForm }
      if (!payload.api_key?.trim()) delete payload.api_key
      await adminAiApi.updateModelApi(editingModelId.value!, payload)
      ElMessage.success('已保存模型')
    }
    modelDialogVisible.value = false
    await refreshAll()
  } finally {
    loading.value = false
  }
}

const testModel = (row?: AiModelApiItem) => {
  testingModel.value = row ?? null
  testPrompt.value = '你好，请自我介绍一下。'
  testApiKey.value = ''
  testResult.value = ''
  testDialogVisible.value = true
}

const runModelTest = async () => {
  const model = testingModel.value
  const provider: any = model?.provider ?? modelForm.provider
  const endpoint = model?.endpoint ?? modelForm.endpoint
  const modelName = model?.model_name ?? modelForm.model_name
  const timeout = model?.timeout_seconds ?? modelForm.timeout_seconds
  const apiKey = (testApiKey.value || (!model ? modelForm.api_key : '')).trim()

  if (!provider || !endpoint || !modelName) {
    ElMessage.error('请先填写完整的模型信息')
    return
  }
  if (!apiKey && !model?.id) {
    ElMessage.error('请输入 API Key 用于本次测试')
    return
  }

  testLoading.value = true
  try {
    const result = await adminAiApi.testModelApi({
      api_id: model?.id,
      provider,
      endpoint,
      model_name: modelName,
      api_key: apiKey,
      timeout_seconds: timeout,
      prompt: testPrompt.value
    })
    testResult.value = result.output || result.message || ''
    result.ok ? ElMessage.success(result.message) : ElMessage.error(result.message)
  } finally {
    testLoading.value = false
  }
}
const removeModel = async (row: AiModelApiItem) => {
  await ElMessageBox.confirm(`确认删除模型「${row.name}」？`, '提示', { type: 'warning' })
  loading.value = true
  try {
    await adminAiApi.deleteModelApi(row.id)
    ElMessage.success('已删除模型')
    await refreshAll()
  } finally {
    loading.value = false
  }
}

const openCreateKb = () => {
  kbDialogMode.value = 'create'
  kbForm.id = 0
  kbForm.name = ''
  kbForm.description = ''
  kbForm.feature = 'course_assistant'
  kbForm.is_default = false
  kbDialogVisible.value = true
}

const openEditKb = (row: AiKnowledgeBaseItem) => {
  kbDialogMode.value = 'edit'
  kbForm.id = row.id
  kbForm.name = row.name
  kbForm.description = row.description || ''
  kbForm.feature = row.feature || 'course_assistant'
  kbForm.is_default = row.is_default
  kbDialogVisible.value = true
}

const saveKb = async () => {
  if (!kbForm.name.trim()) {
    ElMessage.error('请输入知识库名称')
    return
  }
  loading.value = true
  try {
    const payload = {
      name: kbForm.name,
      description: kbForm.description,
      feature: kbForm.feature,
      is_default: kbForm.is_default
    }
    if (kbDialogMode.value === 'create') {
      await adminAiApi.createWorkflowKnowledgeBase(payload)
      ElMessage.success('已创建知识库')
    } else {
      await adminAiApi.updateWorkflowKnowledgeBase(kbForm.id, payload)
      ElMessage.success('已更新知识库')
    }
    kbDialogVisible.value = false
    await refreshWorkflow()
  } finally {
    loading.value = false
  }
}

const deleteKb = async (row: AiKnowledgeBaseItem) => {
  await ElMessageBox.confirm(`确认删除知识库「${row.name}」？`, '提示', { type: 'warning' })
  loading.value = true
  try {
    await adminAiApi.deleteWorkflowKnowledgeBase(row.id)
    if (selectedKbId.value === row.id) {
      selectedKbId.value = workflowKbs.value.find(kb => kb.id !== row.id)?.id || null
    }
    await refreshWorkflow()
    ElMessage.success('已删除知识库')
  } finally {
    loading.value = false
  }
}

const openUploadDoc = () => {
  if (!selectedKbId.value) {
    ElMessage.warning('请先选择知识库')
    return
  }
  uploadTitle.value = ''
  uploadFile.value = null
  uploadDialogVisible.value = true
}

const handleUploadFileChange = (e: Event) => {
  const files = (e.target as HTMLInputElement).files
  uploadFile.value = files && files.length ? files[0] : null
}

const doUploadDoc = async () => {
  if (!selectedKbId.value || !uploadFile.value) {
    ElMessage.error('请选择文件')
    return
  }
  loading.value = true
  try {
    await adminAiApi.uploadWorkflowDocument(
      selectedKbId.value,
      uploadTitle.value || uploadFile.value.name,
      uploadFile.value
    )
    uploadDialogVisible.value = false
    await loadWorkflowDocs(selectedKbId.value)
    ElMessage.success('上传成功')
  } finally {
    loading.value = false
  }
}

const deleteDoc = async (doc: AiKbDocument) => {
  await ElMessageBox.confirm(`确认删除文档「${doc.title}」？`, '提示', { type: 'warning' })
  loading.value = true
  try {
    await adminAiApi.deleteWorkflowDocument(doc.id)
    if (selectedKbId.value) {
      await loadWorkflowDocs(selectedKbId.value)
    }
    ElMessage.success('已删除文档')
  } finally {
    loading.value = false
  }
}

const previewDoc = (doc: AiKbDocument) => {
  window.open(doc.url, '_blank')
}

const selectKb = (id: number) => {
  selectedKbId.value = id
}

const saveApp = async () => {
  const payload: any = {
    name: appForm.name,
    knowledge_base_id: appForm.knowledge_base_id,
    model_api_id: appForm.model_api_id,
    status: appForm.status
  }
  if (showCustomerFields.value) {
    payload.settings = {
      welcome_str: appForm.welcome_str,
      search_placeholder: appForm.search_placeholder,
      system_prompt_template: appForm.system_prompt_template,
      recommend_questions: appForm.recommend_text
        .split('\n')
        .map(item => item.trim())
        .filter(Boolean)
        .slice(0, 12)
    }
  }
  loading.value = true
  try {
    await adminAiApi.updateWorkflowApp(editingAppCode.value, payload)
    ElMessage.success('已保存工作流')
    await refreshWorkflow()
  } finally {
    loading.value = false
  }
}

const openNewWorkflow = () => {
  newAppForm.code = ''
  newAppForm.type = 'customer_service'
  newAppForm.name = ''
  newAppDialogVisible.value = true
}

const createWorkflow = async () => {
  if (!newAppForm.code.trim() || !newAppForm.name.trim()) {
    ElMessage.error('请输入工作流编码和名称')
    return
  }
  loading.value = true
  try {
    await adminAiApi.createWorkflowApp({
      code: newAppForm.code.trim(),
      type: newAppForm.type,
      name: newAppForm.name.trim(),
      status: 'enabled',
      knowledge_base_id: selectedKbId.value,
      model_api_id: appForm.model_api_id,
      settings: showCustomerFields.value
        ? {
            welcome_str: appForm.welcome_str,
            search_placeholder: appForm.search_placeholder,
            system_prompt_template: appForm.system_prompt_template,
            recommend_questions: appForm.recommend_text
              .split('\n')
              .map(i => i.trim())
              .filter(Boolean)
              .slice(0, 12)
          }
        : {}
    })
    ElMessage.success('已创建工作流')
    newAppDialogVisible.value = false
    await refreshWorkflow()
  } finally {
    loading.value = false
  }
}

const deleteWorkflow = async (code: string) => {
  await ElMessageBox.confirm(`确认删除工作流「${code}」？`, '提示', { type: 'warning' })
  loading.value = true
  try {
    await adminAiApi.deleteWorkflowApp(code)
    if (editingAppCode.value === code) {
      editingAppCode.value = workflowApps.value.find(a => a.code !== code)?.code || 'customer_service'
      syncCurrentApp()
    }
    await refreshWorkflow()
    ElMessage.success('已删除')
  } finally {
    loading.value = false
  }
}
</script>
<template>
  <div class="admin-ai-config">
    <div class="page-header">
      <div>
        <h2>AI 设置</h2>
        <p class="sub">管理大模型、知识库与 AI 工作流</p>
      </div>
      <el-button :icon="Refresh" @click="refreshAll" :loading="loading">刷新</el-button>
    </div>

    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="模型管理" name="models">
        <div class="toolbar">
          <el-button type="primary" :icon="Plus" @click="openCreateModel">新增模型</el-button>
        </div>
        <el-table :data="modelApis" border v-loading="loading">
          <el-table-column prop="name" label="名称" min-width="180" />
          <el-table-column prop="provider" label="提供商" width="160" />
          <el-table-column prop="model_name" label="模型标识" width="200" />
          <el-table-column prop="endpoint" label="接口地址" min-width="260" show-overflow-tooltip />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '启用' : '停用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="默认" width="90">
            <template #default="{ row }">
              <el-tag v-if="row.is_default" type="success" size="small">默认</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="260" fixed="right">
            <template #default="{ row }">
              <el-button size="small" link @click="testModel(row)">测试</el-button>
              <el-button size="small" link type="primary" :icon="Edit" @click="openEditModel(row)">编辑</el-button>
              <el-button size="small" link type="danger" :icon="Delete" @click="removeModel(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="知识库管理" name="kb">
        <div class="kb-toolbar">
          <el-button type="primary" :icon="Plus" @click="openCreateKb">新建知识库</el-button>
          <el-button :icon="Refresh" @click="refreshWorkflow">刷新</el-button>
        </div>
        <el-table :data="workflowKbs" border>
          <el-table-column prop="name" label="名称" min-width="180" />
          <el-table-column prop="feature" label="适用场景" width="160" />
          <el-table-column prop="document_count" label="文档数" width="120" />
          <el-table-column prop="chunk_count" label="片段数" width="120" />
          <el-table-column prop="updated_at" label="更新时间" width="180" />
          <el-table-column label="操作" width="240" fixed="right">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="selectKb(row.id)">查看文档</el-button>
              <el-button size="small" link :icon="Edit" @click="openEditKb(row)">编辑</el-button>
              <el-button size="small" link type="danger" :icon="Delete" @click="deleteKb(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="doc-header">
          <div class="doc-title">知识库文档</div>
          <div class="doc-actions">
            <el-select v-model="selectedKbId" placeholder="选择知识库" style="min-width: 220px">
              <el-option v-for="kb in workflowKbs" :key="kb.id" :label="kb.name" :value="kb.id" />
            </el-select>
            <el-button type="primary" :icon="Plus" :disabled="!selectedKbId" @click="openUploadDoc">上传文档</el-button>
          </div>
        </div>

        <el-table :data="workflowDocs" border>
          <el-table-column prop="title" label="标题" min-width="200" />
          <el-table-column prop="file_ext" label="格式" width="80" />
          <el-table-column prop="chunk_count" label="片段数" width="100" />
          <el-table-column prop="created_at" label="创建时间" width="180" />
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <el-button size="small" link :icon="Link" @click="previewDoc(row)">预览</el-button>
              <el-button size="small" link type="danger" :icon="Delete" @click="deleteDoc(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="AI 工作流" name="apps">
        <el-card shadow="never" style="margin-bottom: 16px;">
          <div style="font-weight: 600; margin-bottom: 8px;">已保存工作流（管理员可见）</div>
          <div style="margin-bottom: 8px;">
            <el-button type="primary" size="small" :icon="Plus" @click="openNewWorkflow">新建工作流</el-button>
          </div>
          <el-table :data="workflowApps" size="small" border>
            <el-table-column prop="name" label="名称" min-width="140" />
            <el-table-column prop="type" label="类型" width="140">
              <template #default="{ row }">{{ typeLabel(row.type) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 'enabled' ? 'success' : 'info'" size="small">
                  {{ row.status === 'enabled' ? '启用' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="绑定知识库" min-width="180">
              <template #default="{ row }">
                {{ kbNameById(row.knowledge_base_id) }}
              </template>
            </el-table-column>
            <el-table-column label="使用模型" min-width="180">
              <template #default="{ row }">
                {{ modelNameById(row.model_api_id) }}
              </template>
            </el-table-column>
            <el-table-column prop="updated_at" label="更新时间" width="180" />
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button size="small" link type="primary" @click="editingAppCode = row.code; syncCurrentApp()">编辑</el-button>
                <el-button size="small" link type="danger" @click="deleteWorkflow(row.code)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-radio-group v-model="editingAppCode" style="margin-bottom: 16px;">
          <el-radio-button label="customer_service">AI 客服</el-radio-button>
          <el-radio-button label="course_assistant">AI 课程助手</el-radio-button>
          <el-radio-button label="lesson_plan">智能教案</el-radio-button>
        </el-radio-group>

        <el-form label-width="120px">
          <el-form-item label="名称">
            <el-input v-model="appForm.name" placeholder="应用名称" />
          </el-form-item>
          <el-form-item label="绑定知识库">
            <el-select v-model="appForm.knowledge_base_id" placeholder="选择知识库" style="width: 320px">
              <el-option v-for="kb in workflowKbs" :key="kb.id" :label="kb.name" :value="kb.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="使用模型">
            <el-select v-model="appForm.model_api_id" placeholder="选择模型" style="width: 320px">
              <el-option v-for="m in modelApis" :key="m.id" :label="`${m.name} · ${m.model_name}`" :value="m.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-switch v-model="appForm.status" active-value="enabled" inactive-value="disabled" />
          </el-form-item>

          <template v-if="showCustomerFields">
            <el-form-item label="欢迎语">
              <el-input type="textarea" :rows="2" v-model="appForm.welcome_str" placeholder="进入对话时展示" />
            </el-form-item>
            <el-form-item label="推荐问题">
              <el-input type="textarea" :rows="4" v-model="appForm.recommend_text" placeholder="每行一个推荐问题，最多 12 条" />
            </el-form-item>
            <el-form-item label="输入占位符">
              <el-input v-model="appForm.search_placeholder" placeholder="例如：请输入问题" />
            </el-form-item>
            <el-form-item label="系统提示词">
              <el-input type="textarea" :rows="4" v-model="appForm.system_prompt_template" placeholder="约束客服语气、标注引用等" />
            </el-form-item>
          </template>

          <div class="app-actions">
            <el-button type="primary" @click="saveApp" :loading="loading">保存工作流</el-button>
          </div>
        </el-form>
      </el-tab-pane>
    </el-tabs>
    <el-dialog v-model="modelDialogVisible" :title="modelDialogMode === 'create' ? '新增模型' : '编辑模型'" width="640px">
      <el-form label-width="140px">
        <el-form-item label="名称" required>
          <el-input v-model="modelForm.name" />
        </el-form-item>
        <el-form-item label="提供商" required>
          <el-select v-model="modelForm.provider" style="width: 240px">
            <el-option label="DashScope(OpenAI兼容)" value="dashscope_openai" />
            <el-option label="Ark Responses" value="ark_responses" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型标识" required>
          <el-input v-model="modelForm.model_name" />
        </el-form-item>
        <el-form-item label="接口地址" required>
          <el-input v-model="modelForm.endpoint" />
        </el-form-item>
        <el-form-item label="API Key" :required="modelDialogMode === 'create'">
          <el-input v-model="modelForm.api_key" type="password" show-password />
        </el-form-item>
        <el-form-item label="超时时间">
          <el-input-number v-model="modelForm.timeout_seconds" :min="1" :max="600" />
        </el-form-item>
        <el-form-item label="调用额度/小时">
          <el-input-number v-model="modelForm.quota_per_hour" :min="0" :max="100000" />
        </el-form-item>
        <el-form-item label="温度">
          <el-input-number v-model="modelForm.temperature" :step="0.1" :min="0" :max="2" />
        </el-form-item>
        <el-form-item label="最大输出 Token">
          <el-input-number v-model="modelForm.max_output_tokens" :min="32" :max="32768" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="modelForm.enabled" />
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="modelForm.is_default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="modelDialogVisible = false">取消</el-button>
        <el-button @click="testModel()" plain>测试连接</el-button>
        <el-button type="primary" :loading="loading" @click="saveModel">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="kbDialogVisible" :title="kbDialogMode === 'create' ? '新建知识库' : '编辑知识库'" width="520px">
      <el-form label-width="120px">
        <el-form-item label="名称" required>
          <el-input v-model="kbForm.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="kbForm.description" />
        </el-form-item>
        <el-form-item label="场景">
          <el-select v-model="kbForm.feature" style="width: 240px">
            <el-option label="AI 客服" value="customer_service" />
            <el-option label="AI 课程助手" value="course_assistant" />
            <el-option label="智能教案" value="lesson_plan" />
          </el-select>
        </el-form-item>
        <el-form-item label="默认">
          <el-switch v-model="kbForm.is_default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="kbDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="loading" @click="saveKb">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="uploadDialogVisible" title="上传文档" width="520px">
      <el-form label-width="120px">
        <el-form-item label="标题">
          <el-input v-model="uploadTitle" placeholder="可选，默认使用文件名" />
        </el-form-item>
        <el-form-item label="文件" required>
          <input type="file" @change="handleUploadFileChange" />
          <div class="hint">支持 PDF/Word/TXT/Markdown/Excel</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="loading" @click="doUploadDoc">上传</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="newAppDialogVisible" title="新建工作流" width="420px">
      <el-form label-width="110px">
        <el-form-item label="编码" required>
          <el-input v-model="newAppForm.code" placeholder="唯一标识，例如 cs-custom-1" />
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="newAppForm.name" placeholder="显示名称" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="newAppForm.type" style="width: 240px">
            <el-option label="AI 客服" value="customer_service" />
            <el-option label="AI 课程助手" value="course_assistant" />
            <el-option label="智能教案" value="lesson_plan" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="newAppDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="loading" @click="createWorkflow">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="testDialogVisible" title="模型快速测试" width="640px">
      <div style="margin-bottom: 10px; color: #a0a0a0;">
        正在测试：
        <strong>{{ testingModel?.name || modelForm.name || '未命名模型' }}</strong>
        （{{ testingModel?.model_name || modelForm.model_name || '未填写标识' }}）
      </div>
      <el-form label-width="110px">
        <el-form-item label="提示词">
          <el-input
            v-model="testPrompt"
            type="textarea"
            :rows="4"
            placeholder="输入要测试的提问或指令"
          />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input
            v-model="testApiKey"
            type="password"
            show-password
            placeholder="不填写则使用当前模型保存的 Key（仅限新增/编辑弹窗）"
          />
        </el-form-item>
        <el-form-item label="返回结果">
          <el-input v-model="testResult" type="textarea" :rows="6" readonly />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="testDialogVisible = false">关闭</el-button>
        <el-button type="primary" :loading="testLoading" @click="runModelTest">开始测试</el-button>
      </template>
    </el-dialog>
  </div>
</template>
<style scoped>
.admin-ai-config {
  display: flex;
  flex-direction: column;
  gap: 20px;
  color: #fff;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.page-header h2 {
  margin: 0;
  color: #fff;
}
.sub {
  margin: 4px 0 0;
  color: rgba(255, 255, 255, 0.6);
}
.toolbar {
  margin-bottom: 12px;
  display: flex;
  justify-content: flex-end;
}
.kb-toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}
.doc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 16px 0 8px;
}
.doc-title {
  font-weight: 600;
}
.doc-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}
.app-actions {
  text-align: right;
  margin-top: 12px;
}
.hint {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
  margin-top: 6px;
}
:deep(.el-tabs--border-card) {
  background: var(--card-bg) !important;
  border: 1px solid var(--border-color) !important;
  backdrop-filter: blur(10px);
}
:deep(.el-table) {
  background-color: transparent !important;
  color: #fff;
}
:deep(.el-table__body td) {
  background-color: transparent !important;
  color: #fff !important;
}
:deep(.el-table__row) {
  background-color: transparent !important;
}
:deep(.el-table__body tr:hover > td),
:deep(.el-table__body tr.el-table__row--striped:hover > td) {
  background-color: rgba(0, 242, 254, 0.08) !important;
  color: #fff !important;
}
:deep(.el-table th.el-table__cell) {
  background-color: rgba(255, 255, 255, 0.05) !important;
}
</style>
