<script setup lang="ts">
import { ref, reactive, onMounted, nextTick, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  ChatRound, Plus, Delete, Edit, MoreFilled, 
  Microphone, FolderAdd, Picture, Document, 
  CopyDocument, RefreshRight, Back, Close,
  ArrowDown, Timer, Monitor, Cpu, ChatDotRound
} from '@element-plus/icons-vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

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
  operable?: boolean // 是否可操作
}

interface Session {
  id: string
  title: string
  messages: ChatMessage[]
  timestamp: number
  unread: boolean
  model: string // 当前会话使用的模型
}

interface ModelAuth {
  model: string
  name: string
  isConfigured: boolean
  studentAuth: boolean
}

// --- 2. 状态管理 ---
const isVisible = ref(false)
const inputContent = ref('')
const loading = ref(false)
const chatContainerRef = ref<HTMLElement>()
const isRecording = ref(false)
const recognition = ref<any>(null)

// 会话管理
const sessions = ref<Session[]>([])
const currentSessionId = ref('')
const currentSession = computed(() => sessions.value.find(s => s.id === currentSessionId.value))

// 模型相关
const availableModels = ref<ModelAuth[]>([])
const allowUserSwitchModel = ref(true)
const keepSessionOnSwitch = ref(true)

// 快捷提问
const quickQuestions = [
  '如何退课？',
  '绩点计算规则？',
  '选课冲突怎么办？',
  '奖学金申请条件？'
]

// 管理员配置
const aiConfig = reactive({
  enableStream: true,
  enableVoiceInput: true,
  enableFileUpload: false,
  allowedFileTypes: ['doc', 'pdf', 'image', 'excel'],
  recallTimeLimit: 5 // 分钟
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
      availableModels.value = config.modelAuths.filter((m: ModelAuth) => m.studentAuth && m.isConfigured)
    }
    if (config.functions) {
      allowUserSwitchModel.value = config.functions.allowUserSwitchModel
      keepSessionOnSwitch.value = config.functions.keepSessionOnSwitch
    }
  } else {
    // 默认兜底
    availableModels.value = [{ model: 'tongyi', name: '通义千问', isConfigured: true, studentAuth: true }]
  }

  // 2. 读取会话历史
  const savedSessions = localStorage.getItem('student_ai_sessions')
  if (savedSessions) {
    sessions.value = JSON.parse(savedSessions)
  }
  
  // 如果没有会话，创建默认会话
  if (sessions.value.length === 0) {
    // 预设历史会话
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
      title: '选课咨询',
      timestamp: now,
      unread: false,
      model: 'tongyi',
      messages: [
        { id: '1-1', role: 'user', content: '选课时间是什么时候？', timestamp: now - 100000, operable: true },
        { id: '1-2', role: 'ai', content: '本学期选课时间为 **9月1日 08:00 - 9月5日 18:00**，请登录教务系统及时选课。', timestamp: now - 90000, modelName: '通义千问' }
      ]
    },
    {
      id: '2',
      title: '成绩查询',
      timestamp: now - 86400000,
      unread: true,
      model: 'tongyi',
      messages: [
        { id: '2-1', role: 'user', content: '怎么查上学期的成绩？', timestamp: now - 86500000, operable: true },
        { id: '2-2', role: 'ai', content: '进入“成绩管理”模块，选择“学期成绩”，即可查看历史学期成绩单。', timestamp: now - 86400000, modelName: '通义千问' }
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
      console.error('Speech recognition error', event)
      isRecording.value = false
      ElMessage.error('语音识别失败')
    }
    
    recognition.value.onend = () => {
      isRecording.value = false
    }
  }
}

// 会话持久化
watch(sessions, (newVal) => {
  localStorage.setItem('student_ai_sessions', JSON.stringify(newVal))
}, { deep: true })

// 切换显示
const toggleChat = () => {
  isVisible.value = !isVisible.value
  if (isVisible.value) {
    scrollToBottom()
    // 清除未读
    if (currentSession.value) currentSession.value.unread = false
  }
}

// 新建会话
const createNewSession = () => {
  const now = Date.now()
  const newSession: Session = {
    id: now.toString(),
    title: `未命名会话-${new Date().toLocaleDateString()}`,
    messages: [{
      id: 'welcome',
      role: 'ai',
      content: '同学你好！我是你的智能教务助手，有什么可以帮你的吗？',
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

// 删除会话
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

// 清除所有会话
const clearAllSessions = () => {
  ElMessageBox.confirm('确定要清空所有会话记录吗？此操作不可恢复。', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    sessions.value = []
    createNewSession()
    ElMessage.success('已清空所有会话')
  })
}

// 重命名会话
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

// 切换会话
const switchSession = (id: string) => {
  currentSessionId.value = id
  if (currentSession.value) currentSession.value.unread = false
  scrollToBottom()
}

// 切换模型
const handleModelSwitch = (modelKey: string) => {
  if (!currentSession.value || currentSession.value.model === modelKey) return
  
  const targetModelName = availableModels.value.find(m => m.model === modelKey)?.name || modelKey
  
  if (!keepSessionOnSwitch.value) {
    // 清空当前会话消息
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

// 发送消息
const handleSend = async (content: string = inputContent.value) => {
  if (!content.trim() || !currentSession.value) return

  // 1. 添加用户消息
  const userMsg: ChatMessage = {
    id: Date.now().toString(),
    role: 'user',
    content: content,
    timestamp: Date.now(),
    operable: true
  }
  currentSession.value.messages.push(userMsg)
  
  // 自动生成标题 (如果是第一条用户消息)
  if (currentSession.value.messages.length <= 2 && currentSession.value.title.startsWith('未命名')) {
    currentSession.value.title = content.substring(0, 10) + (content.length > 10 ? '...' : '')
  }
  currentSession.value.timestamp = Date.now()

  inputContent.value = ''
  scrollToBottom()
  loading.value = true

  // 2. 模拟 AI 响应
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

  // 模拟响应内容
  let fullResponse = ''
  
  // 简单的关键词匹配逻辑
  if (content.includes('退课')) {
    fullResponse = `### 退课流程说明\n\n1. 登录教务系统\n2. 进入 **选课管理** -> **我的课程**\n3. 找到对应课程，点击“退课”按钮\n\n> 注意：退课需在开学后两周内完成，逾期将无法退课。`
  } else if (content.includes('绩点')) {
    fullResponse = `### 绩点计算规则\n\n平均学分绩点 (GPA) 计算公式：\n\n$$ GPA = \\frac{\\sum(课程绩点 \\times 学分)}{\\sum 学分} $$\n\n**绩点对照表**：\n| 分数 | 绩点 |\n|---|---|\n| 90-100 | 4.0 |\n| 85-89 | 3.7 |\n| 82-84 | 3.3 |`
  } else if (content.includes('代码') || content.includes('python')) {
    fullResponse = `好的，这是一个 Python 成绩统计的示例代码：\n\n\`\`\`python\ndef calculate_average(scores):\n    if not scores:\n        return 0\n    return sum(scores) / len(scores)\n\nscores = [85, 92, 78, 90]\nprint(f"平均分: {calculate_average(scores)}")\n\`\`\``
  } else {
    fullResponse = `(由 ${modelName} 生成) 收到您的问题：“${content}”。\n正在为您查询相关教务规定...`
  }

  // 流式模拟
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

// 语音输入
const toggleRecording = () => {
  if (!recognition.value) {
    ElMessage.warning('当前浏览器不支持语音输入，请使用 Chrome')
    // 模拟演示
    setTimeout(() => {
      inputContent.value += '请问期末成绩什么时候发布？'
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

// 文件上传
const handleFileUpload = () => {
  ElMessage.success('模拟文件上传成功：question.docx')
  inputContent.value += '[已上传文件: question.docx] '
}

// 消息操作
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
  // 找到该 AI 消息的前一条用户消息
  if (!currentSession.value) return
  const index = currentSession.value.messages.findIndex(m => m.id === msg.id)
  if (index > 0) {
    const lastUserMsg = currentSession.value.messages[index - 1]
    if (lastUserMsg.role === 'user') {
      // 删除旧的 AI 消息
      currentSession.value.messages.splice(index, 1)
      // 重新发送
      handleSend(lastUserMsg.content)
    }
  }
}

// 辅助函数
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

const useQuickQuestion = (text: string) => {
  handleSend(text)
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
            <span class="app-name">AI 助手</span>
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
            <!-- 快捷提问 -->
            <div class="quick-tags">
              <el-tag 
                v-for="q in quickQuestions" 
                :key="q" 
                class="quick-tag" 
                effect="plain" 
                round
                @click="useQuickQuestion(q)"
              >
                {{ q }}
              </el-tag>
            </div>

            <div class="input-box">
              <div class="input-tools">
                <el-tooltip content="语音输入" placement="top">
                  <el-icon class="tool-icon" :class="{ recording: isRecording }" @click="toggleRecording"><Microphone /></el-icon>
                </el-tooltip>
                <el-tooltip content="上传文件" placement="top">
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
  color: #409EFF;
  text-decoration: none;
}

/* 悬浮按钮 */
.float-trigger {
  position: fixed;
  right: 30px;
  bottom: 30px;
  width: 60px;
  height: 60px;
  background: #409EFF;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
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
  background: #E6F7FF;
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
.edit-icon:hover { color: #409EFF; }

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
.model-select:hover { color: #409EFF; }
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
.ai .avatar { background: #fff; color: #409EFF; border: 1px solid #e0e0e0; }
.user-avatar { background: #409EFF; color: #fff; font-size: 12px; }

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
  background: #409EFF; 
  color: #fff;
  border-top-right-radius: 2px;
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
.action-btn:hover { color: #409EFF; }

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

.quick-tags {
  margin-bottom: 12px;
  display: flex;
  gap: 8px;
}
.quick-tag {
  cursor: pointer;
}
.quick-tag:hover {
  color: #409EFF;
  border-color: #409EFF;
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
  border-color: #409EFF;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.1);
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
.tool-icon:hover { color: #409EFF; }
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
}

@keyframes pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); }
}
</style>
