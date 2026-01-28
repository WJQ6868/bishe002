<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElTag, ElCard, ElButton, ElInput, ElSelect, ElOption } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { streamQA } from '@/api/ai'
import { aiPortalApi, type AiWorkflowApp } from '@/api/aiPortal'

const loading = ref(false)
const asking = ref(false)
const workflowApps = ref<AiWorkflowApp[]>([])
const selectedWorkflow = ref<string>('')
const question = ref('')
const answer = ref('')

const workflowOptions = computed(() => workflowApps.value.map(a => ({ label: a.name || a.code, value: a.code })))
const enabled = computed(() => workflowApps.value.length > 0)

const loadData = async () => {
  loading.value = true
  try {
    const apps = await aiPortalApi.listCourseAssistantApps()
    workflowApps.value = (apps || []).filter(a => a.status === 'enabled')
    if (!selectedWorkflow.value && workflowApps.value.length) {
      selectedWorkflow.value = workflowApps.value[0].code
    }
  } catch (err) {
    console.error(err)
    workflowApps.value = []
  } finally {
    loading.value = false
  }
}

const handleAsk = async () => {
  if (!question.value.trim()) {
    ElMessage.warning('请输入问题')
    return
  }
  if (!selectedWorkflow.value) {
    ElMessage.warning('请选择 AI 课程助手')
    return
  }
  asking.value = true
  answer.value = ''
  try {
    await streamQA(
      localStorage.getItem('user_id') || '0',
      question.value.trim(),
      false,
      (chunk) => { answer.value += chunk },
      undefined,
      undefined,
      selectedWorkflow.value,
    )
  } catch (err) {
    console.error(err)
    ElMessage.error('调用失败，请稍后再试')
  } finally {
    asking.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div class="course-assistant-page">
    <div class="hero">
      <div>
        <h2>AI课程助手</h2>
        <p>选择老师提供的课程助手，快速解答学习问题。</p>
      </div>
      <el-tag :type="enabled ? 'success' : 'info'">{{ enabled ? '可用' : '暂无可用助手' }}</el-tag>
    </div>

    <el-card shadow="never" class="card">
      <div class="controls">
        <el-select v-model="selectedWorkflow" placeholder="选择课程助手" style="width: 260px" :disabled="loading">
          <el-option v-for="opt in workflowOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
        <el-button type="primary" :icon="Search" :loading="asking" @click="handleAsk">提问</el-button>
      </div>

      <el-input
        v-model="question"
        type="textarea"
        :rows="4"
        placeholder="例如：第3章函数的考点是什么？"
        class="mt"
      />

      <el-card v-if="answer" class="mt answer" shadow="never">
        <template #header>回答</template>
        <p style="white-space: pre-wrap;">{{ answer }}</p>
      </el-card>
    </el-card>
  </div>
</template>

<style scoped>
.course-assistant-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  color: #e6f0ff;
}
.hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--card-bg, rgba(17,24,39,0.85));
  border: 1px solid var(--border-color, #1f2a3d);
  border-radius: 6px;
  padding: 14px 16px;
  backdrop-filter: blur(10px);
}
.hero h2 { margin: 0; color: #e6f0ff; }
.hero p { margin: 4px 0 0; color: rgba(255,255,255,0.65); }
.card {
  background: rgba(17,24,39,0.85);
  border: 1px solid var(--border-color, #1f2a3d);
  color: #e6f0ff;
}
.controls {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}
.mt { margin-top: 12px; }
.answer {
  background: rgba(255,255,255,0.05);
  color: #e6f0ff;
}
</style>
