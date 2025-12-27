<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'

interface FeatureState {
  enabled: boolean
  rateLimit: number
  concurrency: number
  timeout: number
  retry: number
  defaultApiName: string
  responseFormat: string
  teacherDailyLimit: number
  subjectDailyLimit: number
  subjectScopes: string[]
}

const buildFeature = (): FeatureState => {
  const saved = localStorage.getItem('ai_feature_configs')
  if (saved) {
    try {
      const parsed = JSON.parse(saved)
      const f = parsed.features?.course
      const apis = parsed.apis || []
      const defaultApi = apis.find((a: any) => a.id === f?.defaultApiId)
      return {
        enabled: !!f?.enabled,
        rateLimit: f?.rateLimit ?? 0,
        concurrency: f?.concurrency ?? 0,
        timeout: f?.timeout ?? 0,
        retry: f?.retry ?? 0,
        defaultApiName: defaultApi?.name || '未配置',
        responseFormat: f?.rules?.responseFormat || 'concise',
        teacherDailyLimit: f?.rules?.teacherDailyLimit ?? 0,
        subjectDailyLimit: f?.rules?.subjectDailyLimit ?? 0,
        subjectScopes: f?.rules?.subjectScopes || []
      }
    } catch (e) {
      console.warn('load course config failed', e)
    }
  }
  return {
    enabled: true,
    rateLimit: 200,
    concurrency: 10,
    timeout: 30,
    retry: 2,
    defaultApiName: '默认模型',
    responseFormat: 'concise',
    teacherDailyLimit: 200,
    subjectDailyLimit: 500,
    subjectScopes: []
  }
}

const feature = reactive<FeatureState>(buildFeature())

const question = ref('')
const result = ref('')
const isAllowed = computed(() => feature.enabled)

const handleAsk = () => {
  if (!isAllowed.value) {
    ElMessage.warning('功能未启用或未授权，联系管理员')
    return
  }
  if (!question.value) {
    ElMessage.warning('请输入问题')
    return
  }
  // 仅做示例提示，实际调用需接入后端 API
  result.value = `已提交至 ${feature.defaultApiName}（格式：${feature.responseFormat === 'concise' ? '精简' : '详细'}），请稍候查看结果。`
  ElMessage.success('已提交检索请求')
}
</script>

<template>
  <div class="course-assistant-page">
    <div class="hero">
      <div>
        <h2>AI课程助手</h2>
        <p>基于已审核的教学资料进行精准问答，调用管理员配置的检索类 API。</p>
        <p class="hint">学科权限：{{ feature.subjectScopes.length ? feature.subjectScopes.join('、') : '未限制' }}</p>
      </div>
      <el-tag :type="isAllowed ? 'success' : 'info'">{{ isAllowed ? '可用' : '已关闭/未授权' }}</el-tag>
    </div>

    <div class="config-grid">
      <div class="item">默认模型：{{ feature.defaultApiName }}</div>
      <div class="item">频次/小时：{{ feature.rateLimit }}</div>
      <div class="item">并发上限：{{ feature.concurrency }}</div>
      <div class="item">超时/重试：{{ feature.timeout }}s / {{ feature.retry }}</div>
      <div class="item">教师日上限：{{ feature.teacherDailyLimit }}</div>
      <div class="item">学科日上限：{{ feature.subjectDailyLimit }}</div>
      <div class="item">结果模式：{{ feature.responseFormat === 'concise' ? '精简' : '详细' }}</div>
    </div>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>资料问答</span>
          <el-tag type="info">需管理员审核通过的资料才参与检索</el-tag>
        </div>
      </template>
      <div class="ask-box">
        <el-input
          v-model="question"
          type="textarea"
          :rows="4"
          placeholder="输入你的教学问题，系统将基于已审核资料检索回答"
        />
        <div class="ask-actions">
          <el-button type="primary" :icon="Search" @click="handleAsk">提交问题</el-button>
        </div>
        <el-alert v-if="!isAllowed" type="warning" title="功能已关闭或未授权" :closable="false" show-icon class="mt" />
        <el-card v-if="result" class="mt" shadow="never">
          <template #header>返回结果</template>
          <p>{{ result }}</p>
        </el-card>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.course-assistant-page { display: flex; flex-direction: column; gap: 16px; }
.hero { display: flex; justify-content: space-between; align-items: center; background: #fff; padding: 16px; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
.hero h2 { margin: 0; }
.hero p { margin: 4px 0 0; color: #606266; }
.hint { color: #909399; font-size: 13px; }
.config-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 8px; background: #fff; padding: 12px; border-radius: 6px; box-shadow: 0 1px 6px rgba(0,0,0,0.05); }
.item { background: #f7f9fb; padding: 8px 10px; border-radius: 4px; font-size: 13px; color: #303133; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.ask-box { display: flex; flex-direction: column; gap: 12px; }
.ask-actions { display: flex; justify-content: flex-end; }
.mt { margin-top: 10px; }
</style>
