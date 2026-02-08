<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  ChatRound, Plus, Delete, Edit, MoreFilled, 
  Microphone, FolderAdd, Picture,
  RefreshRight, Close, ChatDotRound
} from '@element-plus/icons-vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import { streamQA } from '@/api/ai'
import { aiPortalApi, type CustomerServiceConfig } from '@/api/aiPortal'

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
}

// --- 2. 状态管理 ---
const isVisible = ref(false)
const inputContent = ref('')
const loading = ref(false)
const chatContainerRef = ref<HTMLElement>()
const isRecording = ref(false)
const recognition = ref<any>(null)
const chatModalRef = ref<HTMLElement>()
const floatTriggerRef = ref<HTMLElement>()

const sidebarHidden = ref(true)
const isDragging = ref(false)
const hasInitPos = ref(false)
const dragOffset = reactive({ x: 0, y: 0 })
const modalPos = reactive({ x: 0, y: 0 })
const modalStyle = computed(() => {
  if (!hasInitPos.value) {
    return { left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }
  }
  return { left: `${modalPos.x}px`, top: `${modalPos.y}px`, transform: 'none' }
})

const floatDragging = ref(false)
const floatMoved = ref(false)
const floatOffset = reactive({ x: 0, y: 0 })
const floatPos = reactive({ x: 0, y: 0 })
const hasFloatPos = ref(false)
const floatStyle = computed(() => {
  if (!hasFloatPos.value) return {}
  return { left: `${floatPos.x}px`, top: `${floatPos.y}px`, right: 'auto', bottom: 'auto' }
})

// 会话管理
const sessions = ref<Session[]>([])
const currentSessionId = ref('')
const currentSession = computed(() => sessions.value.find(s => s.id === currentSessionId.value))

const appTitle = 'AI客服'

const defaultCustomerConfig: CustomerServiceConfig = {
  welcome_str: '你好，我是AI客服，可以帮你解答校园常见问题。',
  recommend_questions: ['如何请假？', '如何选课？', '成绩在哪里查询？'],
  search_placeholder: '请输入问题，例如：如何请假？'
}

const customerConfig = reactive({
  welcome_str: defaultCustomerConfig.welcome_str,
  recommend_questions: [...defaultCustomerConfig.recommend_questions],
  search_placeholder: defaultCustomerConfig.search_placeholder
})

const customerWorkflow = ref('')

// 快捷提问
const quickQuestions = ref<string[]>([...defaultCustomerConfig.recommend_questions])
const inputPlaceholder = computed(() => customerConfig.search_placeholder || defaultCustomerConfig.search_placeholder)

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
  void initData()
  initSpeechRecognition()
})

const loadCustomerService = async () => {
  try {
    const [config, apps] = await Promise.all([
      aiPortalApi.getCustomerServiceConfig(),
      aiPortalApi.listCustomerServiceApps()
    ])
    if (config) {
      customerConfig.welcome_str = config.welcome_str || defaultCustomerConfig.welcome_str
      customerConfig.search_placeholder = config.search_placeholder || defaultCustomerConfig.search_placeholder
      customerConfig.recommend_questions = (config.recommend_questions && config.recommend_questions.length)
        ? config.recommend_questions
        : [...defaultCustomerConfig.recommend_questions]
      quickQuestions.value = [...customerConfig.recommend_questions]
    }
    const enabledApps = (apps || []).filter(a => a.status === 'enabled')
    customerWorkflow.value = enabledApps[0]?.code || 'customer_service'
  } catch (err) {
    console.error(err)
    quickQuestions.value = [...customerConfig.recommend_questions]
    if (!customerWorkflow.value) customerWorkflow.value = 'customer_service'
  }
}

const initData = async () => {
  await loadCustomerService()

  // 读取会话历史
  const savedSessions = localStorage.getItem('student_ai_sessions')
  if (savedSessions) {
    sessions.value = JSON.parse(savedSessions)
  }
  
  // 如果没有会话，创建默认会话
  if (sessions.value.length === 0) {
    createNewSession()
  } else {
    currentSessionId.value = sessions.value[0].id
  }
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
    ensureModalPosition()
  }
}

const ensureModalPosition = () => {
  nextTick(() => {
    const el = chatModalRef.value
    if (!el) return
    const rect = el.getBoundingClientRect()
    const maxX = Math.max(0, window.innerWidth - rect.width)
    const maxY = Math.max(0, window.innerHeight - rect.height)
    if (!hasInitPos.value) {
      modalPos.x = Math.max(0, Math.min((window.innerWidth - rect.width) / 2, maxX))
      modalPos.y = Math.max(0, Math.min((window.innerHeight - rect.height) / 2, maxY))
      hasInitPos.value = true
      return
    }
    modalPos.x = Math.min(Math.max(0, modalPos.x), maxX)
    modalPos.y = Math.min(Math.max(0, modalPos.y), maxY)
  })
}

const startDrag = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  if (target?.closest('.no-drag')) return
  const el = chatModalRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  hasInitPos.value = true
  modalPos.x = rect.left
  modalPos.y = rect.top
  dragOffset.x = event.clientX - rect.left
  dragOffset.y = event.clientY - rect.top
  isDragging.value = true
  document.body.style.userSelect = 'none'
}

const onDrag = (event: MouseEvent) => {
  if (!isDragging.value || !chatModalRef.value) return
  const el = chatModalRef.value
  const width = el.offsetWidth || 0
  const height = el.offsetHeight || 0
  let x = event.clientX - dragOffset.x
  let y = event.clientY - dragOffset.y
  const maxX = Math.max(0, window.innerWidth - width)
  const maxY = Math.max(0, window.innerHeight - height)
  x = Math.min(Math.max(0, x), maxX)
  y = Math.min(Math.max(0, y), maxY)
  modalPos.x = x
  modalPos.y = y
}

const stopDrag = () => {
  if (!isDragging.value) return
  isDragging.value = false
  document.body.style.userSelect = ''
}

const toggleSidebar = () => {
  sidebarHidden.value = !sidebarHidden.value
  ensureModalPosition()
}

const startFloatDrag = (event: MouseEvent) => {
  if (isVisible.value) return
  const el = floatTriggerRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  hasFloatPos.value = true
  floatPos.x = rect.left
  floatPos.y = rect.top
  floatOffset.x = event.clientX - rect.left
  floatOffset.y = event.clientY - rect.top
  floatDragging.value = true
  floatMoved.value = false
  document.body.style.userSelect = 'none'
}

const onFloatDrag = (event: MouseEvent) => {
  if (!floatDragging.value || !floatTriggerRef.value) return
  const el = floatTriggerRef.value
  const width = el.offsetWidth || 0
  const height = el.offsetHeight || 0
  let x = event.clientX - floatOffset.x
  let y = event.clientY - floatOffset.y
  const maxX = Math.max(0, window.innerWidth - width)
  const maxY = Math.max(0, window.innerHeight - height)
  x = Math.min(Math.max(0, x), maxX)
  y = Math.min(Math.max(0, y), maxY)
  const moved = Math.abs(x - floatPos.x) + Math.abs(y - floatPos.y)
  if (moved > 3) floatMoved.value = true
  floatPos.x = x
  floatPos.y = y
}

const stopFloatDrag = () => {
  if (!floatDragging.value) return
  floatDragging.value = false
  document.body.style.userSelect = ''
}

const handleFloatClick = () => {
  if (floatMoved.value) {
    floatMoved.value = false
    return
  }
  toggleChat()
}

onMounted(() => {
  window.addEventListener('mousemove', onDrag)
  window.addEventListener('mouseup', stopDrag)
  window.addEventListener('mousemove', onFloatDrag)
  window.addEventListener('mouseup', stopFloatDrag)
})

onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onDrag)
  window.removeEventListener('mouseup', stopDrag)
  window.removeEventListener('mousemove', onFloatDrag)
  window.removeEventListener('mouseup', stopFloatDrag)
})

// 新建会话
const createNewSession = () => {
  const now = Date.now()
  const newSession: Session = {
    id: now.toString(),
    title: `未命名会话-${new Date().toLocaleDateString()}`,
    messages: [{
      id: 'welcome',
      role: 'ai',
      content: customerConfig.welcome_str || defaultCustomerConfig.welcome_str,
      timestamp: now,
      modelName: '系统'
    }],
    timestamp: now,
    unread: false
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

// 发送消息
const handleSend = async (content: string = inputContent.value) => {
  if (!content.trim() || !currentSession.value) return

  const question = content.trim()

  // 1. ??????
  const userMsg: ChatMessage = {
    id: Date.now().toString(),
    role: 'user',
    content: question,
    timestamp: Date.now(),
    operable: true
  }
  currentSession.value.messages.push(userMsg)
  
  // ?????? (??????????)
  if (currentSession.value.messages.length <= 2 && currentSession.value.title.startsWith('???')) {
    currentSession.value.title = question.substring(0, 10) + (question.length > 10 ? '...' : '')
  }
  currentSession.value.timestamp = Date.now()

  inputContent.value = ''
  scrollToBottom()
  loading.value = true

  const aiMsg: ChatMessage = {
    id: (Date.now() + 1).toString(),
    role: 'ai',
    content: '',
    timestamp: Date.now(),
    isStreaming: true,
    modelName: appTitle
  }
  currentSession.value.messages.push(aiMsg)

  const workflowCode = customerWorkflow.value || 'customer_service'
  if (!workflowCode) {
    aiMsg.content = 'AI???????????????'
    aiMsg.isStreaming = false
    loading.value = false
    return
  }

  try {
    await streamQA(
      localStorage.getItem('user_id') || '0',
      question,
      false,
      (chunk) => {
        aiMsg.content += chunk
        scrollToBottom()
      },
      undefined,
      undefined,
      workflowCode
    )
  } catch (err) {
    console.error(err)
    if (!aiMsg.content) {
      aiMsg.content = 'AI?????????????????'
    }
    ElMessage.error('AI??????????')
  } finally {
    aiMsg.isStreaming = false
    loading.value = false
    scrollToBottom()
  }
}

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

</script>

<template>
  <div class="student-ai-chat">
    <!-- 悬浮触发按钮 -->
    <div
      class="float-trigger"
      ref="floatTriggerRef"
      :style="floatStyle"
      v-if="!isVisible"
      @mousedown="startFloatDrag"
      @click="handleFloatClick"
    >
      <el-icon :size="28"><ChatRound /></el-icon>
      <span class="trigger-text">{{ appTitle }}</span>
    </div>

    <!-- 聊天主窗口 (Modal) -->
    <div class="chat-modal-overlay" v-if="isVisible" @click.self="toggleChat">
      <div class="chat-modal" ref="chatModalRef" :class="{ 'sidebar-hidden': sidebarHidden }" :style="modalStyle">
        
        <!-- 左侧会话列表 -->
        <div class="sidebar" v-if="!sidebarHidden">
          <div class="sidebar-header">
            <span class="app-name">{{ appTitle }}</span>
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
          <div class="chat-header" @mousedown="startDrag">
            <div class="header-left">
              <span class="current-title">{{ currentSession?.title }}</span>
              <el-icon class="edit-icon no-drag" @click="renameSession"><Edit /></el-icon>
            </div>
            
            <div class="header-right no-drag">
              <el-dropdown trigger="click" popper-class="ai-more-dropdown">
                <el-icon class="more-btn"><MoreFilled /></el-icon>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item @click="toggleSidebar">
                      {{ sidebarHidden ? '显示会话列表' : '隐藏会话列表' }}
                    </el-dropdown-item>
                    <el-dropdown-item :icon="Delete" @click="deleteSession(currentSessionId)">删除会话</el-dropdown-item>
                    <el-dropdown-item :icon="RefreshRight" @click="currentSession!.messages = []">清空消息</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              
              <el-icon class="close-btn no-drag" @click="toggleChat"><Close /></el-icon>
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
                :placeholder="inputPlaceholder"
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
  color: #e6e8eb;
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

/* 统一学生端 AI 助手面板底色 */
.student-ai-chat {
  --ai-chat-bg: #2b2f36;
  --ai-chat-sidebar-bg: #24272e;
  --ai-chat-main-bg: #2b2f36;
  --ai-chat-messages-bg: #30343c;
  --ai-chat-input-bg: #262a31;
  --ai-chat-text: #e6e8eb;
  --ai-chat-text-muted: #aeb4be;
  --ai-chat-border: #3a3f46;
  --ai-chat-hover: #343a42;
  --ai-chat-active: #3a4452;
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
  position: fixed;
  background: var(--ai-chat-bg, #f7fbff) !important;
  color: var(--ai-chat-text, #303133) !important;
  border-radius: 12px;
  display: flex;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}
.chat-modal.sidebar-hidden .sidebar {
  display: none;
}
.chat-modal.sidebar-hidden .main-area {
  width: 100%;
}

/* 左侧边栏 */
.sidebar {
  width: 280px;
  background: var(--ai-chat-sidebar-bg, #f1f6ff) !important;
  color: var(--ai-chat-text, #303133) !important;
  border-right: 1px solid var(--ai-chat-border, #3a3f46);
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
  color: var(--ai-chat-text, #e6e8eb);
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
  background: var(--ai-chat-hover, #343a42);
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
.session-card.active {
  background: var(--ai-chat-active, #3a4452);
}
.session-title-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}
.session-title {
  font-size: 14px;
  color: var(--ai-chat-text, #e6e8eb);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 160px;
}
.session-time {
  font-size: 12px;
  color: var(--ai-chat-text-muted, #aeb4be);
}
.session-preview {
  font-size: 12px;
  color: var(--ai-chat-text-muted, #aeb4be);
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
  border-top: 1px solid var(--ai-chat-border, #3a3f46);
  text-align: center;
}

/* 右侧主区 */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--ai-chat-main-bg, #f7fbff) !important;
  color: var(--ai-chat-text, #303133) !important;
}

.chat-header {
  height: 60px;
  border-bottom: 1px solid var(--ai-chat-border, #3a3f46);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  cursor: move;
  user-select: none;
}
.no-drag {
  cursor: default;
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
  color: var(--ai-chat-text-muted, #aeb4be);
  font-size: 14px;
}
.edit-icon:hover { color: #409EFF; }

.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}
.more-btn, .close-btn {
  font-size: 20px;
  cursor: pointer;
  color: var(--ai-chat-text-muted, #aeb4be);
}
.more-btn:hover, .close-btn:hover { color: var(--ai-chat-text, #e6e8eb); }

/* 三点下拉菜单（全局样式，避免被 scoped 限制） */
:global(.ai-more-dropdown.el-popper),
:global(.ai-more-dropdown.el-dropdown__popper) {
  background: #2b2f36 !important;
  border: 1px solid #3a3f46 !important;
  box-shadow: 0 10px 26px rgba(0, 0, 0, 0.35) !important;
}
:global(.ai-more-dropdown .el-dropdown-menu) {
  background: transparent !important;
  border: none !important;
}
:global(.ai-more-dropdown .el-dropdown-menu__item) {
  color: #e6e8eb !important;
}
:global(.ai-more-dropdown .el-dropdown-menu__item:not(.is-disabled):hover) {
  background: #3a4452 !important;
  color: #fff !important;
}
:global(.ai-more-dropdown .el-dropdown-menu__item.is-disabled) {
  color: #7a828e !important;
}
:global(.ai-more-dropdown .el-popper__arrow::before) {
  background: #2b2f36 !important;
  border: 1px solid #3a3f46 !important;
}

/* 消息区 */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: var(--ai-chat-messages-bg, #f9fcff) !important;
  color: var(--ai-chat-text, #303133) !important;
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
  flex-direction: row;
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
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid transparent;
}
.ai .bubble { 
  background: rgba(120, 130, 140, 0.22);
  color: #e6e8eb;
  border-color: rgba(180, 190, 200, 0.35);
  border-bottom-color: rgba(200, 210, 220, 0.7);
  border-top-left-radius: 2px;
}
.user .bubble { 
  background: rgba(64, 158, 255, 0.22);
  color: #e6e8eb;
  border-color: rgba(64, 158, 255, 0.35);
  border-bottom-color: rgba(64, 158, 255, 0.75);
  border-top-right-radius: 2px;
}

.message-footer {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--ai-chat-text-muted, #aeb4be);
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
  color: var(--ai-chat-text-muted, #aeb4be);
  font-size: 13px;
}
.dot {
  display: inline-block;
  width: 4px;
  height: 4px;
  background: var(--ai-chat-text-muted, #aeb4be);
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
  padding: 16px 0 20px;
  background: var(--ai-chat-input-bg, #f7fbff) !important;
  color: var(--ai-chat-text, #303133) !important;
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
  border: 1px solid var(--ai-chat-border, #3a3f46);
  border-radius: 16px;
  padding: 10px 12px;
  display: grid;
  grid-template-columns: 40px 1fr auto;
  align-items: stretch;
  gap: 10px;
  transition: all 0.2s;
  background: #1f2329;
}
.input-box:focus-within {
  border-color: #409EFF;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.1);
}

.input-tools {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: center;
  justify-content: center;
  padding: 4px 0;
}
.tool-icon {
  font-size: 20px;
  color: var(--ai-chat-text-muted, #aeb4be);
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
  height: 84px;
  padding: 6px 0;
  font-size: 14px;
  line-height: 1.5;
  color: var(--ai-chat-text, #e6e8eb);
  background: transparent;
}
.custom-input::placeholder { color: var(--ai-chat-text-muted, #aeb4be); }

.send-btn {
  border-radius: 16px;
  padding: 8px 18px;
  align-self: center;
}

@keyframes pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); }
}
</style>
