<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const creating = ref(false)
const generating = ref(false)
const planTitle = ref('')
const planContent = ref('')
const syllabus = ref('')
const modelList = ref<string[]>([])
const selectedModel = ref('')
const dialogVisible = ref(false)

const openCreate = () => {
  creating.value = true
}
const savePlan = () => {
  if (!planTitle.value.trim()) {
    ElMessage.error('请输入教案标题')
    return
  }
  ElMessage.success('已保存教案草案')
  creating.value = false
}
const loadModels = () => {
  try {
    const saved = localStorage.getItem('ai_models')
    const arr = saved ? JSON.parse(saved) : null
    const base = Array.isArray(arr) && arr.length ? arr : ['Qwen-Max','Qwen-Plus','Qwen-Turbo']
    modelList.value = base
    selectedModel.value = base[0]
  } catch {
    modelList.value = ['Qwen-Max']
    selectedModel.value = 'Qwen-Max'
  }
}
loadModels()

const assemblePrompt = () => {
  const title = planTitle.value.trim() || '未命名课程教案'
  const syl = syllabus.value.trim()
  const model = selectedModel.value
  const sys = `你是一名高校教师助理。根据课程大纲生成结构化教案，包含教学目标、重点难点、教学过程（导入、讲授、练习、总结）、课后作业、评价方式。课程：${title}。模型：${model}。`
  const user = syl ? `课程大纲：\n${syl}` : '无课程大纲'
  return `${sys}\n\n${user}`
}

const generatePlan = async () => {
  if (!planTitle.value.trim()) {
    ElMessage.error('请输入教案标题')
    return
  }
  generating.value = true
  planContent.value = ''
  try {
    const controller = new AbortController()
    const res = await fetch('/qa/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
      body: JSON.stringify({ question: assemblePrompt(), user_id: localStorage.getItem('user_id') || '0', history_flag: false }),
      signal: controller.signal
    })
    const reader = res.body!.getReader()
    const decoder = new TextDecoder('utf-8')
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value)
      planContent.value += chunk
    }
  } catch (e) {
    ElMessage.error('生成失败')
  } finally {
    generating.value = false
    dialogVisible.value = true
  }
}
</script>

<template>
  <div class="lesson-plan-page">
    <div class="header">
      <h2>智能教案</h2>
      <div class="actions">
        <el-button type="primary" @click="openCreate">新建教案</el-button>
      </div>
    </div>

    <el-alert type="info" show-icon title="说明">
      <template #default>
        <div>本页面为智能教案入口。可在右下角 AI 助手中生成教案草案并粘贴到此处保存。</div>
      </template>
    </el-alert>

    <el-empty description="暂无教案，点击右上角“新建教案”，提供课程大纲并选择模型进行生成" />

    <el-dialog v-model="creating" title="新建教案" width="800px">
      <el-form label-width="100px">
        <el-form-item label="标题">
          <el-input v-model="planTitle" placeholder="例如：软件工程-第1章教学设计" />
        </el-form-item>
        <el-form-item label="选择模型">
          <el-select v-model="selectedModel" placeholder="选择模型" style="width: 100%">
            <el-option v-for="m in modelList" :key="m" :label="m" :value="m" />
          </el-select>
        </el-form-item>
        <el-form-item label="课程大纲">
          <el-input v-model="syllabus" type="textarea" :rows="8" placeholder="粘贴课程大纲或关键要点" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="planContent" type="textarea" :rows="12" placeholder="点击生成教案后将在此展示结果" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="creating = false">取消</el-button>
        <el-button type="primary" :loading="generating" @click="generatePlan">生成教案</el-button>
        <el-button type="primary" @click="savePlan">保存</el-button>
      </template>
    </el-dialog>
    <el-dialog v-model="dialogVisible" title="生成结果" width="800px">
      <div style="white-space: pre-wrap; line-height: 1.6">{{ planContent }}</div>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
  
</template>

<style scoped>
.lesson-plan-page {
  padding: 20px;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.actions {
  display: flex;
  gap: 12px;
}
</style>
