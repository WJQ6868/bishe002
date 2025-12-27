<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElCard, ElTag, ElAlert, ElButton, ElDescriptions, ElDescriptionsItem } from 'element-plus'
import StudentAIChat from '@/components/StudentAIChat.vue'

interface FeatureState {
  enabled: boolean
  rateLimit: number
  concurrency: number
  timeout: number
  retry: number
  defaultApiName: string
  hint: string
}

const buildState = (): FeatureState => {
  const saved = localStorage.getItem('ai_feature_configs')
  if (saved) {
    try {
      const parsed = JSON.parse(saved)
      const feature = parsed.features?.customer
      const apis = parsed.apis || []
      const defaultId = feature?.defaultApiId
      const defaultApi = apis.find((a: any) => a.id === defaultId)
      return {
        enabled: !!feature?.enabled,
        rateLimit: feature?.rateLimit ?? 0,
        concurrency: feature?.concurrency ?? 0,
        timeout: feature?.timeout ?? 0,
        retry: feature?.retry ?? 0,
        defaultApiName: defaultApi?.name || '未配置',
        hint: feature?.rules?.kbTrigger || '基于校园知识库的问答'
      }
    } catch (e) {
      console.warn('load ai feature failed', e)
    }
  }
  return {
    enabled: true,
    rateLimit: 200,
    concurrency: 20,
    timeout: 30,
    retry: 2,
    defaultApiName: '默认模型',
    hint: '基于校园知识库的问答'
  }
}

const state = ref<FeatureState>(buildState())

const visible = ref(false)
const toggle = () => {
  if (!state.value.enabled) return
  visible.value = !visible.value
}

const statusTag = computed(() => state.value.enabled ? { type: 'success' as const, text: '可用' } : { type: 'info' as const, text: '已关闭' })
</script>

<template>
  <div class="ai-service-page">
    <el-card shadow="never" class="hero">
      <div class="hero-head">
        <div>
          <h2>AI客服</h2>
          <p>调用管理员配置的客服 API，回答校园常见问题。</p>
        </div>
        <el-tag :type="statusTag.type">{{ statusTag.text }}</el-tag>
      </div>
      <p class="hint">{{ state.hint }}</p>
      <el-descriptions :column="2" border size="small" class="desc">
        <el-descriptions-item label="默认模型">{{ state.defaultApiName }}</el-descriptions-item>
        <el-descriptions-item label="频次上限/小时">{{ state.rateLimit }}</el-descriptions-item>
        <el-descriptions-item label="并发上限">{{ state.concurrency }}</el-descriptions-item>
        <el-descriptions-item label="超时/重试">{{ state.timeout }}s / {{ state.retry }}</el-descriptions-item>
      </el-descriptions>
      <div class="actions">
        <el-button type="primary" :disabled="!state.enabled" @click="toggle">{{ visible ? '收起对话' : '打开AI客服' }}</el-button>
        <el-alert v-if="!state.enabled" title="功能已关闭，联系管理员开启" type="warning" show-icon :closable="false" />
      </div>
    </el-card>

    <div v-if="visible && state.enabled" class="chat-wrapper">
      <StudentAIChat />
    </div>
  </div>
</template>

<style scoped>
.ai-service-page { display: flex; flex-direction: column; gap: 16px; }
.hero-head { display: flex; justify-content: space-between; align-items: center; }
.hero h2 { margin: 0; }
.hero p { margin: 4px 0 0; color: #606266; }
.hint { margin: 8px 0; color: #909399; font-size: 13px; }
.desc { margin-top: 8px; }
.actions { margin-top: 12px; display: flex; gap: 12px; align-items: center; }
.chat-wrapper { background: #fff; border-radius: 6px; padding: 10px; box-shadow: 0 1px 6px rgba(0,0,0,0.05); }
</style>
