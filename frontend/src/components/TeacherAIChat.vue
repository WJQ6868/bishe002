<script setup lang="ts">
import { ref, reactive, onMounted, nextTick, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  ChatRound, Plus, Delete, Edit, MoreFilled, 
  Microphone, FolderAdd, Picture, Document, 
  CopyDocument, RefreshRight, Back, Close,
  ArrowDown, Timer, Monitor, Cpu, ChatDotRound,
  Download, DataLine, AlarmClock
} from '@element-plus/icons-vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import * as echarts from 'echarts'

const router = useRouter()

// 配置 marked
marked.setOptions({
  highlight: function (code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value
    }
    return hljs.highlightAuto(code).value
  },
  breaks: true
})

// --- 1. 类型定义 ---
interface ChatMessage {
  id: string
  role: 'user' | 'ai'
  content: string
  timestamp: number
  isStreaming?: boolean
  modelName?: string
  operable?: boolean
  // 教师端专属
  scene?: string 
  exportable?: boolean // 是否可导出教案
  chartData?: any // 图表数据
  reservationLink?: string // 预约链接资源名
}

interface Session {
  id: string
  title: string
  messages: ChatMessage[]
  timestamp: number
  unread: boolean
  model: string
}

interface ModelAuth {
  model: string
  name: string
  isConfigured: boolean
  teacherAuth: boolean
}

// --- 2. 状态管理 ---
const isVisible = ref(false)
const inputContent = ref('')
const loading = ref(false)
const chatContainerRef = ref<HTMLElement>()
const isRecording = ref(false)
const recognition = ref<any>(null)

// 图表弹窗
const chartDialogVisible = ref(false)
const chartType = ref<'bar' | 'pie'>('bar')
const currentChartData = ref<any>(null)
const chartRef = ref<HTMLElement>()
let myChart: any = null

// 会话管理
const sessions = ref<Session[]>([])
const currentSessionId = ref('')
const currentSession = computed(() => sessions.value.find(s => s.id === currentSessionId.value))

// 模型相关
const availableModels = ref<ModelAuth[]>([])
const allowUserSwitchModel = ref(true)
const keepSessionOnSwitch = ref(true)

// 场景快捷入口
const sceneShortcuts = [
  { label: '教案生成', prompt: '生成Python编程课程第3章教案，含教学目标、重难点、教学步骤' },
  { label: '成绩分析', prompt: '请分析上传的成绩表格，计算平均分、及格率并生成统计图表' },
  { label: '资源预约咨询', prompt: '我想预约下周三下午的计算机实验室，有哪些可用资源？' },
  { label: '教学问题解答', prompt: '如何提高学生在编程课上的互动积极性？' }
]

// 管理员配置
const aiConfig = reactive({
  enableStream: true,
  enableVoiceInput: true,
  enableFileUpload: false,
  allowedFileTypes: ['doc', 'pdf', 'image', 'excel'],
  recallTimeLimit: 5
})

// --- 3. 核心逻辑 ---

onMounted(() => {
  initData()
  initSpeechRecognition()
})

const initData = () => {
  // 1. 读取配置
  const savedConfig = localStorage.getItem('ai_chat_config')
  if (savedConfig) {
    const config = JSON.parse(savedConfig)
    aiConfig.enableStream = config.functions?.enableStream ?? true
    aiConfig.enableVoiceInput = config.functions?.enableVoiceInput ?? true
    aiConfig.enableFileUpload = config.functions?.enableFileUpload ?? false
    aiConfig.allowedFileTypes = config.functions?.allowedFileTypes || ['doc', 'pdf', 'image', 'excel']
    aiConfig.recallTimeLimit = config.functions?.recallTimeLimit || 5
    
    if (config.modelAuths) {
      availableModels.value = config.modelAuths.filter((m: ModelAuth) => m.teacherAuth && m.isConfigured)
    }
    if (config.functions) {
      allowUserSwitchModel.value = config.functions.allowUserSwitchModel
      keepSessionOnSwitch.value = config.functions.keepSessionOnSwitch
    }
  } else {
    availableModels.value = [{ model: 'tongyi', name: '通义千问', isConfigured: true, teacherAuth: true }]
  }

  // 2. 读取会话历史
  const savedSessions = localStorage.getItem('teacher_ai_sessions')
  if (savedSessions) {
    sessions.value = JSON.parse(savedSessions)
  }
  
  if (sessions.value.length === 0) {
    createPresetSessions()
  } else {
    currentSessionId.value = sessions.value[0].id
  }
}

const createPresetSessions = () => {
  const now = Date.now()
  const preset: Session[] = [
    {
      id: '1',
      title: 'Python教案生成',
      timestamp: now,
      unread: false,
      model: 'tongyi',
      messages: [
        { id: '1-1', role: 'user', content: '生成Python循环结构教案', timestamp: now - 100000, operable: true },
        { 
          id: '1-2', 
          role: 'ai', 
          content: '### Python 循环结构教案\n\n**一、教学目标**\n1. 掌握 for 循环与 while 循环\n2. 理解 break 与 continue\n\n**二、教学过程**\n...', 
          timestamp: now - 90000, 
          modelName: '通义千问',
          exportable: true 
        }
      ]
    },
    {
      id: '2',
      title: '高等数学成绩分析',
      timestamp: now - 86400000,
      unread: true,
      model: 'tongyi',
      messages: [
        { id: '2-1', role: 'user', content: '分析高数期中成绩', timestamp: now - 86500000, operable: true },
        { 
          id: '2-2', 
          role: 'ai', 
          content: '已分析成绩数据：\n- **平均分**：78.5\n- **及格率**：85%\n建议关注不及格学生。', 
          timestamp: now - 86400000, 
          modelName: '通义千问',
          chartData: {
            categories: ['60分以下', '60-70', '70-80', '80-90', '90以上'],
            data: [5, 10, 15, 12, 8]
          }
        }
      ]
    }
  ]
  sessions.value = preset
  currentSessionId.value = '1'
}

// 语音识别初始化
const initSpeechRecognition = () => {
  if ('webkitSpeechRecognition' in window) {
    // @ts-ignore
    recognition.value = new webkitSpeechRecognition()
    recognition.value.continuous = false
    recognition.value.interimResults = false
    recognition.value.lang = 'zh-CN'
    
    recognition.value.onresult = (event: any) => {
      const text = event.results[0][0].transcript
      inputContent.value += text
      isRecording.value = false
      ElMessage.success('语音识别成功')
    }
    
    recognition.value.onerror = (event: any) => {
      isRecording.value = false
      ElMessage.error('语音识别失败')
    }
    
    recognition.value.onend = () => {
      isRecording.value = false
    }
  }
}

watch(sessions, (newVal) => {
  localStorage.setItem('teacher_ai_sessions', JSON.stringify(newVal))
}, { deep: true })

const toggleChat = () => {
  isVisible.value = !isVisible.value
  if (isVisible.value) {
    scrollToBottom()
    if (currentSession.value) currentSession.value.unread = false
  }
}

const createNewSession = () => {
  const now = Date.now()
  const newSession: Session = {
    id: now.toString(),
    title: `未命名会话-${new Date().toLocaleDateString()}`,
    messages: [{
      id: 'welcome',
      role: 'ai',
      content: '老师您好！我是您的智能教学助手，可以帮您生成教案、分析成绩或预约资源。',
      timestamp: now,
      modelName: '系统'
    }],
    timestamp: now,
    unread: false,
    model: availableModels.value[0]?.model || 'tongyi'
  }
  sessions.value.unshift(newSession)
  currentSessionId.value = newSession.id
  scrollToBottom()
}

const deleteSession = (id: string, e?: Event) => {
  e?.stopPropagation()
  ElMessageBox.confirm('确定要删除该会话吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    const index = sessions.value.findIndex(s => s.id === id)
    sessions.value.splice(index, 1)
    if (sessions.value.length === 0) {
      createNewSession()
    } else if (currentSessionId.value === id) {
      currentSessionId.value = sessions.value[0].id
    }
    ElMessage.success('会话已删除')
  })
}

const clearAllSessions = () => {
  ElMessageBox.confirm('确定要清空所有会话记录吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    sessions.value = []
    createNewSession()
    ElMessage.success('已清空所有会话')
  })
}

const renameSession = () => {
  if (!currentSession.value) return
  ElMessageBox.prompt('请输入新的会话标题', '重命名', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    inputValue: currentSession.value.title,
    inputValidator: (val) => !!val.trim() || '标题不能为空'
  }).then(({ value }) => {
    if (currentSession.value) {
      currentSession.value.title = value
    }
  })
}

const switchSession = (id: string) => {
  currentSessionId.value = id
  if (currentSession.value) currentSession.value.unread = false
  scrollToBottom()
}

const handleModelSwitch = (modelKey: string) => {
  if (!currentSession.value || currentSession.value.model === modelKey) return
  
  const targetModelName = availableModels.value.find(m => m.model === modelKey)?.name || modelKey
  
  if (!keepSessionOnSwitch.value) {
    currentSession.value.messages = [{
      id: Date.now().toString(),
      role: 'ai',
      content: `已切换至【${targetModelName}】模型，会话已重置。`,
      timestamp: Date.now(),
      modelName: '系统'
    }]
  } else {
    currentSession.value.messages.push({
      id: Date.now().toString(),
      role: 'ai',
      content: `已切换至【${targetModelName}】模型，继续为您解答~`,
      timestamp: Date.now(),
      modelName: '系统'
    })
  }
  currentSession.value.model = modelKey
  scrollToBottom()
}

const handleSend = async (content: string = inputContent.value) => {
  if (!content.trim() || !currentSession.value) return

  const userMsg: ChatMessage = {
    id: Date.now().toString(),
    role: 'user',
    content: content,
    timestamp: Date.now(),
    operable: true
  }
  currentSession.value.messages.push(userMsg)
  
  if (currentSession.value.messages.length <= 2 && currentSession.value.title.startsWith('未命名')) {
    currentSession.value.title = content.substring(0, 10) + (content.length > 10 ? '...' : '')
  }
  currentSession.value.timestamp = Date.now()

  inputContent.value = ''
  scrollToBottom()
  loading.value = true

  const aiMsgId = (Date.now() + 1).toString()
  const modelKey = currentSession.value.model
  const modelName = availableModels.value.find(m => m.model === modelKey)?.name || 'AI'
  
  const aiMsg: ChatMessage = {
    id: aiMsgId,
    role: 'ai',
    content: '',
    timestamp: Date.now(),
    isStreaming: true,
    modelName: modelName
  }
  currentSession.value.messages.push(aiMsg)

  let fullResponse = ''
  
  // 教师端专属模拟逻辑
  if (content.includes('教案')) {
    fullResponse = `### Python 课程教案框架\n\n**一、教学目标**\n1. 理解 Python 基础语法\n2. 掌握变量与数据类型\n\n**二、教学重难点**\n- 重点：变量定义\n- 难点：动态类型理解\n\n**三、教学过程**\n1. 导入 (5分钟)\n2. 讲解 (20分钟)\n3. 练习 (15分钟)\n\n**四、作业布置**\n完成课后习题 1-5`
    aiMsg.exportable = true
  } else if (content.includes('成绩') || content.includes('分析')) {
    fullResponse = `已分析上传的成绩表格：\n- **平均分**：82.5\n- **及格率**：93%\n- **最高分**：98 (李四)\n\n建议关注不及格学生，安排辅导。`
    aiMsg.chartData = {
      categories: ['60分以下', '60-70', '70-80', '80-90', '90以上'],
      data: [3, 8, 18, 15, 6]
    }
  } else if (content.includes('预约') || content.includes('资源')) {
    fullResponse = `为您找到以下可用资源：\n1. **第一计算机实验室** (周三 14:00-16:00)\n2. **多媒体教室 302** (周三 14:00-16:00)\n\n您可以点击下方按钮一键预约。`
    aiMsg.reservationLink = '第一计算机实验室'
  } else {
    fullResponse = `(由 ${modelName} 生成) 收到您的问题：“${content}”。\n正在为您查找相关教学资料...`
  }

  const chars = fullResponse.split('')
  let index = 0
  const speed = 30

  const streamInterval = setInterval(() => {
    if (index < chars.length) {
      aiMsg.content += chars[index]
      index++
      scrollToBottom()
    } else {
      clearInterval(streamInterval)
      aiMsg.isStreaming = false
      loading.value = false
    }
  }, speed) 
}

const toggleRecording = () => {
  if (!recognition.value) {
    ElMessage.warning('当前浏览器不支持语音输入，请使用 Chrome')
    setTimeout(() => {
      inputContent.value += '请帮我生成一份Java课程的期末复习教案'
      ElMessage.success('模拟语音识别成功')
    }, 1500)
    return
  }
  
  if (isRecording.value) {
    recognition.value.stop()
  } else {
    isRecording.value = true
    recognition.value.start()
    ElMessage.info('请开始说话...')
  }
}

const handleFileUpload = () => {
  ElMessage.success('模拟文件上传成功：grade_sheet.xlsx')
  inputContent.value += '[已上传文件: grade_sheet.xlsx] '
}

const copyContent = (text: string) => {
  navigator.clipboard.writeText(text)
  ElMessage.success('复制成功')
}

const recallMessage = (msg: ChatMessage) => {
  const now = Date.now()
  const diffMinutes = (now - msg.timestamp) / 1000 / 60
  if (diffMinutes > aiConfig.recallTimeLimit) {
    ElMessage.warning(`超过 ${aiConfig.recallTimeLimit} 分钟无法撤回`)
    return
  }
  
  if (currentSession.value) {
    const index = currentSession.value.messages.findIndex(m => m.id === msg.id)
    if (index !== -1) {
      currentSession.value.messages.splice(index, 1)
      ElMessage.success('已撤回一条消息')
    }
  }
}

const regenerateMsg = (msg: ChatMessage) => {
  if (!currentSession.value) return
  const index = currentSession.value.messages.findIndex(m => m.id === msg.id)
  if (index > 0) {
    const lastUserMsg = currentSession.value.messages[index - 1]
    if (lastUserMsg.role === 'user') {
      currentSession.value.messages.splice(index, 1)
      handleSend(lastUserMsg.content)
    }
  }
}

// 教师专属操作
const exportLessonPlan = () => {
  const loadingMsg = ElMessage.loading({
    message: '正在导出教案...',
    duration: 0
  })
  setTimeout(() => {
    loadingMsg.close()
    ElMessage.success('教案导出成功 (模拟下载 lesson_plan.docx)')
  }, 1000)
}

const showChart = (data: any) => {
  currentChartData.value = data
  chartDialogVisible.value = true
  nextTick(() => {
    initChart()
  })
}

const initChart = () => {
  if (!chartRef.value || !currentChartData.value) return
  if (myChart) myChart.dispose()
  
  myChart = echarts.init(chartRef.value)
  const option = {
    title: { text: '成绩分布统计' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: currentChartData.value.categories },
    yAxis: { type: 'value' },
    series: [{
      data: currentChartData.value.data,
      type: chartType.value,
      itemStyle: { color: '#52C41A' }
    }]
  }
  myChart.setOption(option)
}

watch(chartType, () => {
  initChart()
})

const handleReservation = (resourceName: string) => {
  ElMessage.success(`正在跳转预约：${resourceName}`)
  // 实际项目中可携带参数跳转
  router.push('/teacher/resource-reservation')
  toggleChat()
}

const renderMarkdown = (content: string) => {
  return marked(content)
}

const formatTime = (timestamp: number) => {
  return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const formatSessionTime = (timestamp: number) => {
  const date = new Date(timestamp)
  const now = new Date()
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
  return date.toLocaleDateString()
}

const scrollToBottom = () => {
  nextTick(() => {
    if (chatContainerRef.value) {
      chatContainerRef.value.scrollTop = chatContainerRef.value.scrollHeight
    }
  })
}

const useSceneShortcut = (prompt: string) => {
  inputContent.value = prompt
  // 自动聚焦输入框 (简单模拟)
  const textarea = document.querySelector('.custom-input') as HTMLTextAreaElement
  if (textarea) textarea.focus()
}

const currentModelName = computed(() => {
  if (!currentSession.value) return ''
  return availableModels.value.find(m => m.model === currentSession.value?.model)?.name || 'AI'
})

</script>

<template>
  <div>
    <!-- 悬浮触发按钮 -->
    <div class="float-trigger" @click="toggleChat" v-if="!isVisible">
      <el-icon :size="28"><ChatRound /></el-icon>
      <span class="trigger-text">AI助手</span>
    </div>

    <!-- 聊天主窗口 (Modal) -->
    <div class="chat-modal-overlay" v-if="isVisible" @click.self="toggleChat">
      <div class="chat-modal">
        
        <!-- 左侧会话列表 -->
        <div class="sidebar">
          <div class="sidebar-header">
            <span class="app-name">教学助手</span>
            <el-button type="primary" size="small" :icon="Plus" class="new-chat-btn" @click="createNewSession">
              新建会话
            </el-button>
          </div>
          
          <div class="session-list">
            <div 
              v-for="session in sessions" 
              :key="session.id" 
              class="session-card"
              :class="{ active: currentSessionId === session.id }"
              @click="switchSession(session.id)"
              @contextmenu.prevent="deleteSession(session.id)"
            >
              <div class="session-main">
                <div class="session-title-row">
                  <span class="session-title">{{ session.title }}</span>
                  <span class="session-time">{{ formatSessionTime(session.timestamp) }}</span>
                </div>
                <div class="session-preview">
                  {{ session.messages[session.messages.length - 1]?.content.substring(0, 15) }}...
                </div>
              </div>
              <div class="unread-dot" v-if="session.unread"></div>
            </div>
          </div>

          <div class="sidebar-footer">
            <el-button link type="danger" :icon="Delete" @click="clearAllSessions">清除所有会话</el-button>
          </div>
        </div>

        <!-- 右侧聊天区 -->
        <div class="main-area">
          <!-- 顶部 Header -->
          <div class="chat-header">
            <div class="header-left">
              <span class="current-title">{{ currentSession?.title }}</span>
              <el-icon class="edit-icon" @click="renameSession"><Edit /></el-icon>
            </div>
            
            <div class="header-right">
              <!-- 模型选择 -->
              <el-dropdown trigger="click" @command="handleModelSwitch" v-if="allowUserSwitchModel">
                <span class="model-select">
                  <el-icon><Cpu /></el-icon>
                  {{ currentModelName }}
                  <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item 
                      v-for="m in availableModels" 
                      :key="m.model" 
                      :command="m.model"
                      :disabled="currentSession?.model === m.model"
                    >
                      {{ m.name }}
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>

              <el-dropdown trigger="click">
                <el-icon class="more-btn"><MoreFilled /></el-icon>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item :icon="Delete" @click="deleteSession(currentSessionId)">删除会话</el-dropdown-item>
                    <el-dropdown-item :icon="RefreshRight" @click="currentSession!.messages = []">清空消息</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              
              <el-icon class="close-btn" @click="toggleChat"><Close /></el-icon>
            </div>
          </div>

          <!-- 消息列表 -->
          <div class="messages-area" ref="chatContainerRef">
            <div v-for="msg in currentSession?.messages" :key="msg.id" class="message-row" :class="msg.role">
              <div class="avatar" v-if="msg.role === 'ai'">
                <el-icon><ChatDotRound /></el-icon>
              </div>
              
              <div class="message-content-wrapper">
                <div class="bubble" :class="msg.role">
                  <div v-if="msg.role === 'ai'" class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
                  <div v-else>{{ msg.content }}</div>
                </div>
                
                <!-- 教师专属操作按钮 -->
                <div class="ai-tools" v-if="msg.role === 'ai' && !msg.isStreaming">
                  <el-button v-if="msg.exportable" size="small" :icon="Download" @click="exportLessonPlan">导出教案</el-button>
                  <el-button v-if="msg.chartData" size="small" :icon="DataLine" @click="showChart(msg.chartData)">查看统计图表</el-button>
                  <el-button v-if="msg.reservationLink" size="small" :icon="AlarmClock" @click="handleReservation(msg.reservationLink)">一键预约</el-button>
                </div>

                <div class="message-footer">
                  <span class="time">{{ formatTime(msg.timestamp) }}</span>
                  <div class="actions">
                    <span class="action-btn" @click="copyContent(msg.content)">复制</span>
                    <span class="action-btn" v-if="msg.role === 'user' && msg.operable" @click="recallMessage(msg)">撤回</span>
                    <span class="action-btn" v-if="msg.role === 'ai'" @click="regenerateMsg(msg)">重新生成</span>
                  </div>
                </div>
              </div>

              <div class="avatar user-avatar" v-if="msg.role === 'user'">
                <span>我</span>
              </div>
            </div>

            <div v-if="loading" class="loading-indicator">
              <span class="dot"></span><span class="dot"></span><span class="dot"></span> AI正在思考...
            </div>
          </div>

          <!-- 输入区 -->
          <div class="input-area">
            <!-- 场景快捷入口 -->
            <div class="scene-shortcuts">
              <el-tag 
                v-for="scene in sceneShortcuts" 
                :key="scene.label" 
                class="scene-tag" 
                effect="light" 
                @click="useSceneShortcut(scene.prompt)"
              >
                {{ scene.label }}
              </el-tag>
            </div>

            <div class="input-box">
              <div class="input-tools">
                <el-tooltip content="语音输入" placement="top">
                  <el-icon class="tool-icon" :class="{ recording: isRecording }" @click="toggleRecording"><Microphone /></el-icon>
                </el-tooltip>
                <el-tooltip content="导入教案/成绩表" placement="top">
                  <el-icon class="tool-icon" @click="handleFileUpload"><FolderAdd /></el-icon>
                </el-tooltip>
                <el-icon class="tool-icon"><Picture /></el-icon>
              </div>
              
              <textarea 
                v-model="inputContent"
                class="custom-input"
                placeholder="输入您的问题，支持语音、文件辅助说明..."
                @keydown.enter.prevent="handleSend()"
              ></textarea>
              
              <el-button 
                type="primary" 
                class="send-btn" 
                :disabled="!inputContent.trim()" 
                @click="handleSend()"
              >
                发送
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 图表弹窗 -->
    <el-dialog v-model="chartDialogVisible" title="成绩分析图表" width="600px">
      <div class="chart-toolbar">
        <el-radio-group v-model="chartType" size="small">
          <el-radio-button label="bar">柱状图</el-radio-button>
          <el-radio-button label="pie">饼图</el-radio-button>
        </el-radio-group>
      </div>
      <div ref="chartRef" style="width: 100%; height: 400px;"></div>
    </el-dialog>
  </div>
</template>

<style scoped>
/* Markdown 样式 */
:deep(.markdown-body) {
  font-size: 14px;
  line-height: 1.6;
  color: #333;
}
:deep(.markdown-body pre) {
  background: #f5f5f5;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 8px 0;
}
:deep(.markdown-body code) {
  font-family: Consolas, Monaco, monospace;
}
:deep(.markdown-body table) {
  border-collapse: collapse;
  width: 100%;
  margin: 10px 0;
}
:deep(.markdown-body th), :deep(.markdown-body td) {
  border: 1px solid #ddd;
  padding: 6px 10px;
}
:deep(.markdown-body a) {
  color: #52C41A;
  text-decoration: none;
}

/* 悬浮按钮 - 教师绿 */
.float-trigger {
  position: fixed;
  right: 30px;
  bottom: 30px;
  width: 60px;
  height: 60px;
  background: #52C41A;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 4px 12px rgba(82, 196, 26, 0.4);
  cursor: pointer;
  z-index: 2000;
  transition: transform 0.2s;
}
.float-trigger:hover {
  transform: scale(1.05);
}
.trigger-text {
  font-size: 10px;
  margin-top: 2px;
}

/* 模态框 */
.chat-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 2001;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-modal {
  width: 1000px;
  height: 800px;
  background: #fff;
  border-radius: 12px;
  display: flex;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

/* 左侧边栏 */
.sidebar {
  width: 280px;
  background: #f7f8fa;
  border-right: 1px solid #eef0f3;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.app-name {
  font-size: 18px;
  font-weight: bold;
  color: #333;
}
.new-chat-btn {
  border-radius: 16px;
  background-color: #52C41A;
  border-color: #52C41A;
}
.new-chat-btn:hover {
  background-color: #73d13d;
  border-color: #73d13d;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 10px;
}

.session-card {
  padding: 12px;
  margin-bottom: 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
  position: relative;
}
.session-card:hover {
  background: #eef0f3;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
.session-card.active {
  background: #F0F9EB; /* 教师端浅绿 */
}
.session-title-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}
.session-title {
  font-size: 14px;
  color: #333;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 160px;
}
.session-time {
  font-size: 12px;
  color: #999;
}
.session-preview {
  font-size: 12px;
  color: #666;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.unread-dot {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 8px;
  height: 8px;
  background: #F56C6C;
  border-radius: 50%;
}

.sidebar-footer {
  padding: 15px;
  border-top: 1px solid #eef0f3;
  text-align: center;
}

/* 右侧主区 */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.chat-header {
  height: 60px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}
.edit-icon {
  cursor: pointer;
  color: #909399;
  font-size: 14px;
}
.edit-icon:hover { color: #52C41A; }

.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}
.model-select {
  cursor: pointer;
  color: #606266;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
}
.model-select:hover { color: #52C41A; }
.more-btn, .close-btn {
  font-size: 20px;
  cursor: pointer;
  color: #909399;
}
.more-btn:hover, .close-btn:hover { color: #333; }

/* 消息区 */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #FAFAFA;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message-row {
  display: flex;
  gap: 12px;
  max-width: 85%;
}
.message-row.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}
.message-row.ai {
  align-self: flex-start;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.ai .avatar { background: #fff; color: #52C41A; border: 1px solid #e0e0e0; }
.user-avatar { background: #52C41A; color: #fff; font-size: 12px; }

.message-content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.bubble {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 15px;
  line-height: 1.6;
  word-break: break-all;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.ai .bubble { 
  background: #fff; 
  color: #333;
  border-top-left-radius: 2px;
}
.user .bubble { 
  background: #52C41A; 
  color: #fff;
  border-top-right-radius: 2px;
}

.ai-tools {
  display: flex;
  gap: 10px;
  margin-top: 5px;
}

.message-footer {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: #999;
  opacity: 0;
  transition: opacity 0.2s;
}
.message-row:hover .message-footer {
  opacity: 1;
}
.actions {
  display: flex;
  gap: 8px;
}
.action-btn {
  cursor: pointer;
}
.action-btn:hover { color: #52C41A; }

.loading-indicator {
  align-self: flex-start;
  margin-left: 50px;
  color: #999;
  font-size: 13px;
}
.dot {
  display: inline-block;
  width: 4px;
  height: 4px;
  background: #999;
  border-radius: 50%;
  margin-right: 2px;
  animation: bounce 1.4s infinite ease-in-out both;
}
.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* 输入区 */
.input-area {
  padding: 20px;
  background: #fff;
  border-top: 1px solid #f0f0f0;
}

.scene-shortcuts {
  margin-bottom: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.scene-tag {
  cursor: pointer;
  background-color: #F0F9EB;
  border-color: #e1f3d8;
  color: #67C23A;
}
.scene-tag:hover {
  background-color: #52C41A;
  color: #fff;
}

.input-box {
  border: 1px solid #dcdfe6;
  border-radius: 24px;
  padding: 10px 15px;
  display: flex;
  align-items: flex-end;
  gap: 10px;
  transition: all 0.2s;
  background: #fff;
}
.input-box:focus-within {
  border-color: #52C41A;
  box-shadow: 0 0 0 2px rgba(82, 196, 26, 0.1);
}

.input-tools {
  display: flex;
  gap: 10px;
  padding-bottom: 8px;
}
.tool-icon {
  font-size: 20px;
  color: #909399;
  cursor: pointer;
  transition: color 0.2s;
}
.tool-icon:hover { color: #52C41A; }
.tool-icon.recording { color: #F56C6C; animation: pulse 1.5s infinite; }

.custom-input {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  height: 60px;
  padding: 8px 0;
  font-size: 14px;
  line-height: 1.5;
  color: #333;
}
.custom-input::placeholder { color: #C0C4CC; }

.send-btn {
  border-radius: 20px;
  padding: 8px 20px;
  margin-bottom: 4px;
  background-color: #52C41A;
  border-color: #52C41A;
}
.send-btn:hover {
  background-color: #73d13d;
  border-color: #73d13d;
}
.send-btn.is-disabled {
  background-color: #a0cfff;
  border-color: #a0cfff;
}

.chart-toolbar {
  margin-bottom: 15px;
  text-align: right;
}

@keyframes pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); }
}
</style>
