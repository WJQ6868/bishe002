<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick, computed, watch } from 'vue'
import { io, Socket } from 'socket.io-client'
import axios from 'axios'
import QRCode from 'qrcode'
import { useTheme } from 'vuetify'

// Types
interface Contact {
  user_id: number
  username: string
  name: string
  role: string
  unread: number
  last_message: string | null
  last_time: string | null
  status: string
}

interface Message {
  id: number
  from_id: number
  from_role: string
  to_id: number
  to_role: string
  content: string
  type: string
  send_time: string
  is_read: number
}

const theme = useTheme()
const message = ref('')
const messages = ref<Message[]>([])
const contacts = ref<Contact[]>([])
const currentUser = reactive({
  id: 0,
  username: '',
  role: ''
})
const selectedContact = ref<Contact | null>(null)
const socket = ref<Socket | null>(null)
const showEmoji = ref(false)
const messageListRef = ref<HTMLElement | null>(null)
const isConnected = ref(false)
const loading = ref(false)
const loadingHistory = ref(false)

// Snackbar
const snackbar = reactive({
  show: false,
  text: '',
  color: 'error'
})

const showSnackbar = (text: string, color: 'success' | 'error' | 'warning' = 'error') => {
  snackbar.text = text
  snackbar.color = color
  snackbar.show = true
}

// Mobile QR Code
const showQRCode = ref(false)
const qrCodeUrl = ref('')

const emojis = ['😀', '😃', '😄', '😁', '😆', '😅', '😂', '🤣', '😊', '😇', '🙂', '🙃', '😉', '😌', '😍', '🥰', '😘', '😗', '😙', '😚', '😋', '😛', '😝', '😜', '🤪', '🤨', '🧐', '🤓', '😎', '🤩', '🥳', '😏', '😒', '😞', '😔', '😟', '😕', '🙁', '☹️', '😣', '😖', '😫', '😩', '🥺', '😢', '😭', '😤', '😠', '😡', '🤬', '🤯', '😳', '🥵', '🥶', '😱', '😨', '😰', '😥', '😓', '🤗', '🤔', '🤭', '🤫', '🤥', '😶', '😐', '😑', '😬', '🙄', '😯', '😦', '😧', '😮', '😲', '🥱', '😴', '🤤', '😪', '😵', '🤐', '🥴', '🤢', '🤮', '🤧', '😷', '🤒', '🤕']

// API Configuration
const api = axios.create({
  baseURL: '/api', // Vite proxy should handle this
  timeout: 5000
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  res => res,
  error => {
    console.error('API Error:', error)
    if (error.response?.status === 401) {
      showSnackbar('认证失效，请重新登录', 'error')
      // Redirect to login logic here
    }
    return Promise.reject(error)
  }
)

// Methods
const initUser = () => {
  const userStr = localStorage.getItem('user')
  if (userStr) {
    const user = JSON.parse(userStr)
    currentUser.id = user.id
    currentUser.username = user.username
    currentUser.role = user.role
  } else {
    // Fallback or decode token if user info not in local storage
    // For now assume localStorage has it
  }
}

const initSocketIO = () => {
  const host = window.location.hostname
  // Assuming backend is on port 8000, but better to use relative path if proxy
  // For socket.io usually we need explicit URL if port differs
  socket.value = io(`http://${host}:8000`, {
    transports: ['websocket', 'polling'],
    auth: {
      token: localStorage.getItem('token')
    }
  })

  socket.value.on('connect', () => {
    isConnected.value = true
    updateStatus('online')
  })

  socket.value.on('disconnect', () => {
    isConnected.value = false
  })

  socket.value.on('new_message', (msg: Message) => {
    if (selectedContact.value && 
        (msg.from_id === selectedContact.value.user_id || msg.from_id === currentUser.id)) {
      messages.value.push(msg)
      scrollToBottom()
      if (msg.from_id === selectedContact.value.user_id) {
        markAsRead(selectedContact.value.user_id)
      }
    } else {
      // Update unread count for contact
      const contact = contacts.value.find(c => c.user_id === msg.from_id)
      if (contact) {
        contact.unread += 1
        contact.last_message = msg.content
        contact.last_time = msg.send_time
        // Re-sort
        sortContacts()
      } else {
        fetchContacts() // Reload if new contact
      }
    }
  })

  socket.value.on('user_status_change', (data: { user_id: number, status: string }) => {
    const contact = contacts.value.find(c => c.user_id === data.user_id)
    if (contact) {
      contact.status = data.status
    }
  })
}

const fetchContacts = async () => {
  loading.value = true
  try {
    const res = await api.get('/chat/contacts')
    if (res.data.code === 200) {
      contacts.value = res.data.data.contacts
    }
  } catch (err) {
    showSnackbar('获取联系人失败', 'error')
  } finally {
    loading.value = false
  }
}

const fetchHistory = async (userId: number) => {
  loadingHistory.value = true
  try {
    const res = await api.get('/chat/history', {
      params: { to_id: userId, page: 1, size: 50 } // Fetch last 50 messages
    })
    if (res.data.code === 200) {
      // Reverse to show oldest first (top) to newest (bottom)
      messages.value = res.data.data.list.reverse()
      scrollToBottom()
    }
  } catch (err) {
    showSnackbar('获取聊天记录失败', 'error')
  } finally {
    loadingHistory.value = false
  }
}

const selectContact = async (contact: Contact) => {
  selectedContact.value = contact
  contact.unread = 0 // Optimistic clear
  await fetchHistory(contact.user_id)
  await markAsRead(contact.user_id)
}

const sendMessage = async () => {
  if (!message.value.trim() || !selectedContact.value) return

  const content = message.value
  message.value = '' // Clear immediately

  try {
    const res = await api.post('/chat/send', {
      from_id: currentUser.id,
      to_id: selectedContact.value.user_id,
      content: content,
      type: 'text'
    })
    
    if (res.data.code === 200) {
      const sentMsg = res.data.data
      messages.value.push(sentMsg)
      scrollToBottom()
      
      // Update last message in list
      selectedContact.value.last_message = sentMsg.content
      selectedContact.value.last_time = sentMsg.send_time
      sortContacts()
    }
  } catch (err) {
    showSnackbar('发送失败', 'error')
    message.value = content // Restore on fail
  }
}

const markAsRead = async (targetId: number) => {
  try {
    await api.post('/chat/read', {
      user_id: currentUser.id,
      target_id: targetId
    })
    // Update local state if needed
  } catch (err) {
    console.error('Mark read failed', err)
  }
}

const updateStatus = async (status: string) => {
  try {
    await api.post('/user/status', {
      user_id: currentUser.id,
      status: status
    })
  } catch (err) {
    console.error('Update status failed', err)
  }
}

const addEmoji = (emoji: string) => {
  message.value += emoji
  showEmoji.value = false
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messageListRef.value) {
      const container = messageListRef.value
      container.scrollTop = container.scrollHeight
    }
  })
}

const sortContacts = () => {
  contacts.value.sort((a, b) => {
    const timeA = a.last_time ? new Date(a.last_time).getTime() : 0
    const timeB = b.last_time ? new Date(b.last_time).getTime() : 0
    return timeB - timeA
  })
}

const generateQRCode = async () => {
  const host = window.location.hostname
  const url = `http://${host}:2003/mobile/chat` 
  try {
    qrCodeUrl.value = await QRCode.toDataURL(url)
    showQRCode.value = true
  } catch (err) {
    showSnackbar('二维码生成失败', 'error')
  }
}

onMounted(() => {
  initUser()
  fetchContacts()
  initSocketIO()
})

onUnmounted(() => {
  updateStatus('offline')
  if (socket.value) {
    socket.value.disconnect()
  }
})

const isDark = computed(() => theme.global.current.value.dark)

const formatTime = (timeStr: string) => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <v-container fluid class="fill-height pa-0">
    <v-row class="fill-height ma-0">
      <!-- Contact List -->
      <v-col cols="12" md="3" class="border-e pa-0 d-flex flex-column">
        <v-toolbar color="surface" density="compact" class="border-b">
          <v-toolbar-title class="text-subtitle-1 font-weight-bold">
            消息列表
          </v-toolbar-title>
          <v-btn icon size="small" @click="generateQRCode">
            <v-icon>mdi-qrcode</v-icon>
          </v-btn>
        </v-toolbar>

        <div v-if="loading" class="pa-4">
           <v-skeleton-loader type="list-item-avatar-two-line" count="3"></v-skeleton-loader>
        </div>

        <v-list v-else class="flex-grow-1 overflow-y-auto">
          <v-list-item
            v-for="contact in contacts"
            :key="contact.user_id"
            :value="contact"
            @click="selectContact(contact)"
            :active="selectedContact?.user_id === contact.user_id"
            color="primary"
            rounded="lg"
            class="ma-2"
          >
            <template v-slot:prepend>
              <v-badge
                dot
                :color="contact.status === 'online' ? 'success' : 'grey'"
                location="bottom end"
                offset-x="2"
                offset-y="2"
              >
                <v-avatar color="grey-lighten-2">
                  <span class="text-subtitle-2">{{ contact.username.slice(0, 2).toUpperCase() }}</span>
                </v-avatar>
              </v-badge>
            </template>
            
            <v-list-item-title class="font-weight-medium">
              {{ contact.name || contact.username }}
            </v-list-item-title>
            <v-list-item-subtitle class="text-caption text-truncate">
              {{ contact.last_message || '暂无消息' }}
            </v-list-item-subtitle>
            
            <template v-slot:append>
               <div class="d-flex flex-column align-end">
                 <span class="text-caption text-grey">{{ formatTime(contact.last_time || '') }}</span>
                 <v-badge v-if="contact.unread > 0" color="error" :content="contact.unread" inline></v-badge>
               </div>
            </template>
          </v-list-item>
        </v-list>
      </v-col>

      <!-- Chat Area -->
      <v-col cols="12" md="9" class="d-flex flex-column pa-0 bg-grey-lighten-4" :class="{ 'bg-grey-darken-4': isDark }">
        <template v-if="selectedContact">
          <!-- Chat Header -->
          <v-toolbar color="surface" density="compact" class="border-b px-4">
            <v-avatar size="32" color="primary" class="mr-3">
              <span class="text-white text-caption">{{ selectedContact.username.slice(0, 2).toUpperCase() }}</span>
            </v-avatar>
            <v-toolbar-title class="text-subtitle-2">
              {{ selectedContact.name || selectedContact.username }}
            </v-toolbar-title>
            <v-chip size="x-small" :color="selectedContact.status === 'online' ? 'success' : 'grey'" class="ml-2" variant="flat">
              {{ selectedContact.status === 'online' ? '在线' : '离线' }}
            </v-chip>
          </v-toolbar>

          <!-- Messages -->
          <div 
            class="flex-grow-1 overflow-y-auto pa-4" 
            ref="messageListRef"
            style="height: 0;"
          >
             <div v-if="loadingHistory" class="d-flex justify-center pa-4">
               <v-progress-circular indeterminate color="primary"></v-progress-circular>
             </div>
            <div
              v-for="(msg, index) in messages"
              :key="msg.id || index"
              class="d-flex mb-4"
              :class="msg.from_id === currentUser.id ? 'justify-end' : 'justify-start'"
            >
              <v-card
                :color="msg.from_id === currentUser.id ? 'primary' : 'surface'"
                :theme="msg.from_id === currentUser.id ? 'dark' : undefined"
                class="rounded-xl px-4 py-2"
                max-width="70%"
                elevation="1"
              >
                <div class="text-body-2">{{ msg.content }}</div>
                <div 
                  class="text-caption mt-1" 
                  :class="msg.from_id === currentUser.id ? 'text-blue-lighten-4' : 'text-grey'"
                  style="font-size: 0.7rem;"
                >
                  {{ formatTime(msg.send_time) }}
                </div>
              </v-card>
            </div>
          </div>

          <!-- Input Area -->
          <v-sheet color="surface" class="pa-4 border-t">
            <v-form @submit.prevent="sendMessage">
              <v-text-field
                v-model="message"
                placeholder="输入消息..."
                variant="outlined"
                density="comfortable"
                hide-details
                bg-color="grey-lighten-5"
                rounded="pill"
              >
                <template v-slot:prepend-inner>
                  <v-menu v-model="showEmoji" :close-on-content-click="false">
                    <template v-slot:activator="{ props }">
                      <v-btn icon="mdi-emoticon-outline" variant="text" size="small" v-bind="props"></v-btn>
                    </template>
                    <v-card max-width="300" max-height="200" class="overflow-y-auto pa-2">
                      <v-btn
                        v-for="emoji in emojis"
                        :key="emoji"
                        variant="text"
                        size="x-small"
                        class="ma-1"
                        @click="addEmoji(emoji)"
                      >
                        {{ emoji }}
                      </v-btn>
                    </v-card>
                  </v-menu>
                </template>
                
                <template v-slot:append-inner>
                   <v-btn 
                    icon="mdi-send" 
                    variant="text" 
                    color="primary" 
                    size="small"
                    @click="sendMessage"
                    :disabled="!message.trim()"
                  ></v-btn>
                </template>
              </v-text-field>
            </v-form>
          </v-sheet>
        </template>

        <template v-else>
          <div class="d-flex flex-column align-center justify-center fill-height text-grey">
            <v-icon size="64" class="mb-4">mdi-chat-processing-outline</v-icon>
            <div class="text-h6">选择联系人开始聊天</div>
          </div>
        </template>
      </v-col>
    </v-row>

    <!-- QR Code Dialog -->
    <v-dialog v-model="showQRCode" max-width="300">
      <v-card>
        <v-card-title class="text-center">手机扫码聊天</v-card-title>
        <v-card-text class="text-center">
          <v-img :src="qrCodeUrl" width="200" height="200" class="mx-auto"></v-img>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" text @click="showQRCode = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
  
  <v-snackbar
    v-model="snackbar.show"
    :color="snackbar.color"
    timeout="3000"
    location="top"
  >
    {{ snackbar.text }}
    <template v-slot:actions>
      <v-btn variant="text" @click="snackbar.show = false">关闭</v-btn>
    </template>
  </v-snackbar>
</template>

<style scoped>
/* Styles remain similar */
</style>
