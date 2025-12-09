<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Search, Plus, Delete, Picture, ChatDotRound,
  CirclePlus, Promotion, MoreFilled, Warning
} from '@element-plus/icons-vue'
import { io, Socket } from 'socket.io-client'
import axios from 'axios'

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
  const host = window.location.hostname
  socket = io(`http://${host}:8000`, {
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
}

const loadContacts = async () => {
  try {
    const res = await axios.get('/api/chat/contacts')
    contacts.value = (res.data?.contacts || []).map((item: any) => ({
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
    ElMessage.error('???????')
  }
}

const loadUnread = async () => {
  try {
    const res = await axios.get('/api/chat/unread')
    const details = res.data?.details || {}
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
    const res = await axios.get('/api/chat/history', {
      params: { to_id: currentContact.value.user_id, page: 1, size: 100 }
    })
    messages.value = res.data?.list || []
    await nextTick()
    scrollToBottom()
    await markConversationRead(currentContact.value.user_id)
  } catch (err) {
    ElMessage.error('????????')
  } finally {
    loadingHistory.value = false
  }
}

const markConversationRead = async (targetId: number) => {
  try {
    await axios.post('/api/chat/read', {
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
    ElMessage.error('??????????')
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
  ElMessageBox.confirm('?????????????????', '??', {
    confirmButtonText: '??',
    cancelButtonText: '??',
    type: 'warning'
  }).then(() => {
    messages.value = []
  })
}

const handleImageUpload = () => {
  ElMessage.info('?????????...')
}

const handleEmoji = () => {
  ElMessage.info('???????...')
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
    return '??'
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
    case 'online': return '??'
    case 'away': return '??'
    default: return '??'
  }
}

const filteredContacts = computed(() => {
  if (!searchKeyword.value) return contacts.value
  return contacts.value.filter((c) => c.name.includes(searchKeyword.value) || c.username.includes(searchKeyword.value))
})
</script>


<template>
  <div class="im-container">
    <!-- 左侧联系人列表 -->
    <div class="contacts-panel">
      <div class="panel-header">
        <h3>消息</h3>
        <el-button type="primary" :icon="Plus" circle size="small" />
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
          <div class="unread-badge" v-if="contact.unread_count > 0">
            {{ contact.unread_count > 99 ? '99+' : contact.unread_count }}
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
          <el-button circle @click="handleEmoji">😊</el-button>
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
  </div>
</template>

<style scoped>
.im-container {
  display: flex;
  height: calc(100vh - 120px);
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

/* 左侧联系人列表 */
.contacts-panel {
  width: 300px;
  border-right: 1px solid #E4E7ED;
  display: flex;
  flex-direction: column;
  background: #FAFAFA;
}

.panel-header {
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #E4E7ED;
}

.panel-header h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
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
  background: #F5F7FA;
}

.contact-item.active {
  background: #E6F7FF;
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
  color: #303133;
}

.contact-header .time {
  font-size: 12px;
  color: #909399;
}

.last-message {
  font-size: 13px;
  color: #909399;
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
  color: #909399;
}

/* 右侧聊天区 */
.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chat-panel.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
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
  border-bottom: 1px solid #E4E7ED;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
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
  color: #303133;
}

.profile-info .status {
  font-size: 12px;
}

/* 消息区域 */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #F5F7FA;
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
  background: #fff;
  color: #303133;
  border-top-left-radius: 2px;
}

.message-item.is-self .bubble-content {
  background: #409EFF;
  color: #fff;
  border-top-right-radius: 2px;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  font-size: 11px;
  color: #909399;
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
  border-top: 1px solid #E4E7ED;
  background: #fff;
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
</style>
