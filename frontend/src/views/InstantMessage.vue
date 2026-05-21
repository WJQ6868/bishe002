<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { 
  Search, Plus, Delete, Picture, ChatDotRound,
  Promotion, MoreFilled, Warning
} from '@element-plus/icons-vue'
import { io, Socket } from 'socket.io-client'
import axios from 'axios'
import FriendManagement from '../components/FriendManagement.vue'

interface Message {
  id: number
  from_id: number
  to_id: number
  content: string
  type: string
  send_time: string
  is_read: boolean | number
}

type UserStatus = 'online' | 'offline' | 'away'

interface Contact {
  user_id: number
  name: string
  role: 'student' | 'teacher' | 'admin'
  username: string
  status: UserStatus
  last_message?: string | null
  last_time?: string | null
  unread: number
}

const searchKeyword = ref('')
const contacts = ref<Contact[]>([])
const currentContact = ref<Contact | null>(null)
const messages = ref<Message[]>([])
const inputMessage = ref('')
const isConnected = ref(false)
const messageContainerRef = ref<HTMLElement>()
const loadingHistory = ref(false)

// 好友管理
const showFriendDialog = ref(false)
const friendManagementRef = ref<InstanceType<typeof FriendManagement>>()
const pendingFriendRequests = ref(0)

const currentUser = reactive({
  id: Number(localStorage.getItem('user_id') || '0'),
  name: localStorage.getItem('user_name') || '?????',
  role: (localStorage.getItem('user_role') || 'student') as 'student' | 'teacher' | 'admin'
})

let socket: Socket | null = null

onMounted(() => {
  initSocketIO()
  loadContacts()
  loadUnread()
})

onUnmounted(() => {
  socket?.disconnect()
})

const initSocketIO = () => {
  socket = io(window.location.origin, {
    path: '/socket.io',
    transports: ['websocket', 'polling']
  })

  socket.on('connect', () => {
    isConnected.value = true
    socket?.emit('user_login', {
      user_id: currentUser.id,
      role: currentUser.role
    })
  })

  socket.on('disconnect', () => {
    isConnected.value = false
  })

  socket.on('new_message', (msg: Message) => {
    if (currentContact.value && msg.from_id === currentContact.value.user_id) {
      messages.value.push(msg)
      scrollToBottom()
      markConversationRead(currentContact.value.user_id)
    } else {
      incrementUnread(msg.from_id)
    }
    updateContactPreview(msg)
  })

  socket.on('message_sent', (msg: Message) => {
    updateContactPreview(msg)
  })

  socket.on('user_status_change', (data: { user_id: number, status: UserStatus }) => {
    const contact = contacts.value.find((c) => c.user_id === data.user_id)
    if (contact) {
      contact.status = data.status
    }
  })

  socket.on('online_users', (payload: { users: number[] }) => {
    contacts.value.forEach((c) => {
      c.status = payload.users.includes(c.user_id) ? 'online' : 'offline'
    })
  })
  
  // 好友相关事件监听
  socket.on('friend_request_received', (data: any) => {
    ElNotification({
      title: '新好友申请',
      message: `${data.from_user_name} 请求添加您为好友`,
      type: 'info',
      duration: 5000
    })
    pendingFriendRequests.value++
    friendManagementRef.value?.loadPendingCount()
  })
  
  socket.on('friend_request_processed', (data: any) => {
    if (data.status === 'accepted') {
      ElNotification({
        title: '好友申请已通过',
        message: `${data.user_name} 接受了您的好友申请`,
        type: 'success'
      })
    }
  })
  
  socket.on('friend_added', () => {
    // 刷新联系人列表
    loadContacts()
  })
  
  socket.on('friend_deleted', (data: any) => {
    // 刷新联系人列表
    loadContacts()
    // 如果正在和被删除的好友聊天，清空消息
    if (currentContact.value && currentContact.value.user_id === data.user_id) {
      currentContact.value = null
      messages.value = []
    }
  })
}

const loadContacts = async () => {
  try {
    const res = await axios.get('/chat/contacts')
    contacts.value = (res.data?.data?.contacts || []).map((item: any) => ({
      user_id: item.user_id,
      name: item.name,
      username: item.username,
      role: item.role,
      status: 'offline',
      last_message: item.last_message,
      last_time: item.last_time,
      unread: item.unread || 0,
    }))
    if (!currentContact.value && contacts.value.length) {
      selectContact(contacts.value[0])
    }
  } catch (err) {
    ElMessage.error('加载联系人列表失败')
  }
}

const loadUnread = async () => {
  try {
    const res = await axios.get('/chat/unread')
    const details = res.data?.data?.details || {}
    contacts.value.forEach((contact) => {
      contact.unread = details[contact.user_id] || 0
    })
  } catch {
    // ignore
  }
}

const loadMessages = async () => {
  if (!currentContact.value) return
  loadingHistory.value = true
  try {
    const res = await axios.get('/chat/history', {
      params: { to_id: currentContact.value.user_id, page: 1, size: 100 }
    })
    messages.value = res.data?.data?.list || []
    await nextTick()
    scrollToBottom()
    await markConversationRead(currentContact.value.user_id)
  } catch (err) {
    ElMessage.error('加载聊天记录失败')
  } finally {
    loadingHistory.value = false
  }
}

const markConversationRead = async (targetId: number) => {
  try {
    await axios.post('/chat/read', {
      user_id: currentUser.id,
      target_id: targetId,
    })
    const contact = contacts.value.find((c) => c.user_id === targetId)
    if (contact) contact.unread = 0
  } catch {
    // ignore
  }
}

const selectContact = async (contact: Contact) => {
  currentContact.value = contact
  contact.unread = 0
  await loadMessages()
}

const incrementUnread = (userId: number) => {
  const contact = contacts.value.find((c) => c.user_id === userId)
  if (contact) {
    contact.unread += 1
  }
}

const updateContactPreview = (msg: Message) => {
  const contactId = msg.from_id === currentUser.id ? msg.to_id : msg.from_id
  const contact = contacts.value.find((c) => c.user_id === contactId)
  if (contact) {
    contact.last_message = msg.content
    contact.last_time = msg.send_time
    const idx = contacts.value.indexOf(contact)
    if (idx > 0) {
      contacts.value.splice(idx, 1)
      contacts.value.unshift(contact)
    }
  }
}

const sendMessage = () => {
  if (!inputMessage.value.trim() || !currentContact.value) return
  if (!socket || !isConnected.value) {
    ElMessage.error('连接未建立，无法发送消息')
    return
  }

  const payload: Message = {
    id: Date.now(),
    from_id: currentUser.id,
    to_id: currentContact.value.user_id,
    content: inputMessage.value,
    type: 'text',
    send_time: new Date().toISOString(),
    is_read: false,
  }

  messages.value.push(payload)
  scrollToBottom()
  socket.emit('send_message', {
    to_id: currentContact.value.user_id,
    content: inputMessage.value,
    type: 'text',
  })
  inputMessage.value = ''
  updateContactPreview(payload)
}

const clearHistory = () => {
  if (!currentContact.value) return
  ElMessageBox.confirm('确定要清空聊天记录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    messages.value = []
  })
}

const handleImageUpload = () => {
  ElMessage.info('图片上传功能开发中...')
}

// 表情选择器状态
const showEmojiPicker = ref(false)
const commonEmojis = [
  '😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂',
  '🙂', '😊', '😇', '🥰', '😍', '🤩', '😘', '😗',
  '😚', '😙', '😋', '😛', '😜', '🤪', '😝', '🤑',
  '🤗', '🤭', '🤫', '🤔', '🤐', '🤨', '😐', '😑',
  '😶', '😏', '😒', '🙄', '😬', '🤥', '😌', '😔',
  '😪', '🤤', '😴', '😷', '🤒', '🤕', '🤢', '🤮',
  '🤧', '🥵', '🥶', '😵', '🤯', '🤠', '🥳', '😎',
  '🤓', '🧐', '😕', '😟', '🙁', '😮', '😯', '😲',
  '😳', '🥺', '😦', '😧', '😨', '😰', '😥', '😢',
  '😭', '😱', '😖', '😣', '😞', '😓', '😩', '😫',
  '🥱', '😤', '😡', '😠', '🤬', '👍', '👎', '👏',
  '🙌', '👋', '🤝', '🙏', '💪', '❤️', '💔', '⭐',
  '✨', '💯', '🔥', '👀', '💀', '🎉', '🎊', '🎁'
]

const handleEmoji = () => {
  showEmojiPicker.value = !showEmojiPicker.value
}

const insertEmoji = (emoji: string) => {
  inputMessage.value += emoji
  showEmojiPicker.value = false
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messageContainerRef.value) {
      messageContainerRef.value.scrollTop = messageContainerRef.value.scrollHeight
    }
  })
}

const formatMessageTime = (isoString: string) => {
  return new Date(isoString).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatTime = (isoString?: string | null) => {
  if (!isoString) return ''
  const date = new Date(isoString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  if (diff < 86400000) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } else if (diff < 172800000) {
    return '昨天'
  }
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

const getStatusColor = (status: UserStatus) => {
  switch (status) {
    case 'online': return '#52C41A'
    case 'away': return '#FAAD14'
    default: return '#D9D9D9'
  }
}

const getStatusText = (status: UserStatus) => {
  switch (status) {
    case 'online': return '在线'
    case 'away': return '离开'
    default: return '离线'
  }
}

const filteredContacts = computed(() => {
  if (!searchKeyword.value) return contacts.value
  return contacts.value.filter((c) => c.name.includes(searchKeyword.value) || c.username.includes(searchKeyword.value))
})

// 打开好友管理
const openFriendManagement = () => {
  showFriendDialog.value = true
}

// 刷新联系人列表（从好友管理调用）
const handleRefreshContacts = () => {
  loadContacts()
}
</script>


<template>
  <div class="im-page">
    <div class="im-container">
      <!-- 左侧联系人列表 -->
      <div class="contacts-panel">
      <div class="panel-header">
        <el-badge :value="pendingFriendRequests" :hidden="pendingFriendRequests === 0" :max="99">
          <h3>消息</h3>
        </el-badge>
        <el-button type="primary" :icon="Plus" circle size="small" @click="openFriendManagement" title="好友管理" />
      </div>
      
      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-input 
          v-model="searchKeyword" 
          placeholder="搜索联系人" 
          :prefix-icon="Search"
          clearable
        />
      </div>
      
      <!-- 联系人列表 -->
      <div class="contacts-list">
        <div 
          v-for="contact in filteredContacts" 
          :key="contact.user_id"
          class="contact-item"
          :class="{ active: currentContact?.user_id === contact.user_id }"
          @click="selectContact(contact)"
        >
          <!-- 头像 -->
          <div class="avatar-wrapper">
            <div class="avatar" :class="contact.role">
              {{ contact.name.charAt(0) }}
            </div>
            <span class="status-dot" :style="{ backgroundColor: getStatusColor(contact.status) }"></span>
          </div>
          
          <!-- 信息 -->
          <div class="contact-info">
            <div class="contact-header">
              <span class="name">{{ contact.name }}</span>
              <span class="time">{{ formatTime(contact.last_time) }}</span>
            </div>
            <div class="last-message">
              {{ contact.last_message || '暂无消息' }}
            </div>
          </div>
          
          <!-- 未读数 -->
          <div class="unread-badge" v-if="contact.unread > 0">
            {{ contact.unread > 99 ? '99+' : contact.unread }}
          </div>
        </div>
        
        <div v-if="filteredContacts.length === 0" class="empty-contacts">
          暂无联系人
        </div>
      </div>
    </div>
    
    <!-- 右侧聊天区 -->
    <div class="chat-panel" v-if="currentContact">
      <!-- 聊天头部 -->
      <div class="chat-header">
        <div class="contact-profile">
          <div class="avatar" :class="currentContact.role">
            {{ currentContact.name.charAt(0) }}
          </div>
          <div class="profile-info">
            <span class="name">{{ currentContact.name }}</span>
            <span class="status" :style="{ color: getStatusColor(currentContact.status) }">
              {{ getStatusText(currentContact.status) }}
            </span>
          </div>
        </div>
        
        <div class="header-actions">
          <el-dropdown trigger="click">
            <el-button :icon="MoreFilled" circle />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item :icon="Delete" @click="clearHistory">清空记录</el-dropdown-item>
                <el-dropdown-item :icon="Warning">举报</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
      
      <!-- 消息区域 -->
      <div class="messages-area" ref="messageContainerRef">
        <div 
          v-for="msg in messages" 
          :key="msg.id"
          class="message-item"
          :class="{ 'is-self': msg.from_id === currentUser.id }"
        >
          <!-- 时间标记 (简化处理) -->
          
          <!-- 消息气泡 -->
          <div class="message-bubble">
            <div class="bubble-content">
              {{ msg.content }}
            </div>
            <div class="message-meta">
              <span class="time">{{ formatMessageTime(msg.send_time) }}</span>
              <span v-if="msg.from_id === currentUser.id" class="read-status">
                {{ msg.is_read ? '已读' : '未读' }}
              </span>
            </div>
          </div>
        </div>
        
        <div v-if="messages.length === 0" class="empty-messages">
          <el-icon :size="48" color="#C0C4CC"><ChatDotRound /></el-icon>
          <p>暂无消息，开始聊天吧~</p>
        </div>
      </div>
      
      <!-- 输入区域 -->
      <div class="input-area">
        <div class="input-tools">
          <el-button :icon="Picture" circle @click="handleImageUpload" />
          <div class="emoji-picker-wrapper">
            <el-button circle @click="handleEmoji">😊</el-button>
            
            <!-- 表情选择器弹出框 -->
            <div v-if="showEmojiPicker" class="emoji-picker">
              <div class="emoji-picker-header">
                <span>选择表情</span>
                <el-button text @click="showEmojiPicker = false" size="small">✕</el-button>
              </div>
              <div class="emoji-grid">
                <div 
                  v-for="emoji in commonEmojis" 
                  :key="emoji"
                  class="emoji-item"
                  @click="insertEmoji(emoji)"
                >
                  {{ emoji }}
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="input-box">
          <el-input 
            v-model="inputMessage"
            type="textarea"
            :rows="3"
            placeholder="输入消息..."
            resize="none"
            @keydown.enter.prevent="sendMessage"
          />
        </div>
        
        <div class="send-btn">
          <el-button 
            type="primary" 
            :icon="Promotion" 
            :disabled="!inputMessage.trim()"
            @click="sendMessage"
          >
            发送
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- 未选择联系人时的占位 -->
    <div class="chat-panel empty-state" v-else>
      <el-icon :size="64" color="#C0C4CC"><ChatDotRound /></el-icon>
      <p>选择一个联系人开始聊天</p>
      <p class="connection-status" :class="{ connected: isConnected }">
        {{ isConnected ? '● 已连接' : '○ 未连接' }}
      </p>
    </div>
    
    <!-- 好友管理对话框 -->
    <FriendManagement
      ref="friendManagementRef"
      v-model:visible="showFriendDialog"
      @refresh-contacts="handleRefreshContacts"
    />
    </div>
  </div>
</template>

<style scoped>
.im-page {
  background: var(--app-bg, #0b0f18);
  min-height: calc(100vh - 90px);
  padding: 12px;
}

.im-container {
  display: flex;
  height: calc(100vh - 120px);
  background: rgba(17, 24, 39, 0.85);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.35);
  border: 1px solid var(--border-color, #1f2a3d);
}

/* 左侧联系人列表 */
.contacts-panel {
  width: 300px;
  border-right: 1px solid rgba(255,255,255,0.06);
  display: flex;
  flex-direction: column;
  background: rgba(12, 17, 28, 0.9);
}

.panel-header {
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

.panel-header h3 {
  margin: 0;
  font-size: 18px;
  color: #e8f5ff;
}

.search-bar {
  padding: 12px;
}

.contacts-list {
  flex: 1;
  overflow-y: auto;
}

.contact-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.2s;
  position: relative;
}

.contact-item:hover {
  background: rgba(0, 242, 254, 0.08);
}

.contact-item.active {
  background: rgba(0, 242, 254, 0.15);
}

.avatar-wrapper {
  position: relative;
  margin-right: 12px;
}

.avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 16px;
  font-weight: 500;
}

.avatar.teacher {
  background: linear-gradient(135deg, #52C41A, #73D13D);
}

.avatar.student {
  background: linear-gradient(135deg, #409EFF, #66B1FF);
}

.status-dot {
  position: absolute;
  bottom: 2px;
  right: 2px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid #fff;
}

.contact-info {
  flex: 1;
  min-width: 0;
}

.contact-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.contact-header .name {
  font-size: 14px;
  font-weight: 500;
  color: #e6f0ff;
}

.contact-header .time {
  font-size: 12px;
  color: rgba(255,255,255,0.45);
}

.last-message {
  font-size: 13px;
  color: rgba(255,255,255,0.6);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.unread-badge {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  background: #F56C6C;
  color: #fff;
  font-size: 11px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-contacts {
  text-align: center;
  padding: 40px;
  color: rgba(255,255,255,0.5);
}

/* 右侧聊天区 */
.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: rgba(17, 24, 39, 0.8);
}

.chat-panel.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: rgba(255,255,255,0.5);
}

.chat-panel.empty-state p {
  margin: 12px 0 0;
}

.connection-status {
  font-size: 12px;
  color: #909399;
}

.connection-status.connected {
  color: #52C41A;
}

/* 聊天头部 */
.chat-header {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: transparent;
}

.contact-profile {
  display: flex;
  align-items: center;
}

.contact-profile .avatar {
  width: 40px;
  height: 40px;
  margin-right: 12px;
}

.profile-info {
  display: flex;
  flex-direction: column;
}

.profile-info .name {
  font-size: 16px;
  font-weight: 500;
  color: #e8f5ff;
}

.profile-info .status {
  font-size: 12px;
}

/* 消息区域 */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: transparent;
}

.message-item {
  display: flex;
  margin-bottom: 16px;
}

.message-item.is-self {
  flex-direction: row-reverse;
}

.message-bubble {
  max-width: 60%;
}

.bubble-content {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
}

.message-item:not(.is-self) .bubble-content {
  background: rgba(255,255,255,0.08);
  color: #e6f0ff;
  border-top-left-radius: 2px;
}

.message-item.is-self .bubble-content {
  background: linear-gradient(135deg, #00f2fe, #0066ff);
  color: #fff;
  border-top-right-radius: 2px;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  font-size: 11px;
  color: rgba(255,255,255,0.55);
}

.message-item.is-self .message-meta {
  justify-content: flex-end;
}

.empty-messages {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
}

.empty-messages p {
  margin-top: 12px;
}

/* 输入区域 */
.input-area {
  padding: 12px 16px;
  border-top: 1px solid rgba(255,255,255,0.06);
  background: rgba(0,0,0,0.25);
}

.input-tools {
  margin-bottom: 8px;
}

.input-box {
  margin-bottom: 8px;
}

.send-btn {
  text-align: right;
}

/* 表情选择器样式 */
.emoji-picker-wrapper {
  position: relative;
  display: inline-block;
}

.emoji-picker {
  position: absolute;
  bottom: 45px;
  left: 0;
  width: 320px;
  max-height: 280px;
  background: #0f172a;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  overflow: hidden;
}

.emoji-picker-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.06);
  font-size: 14px;
  font-weight: 500;
}

.emoji-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 4px;
  padding: 8px;
  max-height: 220px;
  overflow-y: auto;
}

.emoji-item {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}

.emoji-item:hover {
  background: rgba(0, 242, 254, 0.08);
  transform: scale(1.2);
}
</style>
