<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'

// --- 1. 类型定义 ---
interface BaseConfig {
  systemName: string
  loginBg: string
  sessionTimeout: number
  defaultPwd: string
}

interface CourseSelectConfig {
  periodStart: string
  periodEnd: string
  maxCourses: number
  priorityEnabled: boolean
  conflictCheck: boolean
}

interface ScheduleConfig {
  timeRange: string
  maxDailyPeriods: number
  teacherMaxDailyPeriods: number
  utilizationTarget: number
}

interface AiConfig {
  modelProvider: string
  streamResponse: boolean
  cacheMinutes: number
  sensitiveFilter: boolean
}

interface SystemConfig {
  base: BaseConfig
  courseSelect: CourseSelectConfig
  schedule: ScheduleConfig
  ai: AiConfig
}

// --- 2. 默认配置 ---
const defaultConfig: SystemConfig = {
  base: {
    systemName: '高校智能教务系统',
    loginBg: 'bg1',
    sessionTimeout: 30,
    defaultPwd: '123456'
  },
  courseSelect: {
    periodStart: '2025-12-05',
    periodEnd: '2025-12-10',
    maxCourses: 5,
    priorityEnabled: true,
    conflictCheck: true
  },
  schedule: {
    timeRange: '周一至周五 8:00-18:00',
    maxDailyPeriods: 6,
    teacherMaxDailyPeriods: 3,
    utilizationTarget: 85
  },
  ai: {
    modelProvider: '通义千问',
    streamResponse: true,
    cacheMinutes: 60,
    sensitiveFilter: true
  }
}

// --- 3. 状态管理 ---
const activeTab = ref('base')
const config = reactive<SystemConfig>(JSON.parse(JSON.stringify(defaultConfig)))
const originalConfig = ref<SystemConfig>(JSON.parse(JSON.stringify(defaultConfig)))
const dirtyTabs = ref<Set<string>>(new Set())

const snackbar = reactive({
  show: false,
  text: '',
  color: 'success'
})

const showMessage = (text: string, color: 'success' | 'error' | 'warning' = 'success') => {
  snackbar.text = text
  snackbar.color = color
  snackbar.show = true
}

// 选项数据
const bgOptions = [
  { value: 'bg1', label: '背景1', preview: 'https://picsum.photos/300/200?random=1' },
  { value: 'bg2', label: '背景2', preview: 'https://picsum.photos/300/200?random=2' },
  { value: 'bg3', label: '背景3', preview: 'https://picsum.photos/300/200?random=3' }
]
const aiProviders = ['通义千问', 'DeepSeek', '讯飞星火']
const timeRangeOptions = [
  '周一至周五 8:00-18:00',
  '周一至周五 7:30-17:30',
  '周一至周日 8:00-20:00'
]

// --- 4. 核心逻辑 ---
const loadConfig = () => {
  const saved = localStorage.getItem('system_config')
  if (saved) {
    try {
      const parsed = JSON.parse(saved)
      Object.assign(config, parsed)
      originalConfig.value = JSON.parse(JSON.stringify(parsed))
    } catch (e) {
      showMessage('加载配置失败', 'error')
    }
  }
}

const saveConfig = () => {
  localStorage.setItem('system_config', JSON.stringify(config))
  originalConfig.value = JSON.parse(JSON.stringify(config))
  dirtyTabs.value.clear()
  showMessage('配置保存成功')
}

const resetTabConfig = () => {
  const tabKey = activeTab.value as keyof SystemConfig
  config[tabKey] = JSON.parse(JSON.stringify(defaultConfig[tabKey]))
  dirtyTabs.value.delete(activeTab.value)
  showMessage('已重置为默认值', 'success')
}

watch(() => config, () => {
  const tabKey = activeTab.value as keyof SystemConfig
  const currentConfig = JSON.stringify(config[tabKey])
  const originalTabConfig = JSON.stringify(originalConfig.value[tabKey])
  
  if (currentConfig !== originalTabConfig) {
    dirtyTabs.value.add(activeTab.value)
  } else {
    dirtyTabs.value.delete(activeTab.value)
  }
}, { deep: true })

const hasUnsavedChanges = computed(() => dirtyTabs.value.size > 0)

const currentBgPreview = computed(() => {
  const bg = bgOptions.find(b => b.value === config.base.loginBg)
  return bg?.preview || ''
})

loadConfig()

</script>

<template>
  <div class="config-container pa-4">
    <!-- 顶部标题 -->
    <v-card class="mb-4" elevation="2">
      <v-card-text class="d-flex justify-space-between align-center py-3">
        <div class="d-flex align-center">
          <v-icon size="large" color="primary" class="mr-2">mdi-cog</v-icon>
          <span class="text-h6">系统配置</span>
        </div>
        <v-btn
          color="warning"
          variant="flat"
          :disabled="!hasUnsavedChanges"
          @click="saveConfig"
        >
          <v-icon start>mdi-content-save</v-icon>
          保存配置
        </v-btn>
      </v-card-text>
    </v-card>

    <!-- 配置内容 -->
    <v-card elevation="2">
      <div class="d-flex flex-row">
        <v-tabs
          v-model="activeTab"
          direction="vertical"
          color="primary"
          class="border-e"
          style="min-width: 160px;"
        >
          <v-tab value="base">
            <v-badge dot color="error" :model-value="dirtyTabs.has('base')">
              基础配置
            </v-badge>
          </v-tab>
          <v-tab value="courseSelect">
            <v-badge dot color="error" :model-value="dirtyTabs.has('courseSelect')">
              选课配置
            </v-badge>
          </v-tab>
          <v-tab value="schedule">
            <v-badge dot color="error" :model-value="dirtyTabs.has('schedule')">
              排课配置
            </v-badge>
          </v-tab>
          <v-tab value="ai">
            <v-badge dot color="error" :model-value="dirtyTabs.has('ai')">
              大模型配置
            </v-badge>
          </v-tab>
        </v-tabs>

        <v-window v-model="activeTab" class="flex-grow-1 pa-6">
          <!-- 基础配置 -->
          <v-window-item value="base">
            <v-row>
              <v-col cols="12" md="8">
                <v-text-field
                  v-model="config.base.systemName"
                  label="系统名称"
                  hint="显示在登录页和顶部标题栏"
                  persistent-hint
                  variant="outlined"
                  class="mb-4"
                ></v-text-field>
                
                <div class="text-subtitle-2 mb-2 text-grey-darken-1">登录页背景图</div>
                <v-radio-group v-model="config.base.loginBg" inline class="mb-2">
                  <v-radio
                    v-for="bg in bgOptions"
                    :key="bg.value"
                    :label="bg.label"
                    :value="bg.value"
                  ></v-radio>
                </v-radio-group>
                <v-img
                  :src="currentBgPreview"
                  width="300"
                  height="200"
                  cover
                  class="rounded mb-6 elevation-2"
                ></v-img>

                <v-text-field
                  v-model.number="config.base.sessionTimeout"
                  label="会话超时时间 (分钟)"
                  type="number"
                  min="10"
                  variant="outlined"
                  class="mb-4"
                  style="max-width: 300px;"
                ></v-text-field>

                <v-text-field
                  v-model="config.base.defaultPwd"
                  label="默认密码"
                  variant="outlined"
                  class="mb-6"
                  style="max-width: 300px;"
                ></v-text-field>

                <v-btn variant="outlined" color="error" @click="resetTabConfig">
                  <v-icon start>mdi-restore</v-icon>
                  重置为默认值
                </v-btn>
              </v-col>
            </v-row>
          </v-window-item>

          <!-- 选课配置 -->
          <v-window-item value="courseSelect">
            <v-row>
              <v-col cols="12" md="8">
                <div class="text-subtitle-2 mb-2 text-grey-darken-1">选课周期</div>
                <div class="d-flex align-center gap-4 mb-6">
                  <v-text-field
                    v-model="config.courseSelect.periodStart"
                    type="date"
                    label="开始日期"
                    variant="outlined"
                    hide-details
                  ></v-text-field>
                  <span>至</span>
                  <v-text-field
                    v-model="config.courseSelect.periodEnd"
                    type="date"
                    label="结束日期"
                    variant="outlined"
                    hide-details
                  ></v-text-field>
                </div>

                <v-text-field
                  v-model.number="config.courseSelect.maxCourses"
                  label="每人最大选课数"
                  type="number"
                  min="1"
                  variant="outlined"
                  class="mb-4"
                  style="max-width: 300px;"
                ></v-text-field>

                <v-switch
                  v-model="config.courseSelect.priorityEnabled"
                  label="志愿优先级生效"
                  color="primary"
                  hint="开启后按志愿顺序分配课程"
                  persistent-hint
                  class="mb-2"
                ></v-switch>

                <v-switch
                  v-model="config.courseSelect.conflictCheck"
                  label="选课冲突检测"
                  color="primary"
                  hint="开启后禁止选择时间冲突的课程"
                  persistent-hint
                  class="mb-6"
                ></v-switch>

                <v-btn variant="outlined" color="error" @click="resetTabConfig">重置本页</v-btn>
              </v-col>
            </v-row>
          </v-window-item>

          <!-- 排课配置 -->
          <v-window-item value="schedule">
            <v-row>
              <v-col cols="12" md="8">
                <v-select
                  v-model="config.schedule.timeRange"
                  :items="timeRangeOptions"
                  label="排课时间范围"
                  variant="outlined"
                  class="mb-4"
                ></v-select>

                <v-text-field
                  v-model.number="config.schedule.maxDailyPeriods"
                  label="每天最大课时"
                  type="number"
                  variant="outlined"
                  class="mb-4"
                  style="max-width: 300px;"
                ></v-text-field>

                <v-text-field
                  v-model.number="config.schedule.teacherMaxDailyPeriods"
                  label="教师单日最大课时"
                  type="number"
                  variant="outlined"
                  class="mb-4"
                  style="max-width: 300px;"
                ></v-text-field>

                <div class="text-subtitle-2 mb-2 text-grey-darken-1">教室利用率目标 ({{ config.schedule.utilizationTarget }}%)</div>
                <v-slider
                  v-model="config.schedule.utilizationTarget"
                  min="60"
                  max="100"
                  step="1"
                  thumb-label
                  color="primary"
                  class="mb-6"
                ></v-slider>

                <v-btn variant="outlined" color="error" @click="resetTabConfig">重置本页</v-btn>
              </v-col>
            </v-row>
          </v-window-item>

          <!-- 大模型配置 -->
          <v-window-item value="ai">
             <v-row>
              <v-col cols="12" md="8">
                <v-select
                  v-model="config.ai.modelProvider"
                  :items="aiProviders"
                  label="大模型选择"
                  variant="outlined"
                  class="mb-4"
                ></v-select>

                <v-switch
                  v-model="config.ai.streamResponse"
                  label="流式响应"
                  color="primary"
                  hint="开启后逐字显示回答"
                  persistent-hint
                  class="mb-2"
                ></v-switch>

                <v-text-field
                  v-model.number="config.ai.cacheMinutes"
                  label="缓存有效期 (分钟)"
                  type="number"
                  variant="outlined"
                  class="mb-4"
                  style="max-width: 300px;"
                ></v-text-field>

                <v-switch
                  v-model="config.ai.sensitiveFilter"
                  label="敏感词过滤"
                  color="primary"
                  class="mb-6"
                ></v-switch>

                <v-btn variant="outlined" color="error" @click="resetTabConfig">重置本页</v-btn>
              </v-col>
            </v-row>
          </v-window-item>
        </v-window>
      </div>
    </v-card>

    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="3000"
      location="top"
    >
      {{ snackbar.text }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar.show = false">关闭</v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<style scoped>
/* .config-container { height: 100%; } */
</style>
