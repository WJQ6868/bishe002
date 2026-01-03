<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { streamQA } from '@/api/ai'
import { aiPortalApi, type PublicAiModelApi, type TeacherCourse, type TeacherKbDocument, type LessonPlanTask } from '@/api/aiPortal'

const creating = ref(false)
const generating = ref(false)
const planTitle = ref('')
const syllabus = ref('')
const planContent = ref('')
const selectedModel = ref('')
const modelOptions = ref<{ label: string; value: string }[]>([])
const resultDialogVisible = ref(false)
const viewingTask = ref<LessonPlanTask | null>(null)
const taskDialogVisible = ref(false)

const courses = ref<TeacherCourse[]>([])
const selectedCourseId = ref<number | null>(null)
const kbDocs = ref<TeacherKbDocument[]>([])
const kbLoading = ref(false)

const kbUploadVisible = ref(false)
const kbEditVisible = ref(false)
const kbReplaceVisible = ref(false)
const kbUploadForm = reactive({ title: '', subject: '', file: null as File | null })
const kbEditForm = reactive({ id: 0, title: '', subject: '' })
const kbReplaceForm = reactive({ id: 0, file: null as File | null })

const lessonPlanTasks = ref<LessonPlanTask[]>([])

const statusText = (status: string) => {
  switch (status) {
    case 'pending':
      return '待生成'
    case 'streaming':
      return '生成中'
    case 'completed':
      return '已完成'
    case 'failed':
      return '失败'
    default:
      return status
  }
}

const statusType = (status: string) => {
  switch (status) {
    case 'completed':
      return 'success'
    case 'failed':
      return 'danger'
    case 'streaming':
      return 'warning'
    default:
      return 'info'
  }
}

const loadModels = async () => {
  try {
    const items = await aiPortalApi.listPublicModelApis()
    modelOptions.value = items.map((m: PublicAiModelApi) => ({ label: `${m.name}（${m.model_name}）`, value: `db:${m.id}` }))
    selectedModel.value = modelOptions.value[0]?.value || 'tongyi'
  } catch {
    modelOptions.value = [{ label: '通义千问（默认）', value: 'tongyi' }]
    selectedModel.value = 'tongyi'
  }
}

const loadTeacherCourses = async () => {
  try {
    courses.value = await aiPortalApi.listTeacherCourses()
    if (!selectedCourseId.value && courses.value.length) {
      selectedCourseId.value = courses.value[0].id
    }
  } catch {
    courses.value = []
  }
}

const loadKbDocs = async () => {
  kbLoading.value = true
  try {
    kbDocs.value = await aiPortalApi.listTeacherKbDocuments(selectedCourseId.value || undefined)
  } finally {
    kbLoading.value = false
  }
}

const loadLessonPlanTasks = async () => {
  lessonPlanTasks.value = await aiPortalApi.listLessonPlanTasks(selectedCourseId.value || undefined)
}

watch(selectedCourseId, async () => {
  await loadKbDocs()
  await loadLessonPlanTasks()
})

onMounted(async () => {
  await loadModels()
  await loadTeacherCourses()
  await loadKbDocs()
  await loadLessonPlanTasks()
})

const openCreatePlan = () => {
  planTitle.value = ''
  syllabus.value = ''
  planContent.value = ''
  creating.value = true
}

const assemblePrompt = () => {
  const title = planTitle.value.trim() || '未命名课程'
  const outline = syllabus.value.trim() || '暂未提供课程大纲'
  return `你是一名高校教师助手。请基于以下课程大纲生成结构化教案，包含教学目标、重难点、教学过程（导入/讲授/练习/总结）、课后作业以及评价方式。课程：${title}。大纲：${outline}`
}

const generatePlan = async () => {
  if (!planTitle.value.trim()) {
    ElMessage.error('请输入教案标题')
    return
  }
  generating.value = true
  planContent.value = ''
  let createdTaskId: number | null = null
  try {
    const task = await aiPortalApi.createLessonPlanTask({
      title: planTitle.value.trim(),
      outline: syllabus.value,
      course_id: selectedCourseId.value || undefined
    })
    createdTaskId = task.id
    await streamQA(
      localStorage.getItem('user_id') || '0',
      assemblePrompt(),
      false,
      (chunk) => {
        planContent.value += chunk
      },
      selectedModel.value,
      selectedCourseId.value || undefined
    )
    if (createdTaskId) {
      await aiPortalApi.updateLessonPlanTaskResult(createdTaskId, { status: 'completed', result: planContent.value })
    }
    ElMessage.success('教案生成完成')
    resultDialogVisible.value = true
    await loadLessonPlanTasks()
  } catch (err) {
    if (createdTaskId) {
      await aiPortalApi.updateLessonPlanTaskResult(createdTaskId, {
        status: 'failed',
        error_message: err instanceof Error ? err.message : '生成失败'
      })
    }
    ElMessage.error('生成失败，请稍后重试')
  } finally {
    generating.value = false
  }
}

const openTaskResult = (task: LessonPlanTask) => {
  viewingTask.value = task
  taskDialogVisible.value = true
}

const openUploadKb = () => {
  kbUploadForm.title = ''
  kbUploadForm.subject = ''
  kbUploadForm.file = null
  kbUploadVisible.value = true
}

const handleUploadFileChange = (e: Event) => {
  const files = (e.target as HTMLInputElement).files
  kbUploadForm.file = files && files.length ? files[0] : null
}

const doUploadKb = async () => {
  if (!kbUploadForm.file) {
    ElMessage.error('请选择文件')
    return
  }
  kbLoading.value = true
  try {
    await aiPortalApi.uploadTeacherKbDocument({
      title: kbUploadForm.title.trim() || kbUploadForm.file.name,
      subject: kbUploadForm.subject,
      course_id: selectedCourseId.value || undefined,
      file: kbUploadForm.file
    })
    kbUploadVisible.value = false
    await loadKbDocs()
    ElMessage.success('上传成功')
  } finally {
    kbLoading.value = false
  }
}

const openEditKb = (row: TeacherKbDocument) => {
  kbEditForm.id = row.id
  kbEditForm.title = row.title
  kbEditForm.subject = row.subject
  kbEditVisible.value = true
}

const doEditKb = async () => {
  kbLoading.value = true
  try {
    await aiPortalApi.updateTeacherKbDocument(kbEditForm.id, {
      title: kbEditForm.title,
      subject: kbEditForm.subject,
      course_id: selectedCourseId.value || undefined
    })
    kbEditVisible.value = false
    await loadKbDocs()
    ElMessage.success('已保存')
  } finally {
    kbLoading.value = false
  }
}

const openReplaceKb = (row: TeacherKbDocument) => {
  kbReplaceForm.id = row.id
  kbReplaceForm.file = null
  kbReplaceVisible.value = true
}

const handleReplaceFile = (e: Event) => {
  const files = (e.target as HTMLInputElement).files
  kbReplaceForm.file = files && files.length ? files[0] : null
}

const doReplaceKb = async () => {
  if (!kbReplaceForm.file) {
    ElMessage.error('请选择文件')
    return
  }
  kbLoading.value = true
  try {
    await aiPortalApi.replaceTeacherKbDocument(kbReplaceForm.id, kbReplaceForm.file)
    kbReplaceVisible.value = false
    await loadKbDocs()
    ElMessage.success('已替换文档')
  } finally {
    kbLoading.value = false
  }
}

const doDeleteKb = async (row: TeacherKbDocument) => {
  await ElMessageBox.confirm(`确认删除「${row.title}」？`, '提示', { type: 'warning' })
  kbLoading.value = true
  try {
    await aiPortalApi.deleteTeacherKbDocument(row.id)
    await loadKbDocs()
    ElMessage.success('已删除')
  } finally {
    kbLoading.value = false
  }
}
</script>

<template>
  <div class="lesson-plan-page">
    <div class="header">
      <h2>智能教案</h2>
      <el-button type="primary" @click="openCreatePlan">新建教案</el-button>
    </div>

    <el-alert type="info" show-icon title="功能说明">
      <div>管理员配置的基础模型与知识库作为底座，叠加课程私有资料后生成专属教案。</div>
    </el-alert>

    <el-card shadow="never" class="kb-card">
      <template #header>
        <div class="card-header">
          <span>课程知识库（用于课程助手与智能教案）</span>
          <el-button type="primary" @click="openUploadKb">上传文档</el-button>
        </div>
      </template>

      <div class="course-select">
        <span>选择课程</span>
        <el-select v-model="selectedCourseId" placeholder="选择课程" style="width: 320px">
          <el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </div>

      <el-table :data="kbDocs" border v-loading="kbLoading">
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column prop="original_filename" label="文件名" min-width="240" show-overflow-tooltip />
        <el-table-column prop="file_ext" label="格式" width="100" />
        <el-table-column label="更新时间" width="180">
          <template #default="{ row }">{{ (row.updated_at || row.created_at || '').replace('T', ' ').slice(0, 19) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link @click="window.open(row.url, '_blank')">预览</el-button>
            <el-button size="small" link type="primary" @click="openEditKb(row)">编辑</el-button>
            <el-button size="small" link @click="openReplaceKb(row)">替换</el-button>
            <el-button size="small" link type="danger" @click="doDeleteKb(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>教案生成记录</span>
          <el-button :icon="Refresh" circle @click="loadLessonPlanTasks" />
        </div>
      </template>
      <el-table :data="lessonPlanTasks" border>
        <el-table-column prop="title" label="标题" min-width="220" />
        <el-table-column label="课程" min-width="160">
          <template #default="{ row }">
            {{ courses.find(c => c.id === row.course_id)?.name || '通用' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180" />
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="openTaskResult(row)" :disabled="!row.result">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="creating" title="新建教案" width="800px">
      <el-form label-width="100px">
        <el-form-item label="标题">
          <el-input v-model="planTitle" placeholder="例如：软件工程第一章教案" />
        </el-form-item>
        <el-form-item label="使用模型">
          <el-select v-model="selectedModel" placeholder="选择模型">
            <el-option v-for="m in modelOptions" :key="m.value" :label="m.label" :value="m.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="课程大纲">
          <el-input v-model="syllabus" type="textarea" :rows="6" placeholder="粘贴课程大纲或关键要点" />
        </el-form-item>
        <el-form-item label="生成结果">
          <el-input v-model="planContent" type="textarea" :rows="10" placeholder="生成结果将在此展示" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="creating = false">取消</el-button>
        <el-button type="primary" :loading="generating" @click="generatePlan">生成教案</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resultDialogVisible" title="生成结果" width="800px">
      <div style="white-space: pre-wrap; line-height: 1.6">{{ planContent }}</div>
      <template #footer>
        <el-button @click="resultDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="taskDialogVisible" :title="viewingTask?.title || '教案详情'" width="800px">
      <div style="white-space: pre-wrap; line-height: 1.6">
        {{ viewingTask?.result || '尚未生成内容' }}
      </div>
      <template #footer>
        <el-button @click="taskDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="kbUploadVisible" title="上传课程文档" width="640px">
      <el-form label-width="100px">
        <el-form-item label="标题">
          <el-input v-model="kbUploadForm.title" placeholder="可选，默认使用文件名" />
        </el-form-item>
        <el-form-item label="学科/标签">
          <el-input v-model="kbUploadForm.subject" placeholder="可选" />
        </el-form-item>
        <el-form-item label="文件" required>
          <input type="file" @change="handleUploadFileChange" />
          <div class="hint">支持 TXT/PDF/DOCX/MD 等常见格式</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="kbUploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="kbLoading" @click="doUploadKb">上传</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="kbEditVisible" title="编辑文档" width="560px">
      <el-form label-width="100px">
        <el-form-item label="标题">
          <el-input v-model="kbEditForm.title" />
        </el-form-item>
        <el-form-item label="学科/标签">
          <el-input v-model="kbEditForm.subject" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="kbEditVisible = false">取消</el-button>
        <el-button type="primary" :loading="kbLoading" @click="doEditKb">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="kbReplaceVisible" title="替换文件" width="560px">
      <el-form label-width="100px">
        <el-form-item label="新文件" required>
          <input type="file" @change="handleReplaceFile" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="kbReplaceVisible = false">取消</el-button>
        <el-button type="primary" :loading="kbLoading" @click="doReplaceKb">替换</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.lesson-plan-page {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.course-select {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.hint {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-top: 6px;
}
:deep(.el-alert),
:deep(.el-card) {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
}
</style>
