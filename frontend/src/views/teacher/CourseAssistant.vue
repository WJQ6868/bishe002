<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { streamQA } from '@/api/ai'
import { aiPortalApi, type TeacherCourse, type AiWorkflowApp, type PublicAiModelApi } from '@/api/aiPortal'

const loading = ref(false)
const asking = ref(false)

const courses = ref<TeacherCourse[]>([])
const selectedCourseId = ref<number | null>(null)
const selectedModel = ref<string>('')
const modelOptions = ref<{ label: string; value: string }[]>([])

// 管理员提供的基础工作流（仅用于复制）
const baseWorkflows = ref<AiWorkflowApp[]>([])
const baseOptions = computed(() => baseWorkflows.value.map(a => ({ label: a.name || a.code, value: a.code })))
const selectedBase = ref<string>('')

// 教师自定义工作流（显示给学生的名称）
const teacherWorkflows = ref<AiWorkflowApp[]>([])
const chatWorkflow = ref<string>('') // 对话时真正使用的工作流 code
const newName = ref('')

const question = ref('')
const result = ref('')

const uploadFile = ref<File | null>(null)
const uploadTitle = ref('')
const uploading = ref(false)
const savingCustom = ref(false)

const courseName = computed(() => {
  const id = selectedCourseId.value
  if (!id) return ''
  return courses.value.find(c => c.id === id)?.name || ''
})

const isAllowed = computed(() => (baseWorkflows.value.length + teacherWorkflows.value.length) > 0)
const chatOptions = computed(() => {
  const opts: { label: string; value: string }[] = []
  teacherWorkflows.value.forEach(a => opts.push({ label: `${a.name || a.code}（自定义）`, value: a.code }))
  baseWorkflows.value.forEach(a => opts.push({ label: a.name || a.code, value: a.code }))
  return opts
})

const loadInit = async () => {
  loading.value = true
  try {
    const [myCourses, apps, myCustom] = await Promise.all([
      aiPortalApi.listTeacherCourses(),
      aiPortalApi.listCourseAssistantApps(),
      aiPortalApi.listTeacherCourseAssistantApps(),
    ])
    courses.value = myCourses || []
    baseWorkflows.value = (apps || []).filter(a => a.status === 'enabled' && !a.owner_user_id)
    teacherWorkflows.value = myCustom || []

    if (!selectedCourseId.value && courses.value.length) selectedCourseId.value = courses.value[0].id
    if (!selectedBase.value && baseWorkflows.value.length) selectedBase.value = baseWorkflows.value[0].code

    if (!chatWorkflow.value) {
      if (teacherWorkflows.value.length) chatWorkflow.value = teacherWorkflows.value[0].code
      else if (baseWorkflows.value.length) chatWorkflow.value = baseWorkflows.value[0].code
    }
    try {
      const models = await aiPortalApi.listPublicModelApis()
      modelOptions.value = (models || []).map((m: PublicAiModelApi) => ({
        label: `${m.name}（${m.model_name}）`,
        value: `db:${m.id}`
      }))
      if (!selectedModel.value) {
        selectedModel.value = modelOptions.value[0]?.value || ''
      }
    } catch {
      modelOptions.value = [{ label: '系统默认模型', value: '' }]
      selectedModel.value = ''
    }
  } catch (err) {
    console.error(err)
    courses.value = []
    baseWorkflows.value = []
  } finally {
    loading.value = false
  }
}

const buildPrompt = () => {
  const courseLine = courseName.value ? `课程：${courseName.value}\n` : ''
  return `你是一名高校课程助手。\n${courseLine}请基于提供的知识库资料回答问题；如果资料不足，请说明并给出合理的补充建议。\n\n问题：${question.value.trim()}`
}

const handleAsk = async () => {
  if (!isAllowed.value) {
    ElMessage.warning('未检测到可用的AI工作流，请联系管理员启用')
    return
  }
  if (!question.value.trim()) {
    ElMessage.warning('请输入问题')
    return
  }
  const workflowCode = chatWorkflow.value || selectedBase.value
  if (!workflowCode) {
    ElMessage.warning('请先选择要使用的工作流')
    return
  }
  asking.value = true
  result.value = ''
  try {
    await streamQA(
      localStorage.getItem('user_id') || '0',
      buildPrompt(),
      false,
      (chunk) => { result.value += chunk },
      selectedModel.value || undefined,
      selectedCourseId.value || undefined,
      workflowCode,
    )
  } catch (err) {
    console.error(err)
    ElMessage.error('AI接口不可用或请求失败')
  } finally {
    asking.value = false
  }
}

const createCustomWorkflow = async () => {
  if (!selectedBase.value) {
    ElMessage.warning('请先选择管理员提供的基础工作流')
    return
  }
  if (!newName.value.trim()) {
    ElMessage.warning('请输入自定义名称')
    return
  }
  savingCustom.value = true
  try {
    const app = await aiPortalApi.createTeacherCourseAssistantApp({
      name: newName.value.trim(),
      base_code: selectedBase.value,
      course_id: selectedCourseId.value || undefined,
    })
    teacherWorkflows.value.unshift(app)
    chatWorkflow.value = app.code
    newName.value = ''
    ElMessage.success('已创建自定义课程助手')
  } catch (err) {
    console.error(err)
    ElMessage.error('创建失败')
  } finally {
    savingCustom.value = false
  }
}

const deleteCustomWorkflow = async (code: string) => {
  await ElMessageBox.confirm('确认删除该自定义课程助手？', '提示', { type: 'warning' })
  savingCustom.value = true
  try {
    await aiPortalApi.deleteTeacherCourseAssistantApp(code)
    teacherWorkflows.value = teacherWorkflows.value.filter(a => a.code !== code)
    if (chatWorkflow.value === code) chatWorkflow.value = baseWorkflows.value[0]?.code || ''
    ElMessage.success('已删除')
  } catch (err) {
    console.error(err)
    ElMessage.error('删除失败')
  } finally {
    savingCustom.value = false
  }
}

const updateCustomName = async (code: string, name: string) => {
  const val = name.trim()
  if (!val) {
    ElMessage.warning('名称不能为空')
    return
  }
  savingCustom.value = true
  try {
    const app = await aiPortalApi.updateTeacherCourseAssistantApp(code, { name: val })
    const idx = teacherWorkflows.value.findIndex(a => a.code === code)
    if (idx >= 0) teacherWorkflows.value[idx] = app
    ElMessage.success('已更新名称')
  } catch (err) {
    console.error(err)
    ElMessage.error('更新失败')
  } finally {
    savingCustom.value = false
  }
}

const handleFileChange = (e: Event) => {
  const files = (e.target as HTMLInputElement).files
  uploadFile.value = files && files.length ? files[0] : null
}

const uploadTeacherDoc = async () => {
  if (!selectedCourseId.value) {
    ElMessage.warning('请先选择课程')
    return
  }
  if (!uploadFile.value) {
    ElMessage.warning('请选择文件')
    return
  }
  uploading.value = true
  try {
    await aiPortalApi.uploadTeacherKbDocument({
      title: uploadTitle.value || uploadFile.value.name,
      course_id: selectedCourseId.value,
      file: uploadFile.value,
    })
    ElMessage.success('已上传，等待管理员审核入库')
    uploadFile.value = null
    uploadTitle.value = ''
  } catch (err) {
    console.error(err)
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

onMounted(loadInit)
</script>

<template>
  <div class="course-assistant-page">
    <div class="hero">
      <div>
        <h2>AI课程助手</h2>
        <p>基于知识库资料进行问答：优先教师上传的课程专属知识库，其次管理员基础知识库。</p>
      </div>
      <el-tag :type="isAllowed ? 'success' : 'info'">{{ isAllowed ? '可用' : '已关闭/未授权' }}</el-tag>
    </div>

    <div class="config-grid">
      <div class="item">可用工作流：{{ baseWorkflows.length }}</div>
      <div class="item">我的课程数：{{ courses.length }}</div>
      <div class="item">当前课程：{{ courseName || '未选择' }}</div>
      <div class="item">知识库策略：教师KB → 基础KB</div>
      <div class="item">当前模型：{{ modelOptions.find(m => m.value === selectedModel)?.label || '系统默认' }}</div>
      <div class="item">响应：流式输出</div>
    </div>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>资料问答</span>
          <el-tag type="info">需管理员审核通过的资料才参与检索</el-tag>
        </div>
      </template>

      <div class="ask-box">
        <div class="row">
          <span class="label">课程</span>
          <el-select
            v-model="selectedCourseId"
            placeholder="选择课程（可选）"
            style="width: 260px"
            :disabled="loading"
          >
            <el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>

          <span class="label">基础工作流</span>
          <el-select
            v-model="selectedBase"
            placeholder="选择AI课程助手（管理员提供）"
            style="width: 260px"
            :disabled="loading"
          >
            <el-option v-for="a in baseOptions" :key="a.value" :label="a.label" :value="a.value" />
          </el-select>
        </div>

        <div class="row">
          <span class="label">对话使用</span>
          <el-select
            v-model="chatWorkflow"
            placeholder="优先选择自己的自定义助手"
            style="width: 260px"
            :disabled="loading || !chatOptions.length"
          >
            <el-option v-for="opt in chatOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
          <span class="label">模型</span>
          <el-select
            v-model="selectedModel"
            placeholder="选择调用模型"
            style="width: 260px"
            :disabled="loading"
          >
            <el-option v-for="m in modelOptions" :key="m.value || 'default'" :label="m.label" :value="m.value" />
          </el-select>
        </div>

        <el-card shadow="never" class="mt upload-card">
          <template #header>
            <div class="card-header">
              <span>上传课程专属知识库</span>
              <small class="hint">管理员审核入库后即可参与检索</small>
            </div>
          </template>
          <div class="upload-row">
            <el-input v-model="uploadTitle" placeholder="可填资料标题，留空默认文件名" style="max-width: 260px;" />
            <input type="file" @change="handleFileChange" />
            <el-button type="primary" :loading="uploading" @click="uploadTeacherDoc">上传</el-button>
          </div>
        </el-card>

        <el-card shadow="never" class="mt">
          <template #header>
            <div class="card-header">
              <span>我的自定义课程助手</span>
              <el-tag v-if="teacherWorkflows.length === 0" type="info">暂无</el-tag>
            </div>
          </template>

          <div class="custom-row">
            <el-input v-model="newName" placeholder="自定义名称（学生端可见）" style="max-width: 260px;" />
            <el-button type="primary" :loading="savingCustom" @click="createCustomWorkflow">创建</el-button>
          </div>

          <el-table :data="teacherWorkflows" size="small" style="margin-top: 10px;">
            <el-table-column prop="name" label="名称" min-width="180">
              <template #default="{ row }">
                <el-input size="small" v-model="row.name" @change="(v: string) => updateCustomName(row.code, v)" />
              </template>
            </el-table-column>
            <el-table-column prop="course_id" label="课程ID" width="120" />
            <el-table-column prop="updated_at" label="更新时间" width="180" />
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button size="small" link type="danger" @click="deleteCustomWorkflow(row.code)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-input
          v-model="question"
          type="textarea"
          :rows="4"
          placeholder="输入你的教学问题，系统将基于知识库检索回答"
        />
        <div class="ask-actions">
          <el-button type="primary" :icon="Search" :loading="asking" @click="handleAsk">提交问题</el-button>
        </div>
        <el-alert
          v-if="!isAllowed"
          type="warning"
          title="功能已关闭或未授权"
          :closable="false"
          show-icon
          class="mt"
        />
        <el-card v-if="result" class="mt" shadow="never">
          <template #header>返回结果</template>
          <p style="white-space: pre-wrap;">{{ result }}</p>
        </el-card>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.course-assistant-page { display: flex; flex-direction: column; gap: 16px; }
.hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--card-bg, rgba(17, 24, 39, 0.85));
  border: 1px solid var(--border-color, #1f2a3d);
  border-radius: 6px;
  padding: 14px 16px;
  backdrop-filter: blur(10px);
}
.hero h2 { margin: 0; color: #e6f0ff; }
.hero p { margin: 4px 0 0; color: rgba(255, 255, 255, 0.75); }
.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 8px;
  background: var(--card-bg, rgba(17, 24, 39, 0.85));
  border: 1px solid var(--border-color, #1f2a3d);
  padding: 12px;
  border-radius: 6px;
}
.item {
  background: rgba(255, 255, 255, 0.05);
  padding: 8px 10px;
  border-radius: 4px;
  font-size: 13px;
  color: #e6f0ff;
  border: 1px solid var(--border-color, #1f2a3d);
}
.card-header { display: flex; justify-content: space-between; align-items: center; }
.ask-box { display: flex; flex-direction: column; gap: 12px; }
.row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.label { min-width: 80px; color: var(--el-text-color-regular); }
.upload-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.custom-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.ask-actions { display: flex; justify-content: flex-end; }
.mt { margin-top: 10px; }
.hint { color: var(--el-text-color-secondary); }
</style>
