<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Setting, Check, RefreshLeft } from '@element-plus/icons-vue'

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

// 背景图选项
const bgOptions = [
  { value: 'bg1', label: '背景1', preview: 'https://picsum.photos/300/200?random=1' },
  { value: 'bg2', label: '背景2', preview: 'https://picsum.photos/300/200?random=2' },
  { value: 'bg3', label: '背景3', preview: 'https://picsum.photos/300/200?random=3' }
]

// 大模型选项
const aiProviders = ['通义千问', 'DeepSeek', '讯飞星火']

// 时间范围选项
const timeRangeOptions = [
  '周一至周五 8:00-18:00',
  '周一至周五 7:30-17:30',
  '周一至周日 8:00-20:00'
]

// --- 4. 核心逻辑 ---

// 加载配置（从 localStorage）
const loadConfig = () => {
  const saved = localStorage.getItem('system_config')
  if (saved) {
    try {
      const parsed = JSON.parse(saved)
      Object.assign(config, parsed)
      originalConfig.value = JSON.parse(JSON.stringify(parsed))
    } catch (e) {
      console.error('Failed to load config:', e)
    }
  }
}

// 保存配置
const saveConfig = () => {
  // 真实场景下需调用接口保存到数据库，此处为本地演示
  localStorage.setItem('system_config', JSON.stringify(config))
  originalConfig.value = JSON.parse(JSON.stringify(config))
  dirtyTabs.value.clear()
  ElMessage.success('配置保存成功')
}

// 重置当前标签页配置
const resetTabConfig = () => {
  ElMessageBox.confirm('确定要重置当前标签页的配置为默认值吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    const tabKey = activeTab.value as keyof SystemConfig
    config[tabKey] = JSON.parse(JSON.stringify(defaultConfig[tabKey]))
    dirtyTabs.value.delete(activeTab.value)
    ElMessage.success('已重置为默认值')
  })
}

// 监听配置变化，标记未保存
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

// 切换标签页前检查
const beforeTabChange = (tab: string) => {
  if (dirtyTabs.value.has(activeTab.value)) {
    ElMessageBox.confirm('当前标签页有未保存的配置，是否放弃？', '提示', {
      confirmButtonText: '放弃',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(() => {
      // 恢复原配置
      const tabKey = activeTab.value as keyof SystemConfig
      config[tabKey] = JSON.parse(JSON.stringify(originalConfig.value[tabKey]))
      dirtyTabs.value.delete(activeTab.value)
      activeTab.value = tab
    }).catch(() => {
      // 留在当前标签
    })
    return false
  }
  return true
}

// 是否有未保存的配置
const hasUnsavedChanges = computed(() => dirtyTabs.value.size > 0)

// 当前背景图预览
const currentBgPreview = computed(() => {
  const bg = bgOptions.find(b => b.value === config.base.loginBg)
  return bg?.preview || ''
})

// 加载配置
loadConfig()
</script>

<template>
  <div class="system-config-container">
    <!-- 顶部操作栏 -->
    <el-card class="header-card">
      <div class="header-bar">
        <h2><el-icon><Setting /></el-icon> 系统配置</h2>
        <el-button 
          type="primary" 
          :icon="Check" 
          @click="saveConfig"
          :disabled="!hasUnsavedChanges"
          color="#FAAD14"
          style="color: white"
        >
          保存配置
        </el-button>
      </div>
    </el-card>

    <!-- 配置标签页 -->
    <el-card class="tabs-card">
      <el-tabs v-model="activeTab" @tab-click="(tab) => beforeTabChange(tab.props.name as string)">
        <!-- 基础配置 -->
        <el-tab-pane name="base">
          <template #label>
            <span :class="{ 'dirty-tab': dirtyTabs.has('base') }">
              基础配置{{ dirtyTabs.has('base') ? ' *' : '' }}
            </span>
          </template>
          <el-form :model="config.base" label-width="150px" class="config-form">
            <el-form-item label="系统名称">
              <el-input v-model="config.base.systemName" placeholder="请输入系统名称" style="width: 400px" />
              <div class="config-tip">系统名称：显示在登录页和顶部标题栏</div>
            </el-form-item>
            
            <el-form-item label="登录页背景图">
              <el-radio-group v-model="config.base.loginBg">
                <el-radio v-for="bg in bgOptions" :key="bg.value" :label="bg.value">{{ bg.label }}</el-radio>
              </el-radio-group>
              <div class="bg-preview">
                <img :src="currentBgPreview" alt="背景预览" />
              </div>
            </el-form-item>
            
            <el-form-item label="会话超时时间">
              <el-input-number v-model="config.base.sessionTimeout" :min="10" :max="1440" style="width: 200px" />
              <span style="margin-left: 10px">分钟</span>
              <div class="config-tip">会话超时时间：用户无操作多久后自动退出登录（需≥10分钟）</div>
            </el-form-item>
            
            <el-form-item label="默认密码">
              <el-input v-model="config.base.defaultPwd" placeholder="请输入默认密码" style="width: 200px" />
              <div class="config-tip">默认密码：新增用户和密码重置时使用的默认密码</div>
            </el-form-item>
            
            <el-form-item>
              <el-button :icon="RefreshLeft" @click="resetTabConfig">重置为默认值</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 选课配置 -->
        <el-tab-pane name="courseSelect">
          <template #label>
            <span :class="{ 'dirty-tab': dirtyTabs.has('courseSelect') }">
              选课配置{{ dirtyTabs.has('courseSelect') ? ' *' : '' }}
            </span>
          </template>
          <el-form :model="config.courseSelect" label-width="150px" class="config-form">
            <el-form-item label="选课周期">
              <el-date-picker
                v-model="config.courseSelect.periodStart"
                type="date"
                placeholder="开始日期"
                value-format="YYYY-MM-DD"
                style="width: 180px"
              />
              <span style="margin: 0 10px">至</span>
              <el-date-picker
                v-model="config.courseSelect.periodEnd"
                type="date"
                placeholder="结束日期"
                value-format="YYYY-MM-DD"
                style="width: 180px"
              />
              <div class="config-tip">选课周期：学生可以选课的时间范围</div>
            </el-form-item>
            
            <el-form-item label="每人最大选课数">
              <el-input-number v-model="config.courseSelect.maxCourses" :min="1" :max="10" style="width: 150px" />
              <span style="margin-left: 10px">门</span>
              <div class="config-tip">每人最大选课数：限制每个学生最多可选择的课程数量（1-10门）</div>
            </el-form-item>
            
            <el-form-item label="志愿优先级生效">
              <el-switch v-model="config.courseSelect.priorityEnabled" />
              <div class="config-tip">志愿优先级生效：开启后按志愿顺序分配课程，关闭后按选课时间先后排序</div>
            </el-form-item>
            
            <el-form-item label="选课冲突检测">
              <el-switch v-model="config.courseSelect.conflictCheck" />
              <div class="config-tip">选课冲突检测：开启后禁止选择时间冲突的课程，关闭后允许冲突</div>
            </el-form-item>
            
            <el-form-item>
              <el-button :icon="RefreshLeft" @click="resetTabConfig">重置为默认值</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 排课配置 -->
        <el-tab-pane name="schedule">
          <template #label>
            <span :class="{ 'dirty-tab': dirtyTabs.has('schedule') }">
              排课配置{{ dirtyTabs.has('schedule') ? ' *' : '' }}
            </span>
          </template>
          <el-form :model="config.schedule" label-width="180px" class="config-form">
            <el-form-item label="排课时间范围">
              <el-select v-model="config.schedule.timeRange" style="width: 250px">
                <el-option v-for="range in timeRangeOptions" :key="range" :label="range" :value="range" />
              </el-select>
              <div class="config-tip">排课时间范围：遗传算法生成排课表时的时间约束</div>
              <div class="time-preview" v-if="config.schedule.timeRange">
                示例时间段：{{ config.schedule.timeRange }}
              </div>
            </el-form-item>
            
            <el-form-item label="每天最大课时">
              <el-input-number v-model="config.schedule.maxDailyPeriods" :min="3" :max="8" style="width: 150px" />
              <span style="margin-left: 10px">节</span>
              <div class="config-tip">每天最大课时：每天最多安排的课程节数（3-8节）</div>
            </el-form-item>
            
            <el-form-item label="教师单日最大课时">
              <el-input-number v-model="config.schedule.teacherMaxDailyPeriods" :min="1" :max="5" style="width: 150px" />
              <span style="margin-left: 10px">节</span>
              <div class="config-tip">教师单日最大课时：单个教师每天最多授课节数（1-5节）</div>
            </el-form-item>
            
            <el-form-item label="教室利用率目标">
              <el-input-number v-model="config.schedule.utilizationTarget" :min="60" :max="100" style="width: 150px" />
              <span style="margin-left: 10px">%</span>
              <div class="config-tip">教室利用率目标：影响排课算法的优化方向，目标利用率设置为60%-100%</div>
            </el-form-item>
            
            <el-form-item>
              <el-button :icon="RefreshLeft" @click="resetTabConfig">重置为默认值</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 大模型配置 -->
        <el-tab-pane name="ai">
          <template #label>
            <span :class="{ 'dirty-tab': dirtyTabs.has('ai') }">
              大模型配置{{ dirtyTabs.has('ai') ? ' *' : '' }}
            </span>
          </template>
          <el-form :model="config.ai" label-width="150px" class="config-form">
            <el-form-item label="大模型选择">
              <el-select v-model="config.ai.modelProvider" style="width: 200px">
                <el-option v-for="provider in aiProviders" :key="provider" :label="provider" :value="provider" />
              </el-select>
              <div class="config-tip">大模型选择：用于智能问答和教案生成的AI服务提供商</div>
            </el-form-item>
            
            <el-form-item label="流式响应">
              <el-switch v-model="config.ai.streamResponse" />
              <div class="config-tip">流式响应：开启后逐字显示回答（类似打字效果），关闭后完整加载后显示</div>
            </el-form-item>
            
            <el-form-item label="缓存有效期">
              <el-input-number v-model="config.ai.cacheMinutes" :min="10" :max="1440" style="width: 150px" />
              <span style="margin-left: 10px">分钟</span>
              <div class="config-tip">缓存有效期：相同问题缓存多久，减少重复请求（10-1440分钟）</div>
            </el-form-item>
            
            <el-form-item label="敏感词过滤">
              <el-switch v-model="config.ai.sensitiveFilter" />
              <div class="config-tip">敏感词过滤：开启后检测并过滤敏感词汇，关闭后不检测</div>
            </el-form-item>
            
            <el-form-item>
              <el-button :icon="RefreshLeft" @click="resetTabConfig">重置为默认值</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<style scoped>
.system-config-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.header-card {
  flex-shrink: 0;
}
.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-bar h2 {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
}
.tabs-card {
  flex: 1;
  overflow: auto;
}
.config-form {
  padding: 20px 0;
}
.config-form :deep(.el-form-item) {
  margin-bottom: 24px;
}
.config-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
  line-height: 1.5;
}
.dirty-tab {
  color: #F56C6C;
  font-weight: bold;
}
.bg-preview {
  margin-top: 15px;
  padding: 10px;
  border: 1px solid #DCDFE6;
  border-radius: 4px;
  background: #F5F7FA;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
.bg-preview img {
  max-width: 300px;
  border-radius: 4px;
}
.time-preview {
  margin-top: 10px;
  padding: 10px;
  background: #FFF7E6;
  border-left: 4px solid #FAAD14;
  color: #606266;
  font-size: 13px;
}
</style>
