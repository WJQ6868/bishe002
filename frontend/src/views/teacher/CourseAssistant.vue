<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { streamQA } from '@/api/ai'
import { aiPortalApi, type PublicAiModelApi, type TeacherCourse } from '@/api/aiPortal'

const loading = ref(false)
const asking = ref(false)

const courses = ref<TeacherCourse[]>([])
const selectedCourseId = ref<number | null>(null)

const modelItems = ref<PublicAiModelApi[]>([])
const modelOptions = computed(() =>
  modelItems.value.map((m) => ({
    label: `${m.name}（${m.model_name}）${m.is_default ? ' · 默认' : ''}`,
    value: `db:${m.id}`
  }))
)
const selectedModel = ref<string>('')

const defaultModelName = computed(() => {
  const def = modelItems.value.find((m) => m.is_default) || modelItems.value[0]
  return def?.name || '未配置'
})

const courseName = computed(() => {
  const id = selectedCourseId.value
  if (!id) return ''
  return courses.value.find((c) => c.id === id)?.name || ''
})

const question = ref('')
const result = ref('')

const isAllowed = computed(() => modelItems.value.length > 0)

const loadInit = async () => {
  loading.value = true
  try {
    const [models, myCourses] = await Promise.all([
      aiPortalApi.listPublicModelApis(),
      aiPortalApi.listTeacherCourses()
    ])
    modelItems.value = (models || []).filter((m) => m.enabled)
    courses.value = myCourses || []

    if (!selectedCourseId.value && courses.value.length) {
      selectedCourseId.value = courses.value[0].id
    }

    if (!selectedModel.value) {
      const def = modelItems.value.find((m) => m.is_default) || modelItems.value[0]
      selectedModel.value = def ? `db:${def.id}` : ''
    }
  } catch {
    modelItems.value = []
    courses.value = []
  } finally {
    loading.value = false
  }
}

const buildPrompt = () => {
  const course = courseName.value ? `课程：${courseName.value}\n` : ''
  return `你是一名高校教师课程助手。${course}请基于提供的知识库资料回答问题；如果资料不足，请明确说明并给出合理的补充建议。\n\n问题：${question.value.trim()}`
}

const handleAsk = async () => {
  if (!isAllowed.value) {
    ElMessage.warning('未检测到可用的大模型配置，请联系管理员启用模型')
    return
  }
  if (!question.value.trim()) {
    ElMessage.warning('请输入问题')
    return
  }
  asking.value = true
  result.value = ''
  try {
    await streamQA(
      localStorage.getItem('user_id') || '0',
      buildPrompt(),
      false,
      (chunk) => {
        result.value += chunk
      },
      selectedModel.value || undefined,
      selectedCourseId.value || undefined
    )
  } catch {
    ElMessage.error('AI接口不可用或请求失败')
  } finally {
    asking.value = false
  }
}

onMounted(loadInit)
</script>

<template>
  <div class="course-assistant-page">
    <div class="hero">
      <div>
        <h2>AI课程助手</h2>
        <p>基于知识库资料进行问答：优先教师个性化KB，其次基础KB。</p>
        <p class="hint">默认模型：{{ defaultModelName }}</p>
      </div>
      <el-tag :type="isAllowed ? 'success' : 'info'">{{ isAllowed ? '可用' : '已关闭/未授权' }}</el-tag>
    </div>

    <div class="config-grid">
      <div class="item">默认模型：{{ defaultModelName }}</div>
      <div class="item">可用模型数：{{ modelItems.length }}</div>
      <div class="item">我的课程数：{{ courses.length }}</div>
      <div class="item">当前课程：{{ courseName || '未选择' }}</div>
      <div class="item">知识库策略：教师KB → 基础KB</div>
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
        <div style="display:flex; gap: 12px; align-items:center;">
          <span style="min-width: 60px;">课程</span>
          <el-select
            v-model="selectedCourseId"
            placeholder="选择课程（可选）"
            style="width: 320px"
            :disabled="loading"
          >
            <el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>

          <span style="min-width: 60px;">模型</span>
          <el-select
            v-model="selectedModel"
            placeholder="默认模型"
            style="width: 320px"
            :disabled="loading"
          >
            <el-option v-for="m in modelOptions" :key="m.value" :label="m.label" :value="m.value" />
          </el-select>
        </div>

        <el-input
          v-model="question"
          type="textarea"
          :rows="4"
          placeholder="输入你的教学问题，系统将基于知识库检索回答"
        />
        <div class="ask-actions">
          <el-button type="primary" :icon="Search" :loading="asking" @click="handleAsk">提交问题</el-button>
        </div>
        <el-alert v-if="!isAllowed" type="warning" title="功能已关闭或未授权" :closable="false" show-icon class="mt" />
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
  background: var(--card-bg); 
  backdrop-filter: blur(10px);
  padding: 16px; 
  border-radius: 6px; 
  border: 1px solid var(--border-color);
}
.hero h2 { margin: 0; color: var(--el-text-color-primary); }
.hero p { margin: 4px 0 0; color: var(--el-text-color-secondary); }
.hint { color: var(--el-text-color-secondary); font-size: 13px; }
.config-grid { 
  display: grid; 
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); 
  gap: 8px; 
  background: var(--card-bg); 
  backdrop-filter: blur(10px);
  padding: 12px; 
  border-radius: 6px; 
  border: 1px solid var(--border-color);
}
.item { 
  background: rgba(255, 255, 255, 0.05); 
  padding: 8px 10px; 
  border-radius: 4px; 
  font-size: 13px; 
  color: var(--el-text-color-regular); 
  border: 1px solid var(--border-color);
}
.card-header { display: flex; justify-content: space-between; align-items: center; }
.ask-box { display: flex; flex-direction: column; gap: 12px; }
.ask-actions { display: flex; justify-content: flex-end; }
.mt { margin-top: 10px; }
</style>
