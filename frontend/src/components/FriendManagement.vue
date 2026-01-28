<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Check, Close, Delete } from '@element-plus/icons-vue'
import { friendAPI, type FriendSearchResult, type FriendRequest, type FriendInfo } from '../api/friend'

// Props
const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'refresh-contacts'): void
}>()

// Tab state
const activeTab = ref('add')

// 添加好友 Tab
const searchKeyword = ref('')
const searchResults = ref<FriendSearchResult[]>([])
const searching = ref(false)

// 好友申请 Tab
const receivedRequests = ref<FriendRequest[]>([])
const sentRequests = ref<FriendRequest[]>([])
const loadingRequests = ref(false)

// 我的好友 Tab
const friendList = ref<FriendInfo[]>([])
const loadingFriends = ref(false)

// 搜索用户
const handleSearch = async () => {
  if (!searchKeyword.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  
  searching.value = true
  try {
    const res = await friendAPI.searchUser(searchKeyword.value)
    searchResults.value = res.data.data.results || []
    
    if (searchResults.value.length === 0) {
      ElMessage.info('未找到匹配的用户')
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '搜索失败')
  } finally {
    searching.value = false
  }
}

// 发送好友申请
const sendFriendRequest = async (user: FriendSearchResult) => {
  try {
    const { value: message } = await ElMessageBox.prompt('请输入申请消息（可选）', '添加好友', {
      confirmButtonText: '发送',
      cancelButtonText: '取消',
      inputPlaceholder: '如: 你好，我想加你为好友',
      inputPattern: /.{0,200}/,
      inputErrorMessage: '消息长度不能超过200字符'
    })
    
    await friendAPI.sendRequest(user.user_id, message || undefined)
    ElMessage.success('好友申请已发送')
    
    // 刷新搜索结果
    await handleSearch()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '发送申请失败')
    }
  }
}

// 加载收到的好友申请
const loadReceivedRequests = async () => {
  loadingRequests.value = true
  try {
    const res = await friendAPI.getReceivedRequests()
    receivedRequests.value = res.data.data.requests || []
  } catch (error: any) {
    ElMessage.error('加载申请列表失败')
  } finally {
    loadingRequests.value = false
  }
}

// 加载发出的好友申请
const loadSentRequests = async () => {
  loadingRequests.value = true
  try {
    const res = await friendAPI.getSentRequests()
    sentRequests.value = res.data.data.requests || []
  } catch (error: any) {
    ElMessage.error('加载申请列表失败')
  } finally {
    loadingRequests.value = false
  }
}

// 处理好友申请
const processRequest = async (requestId: number, action: 'accept' | 'reject') => {
  try {
    await friendAPI.processRequest(requestId, action)
    ElMessage.success(action === 'accept' ? '已接受好友申请' : '已拒绝好友申请')
    
    // 刷新申请列表和好友列表
    await loadReceivedRequests()
    if (action === 'accept') {
      await loadFriendList()
      emit('refresh-contacts')  // 通知父组件刷新联系人列表
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

// 加载好友列表
const loadFriendList = async () => {
  loadingFriends.value = true
  try {
    const res = await friendAPI.getFriendList()
    friendList.value = res.data.data.friends || []
  } catch (error: any) {
    ElMessage.error('加载好友列表失败')
  } finally {
    loadingFriends.value = false
  }
}

// 删除好友
const deleteFriend = async (friend: FriendInfo) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除好友 "${friend.name}" 吗？`,
      '删除好友',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await friendAPI.deleteFriend(friend.user_id)
    ElMessage.success('已删除好友')
    
    await loadFriendList()
    emit('refresh-contacts')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

// 获取状态颜色
const getStatusColor = (status: string) => {
  switch (status) {
    case 'online': return '#52C41A'
    case 'away': return '#FAAD14'
    default: return '#D9D9D9'
  }
}

// 获取状态文本
const getStatusText = (status: string) => {
  switch (status) {
    case 'online': return '在线'
    case 'away': return '离开'
    default: return '离线'
  }
}

// 格式化时间
const formatTime = (timeStr: string) => {
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  if (diff < 86400000) { // 小于1天
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }else if (diff < 172800000) { // 小于2天
    return '昨天'
  } else {
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  }
}

// Tab切换时加载数据
const handleTabChange = (tabName: string) => {
  if (tabName === 'requests') {
    loadReceivedRequests()
    loadSentRequests()
  } else if (tabName === 'friends') {
    loadFriendList()
  }
}

// 组件挂载时加载待处理申请数量
onMounted(() => {
  loadReceivedRequests()
})

// 获取待处理申请数量
const pendingCount = ref(0)
const updatePendingCount = () => {
  pendingCount.value = receivedRequests.value.filter(r => r.status === 'pending').length
}

// 监听申请列表变化
const loadPendingCount = async () => {
  try {
    const res = await friendAPI.getReceivedRequests('pending')
    pendingCount.value = res.data.data.total || 0
  } catch (error) {
    // ignore
  }
}

onMounted(() => {
  loadPendingCount()
})

defineExpose({
  loadPendingCount
})
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="emit('update:visible', $event)"
    title="好友管理"
    width="700px"
    :close-on-click-modal="false"
  >
    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <!-- 添加好友 Tab -->
      <el-tab-pane label="添加好友" name="add">
        <div class="search-section">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索姓名、学号或工号"
            :prefix-icon="Search"
            clearable
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button :icon="Search" @click="handleSearch" :loading="searching">搜索</el-button>
            </template>
          </el-input>
        </div>

        <div class="search-results">
          <div v-if="searchResults.length === 0 && !searching" class="empty-state">
            <el-empty description="输入关键词搜索用户" :image-size="80" />
          </div>

          <div v-else class="user-list">
            <div
              v-for="user in searchResults"
              :key="user.user_id"
              class="user-item"
            >
              <div class="user-avatar" :class="user.role">
                {{ user.name.charAt(0) }}
              </div>
              <div class="user-info">
                <div class="user-name">{{ user.name }}</div>
                <div class="user-meta">
                  {{ user.username }}
                  <span v-if="user.dept" class="user-dept">· {{ user.dept }}</span>
                </div>
              </div>
              <div class="user-actions">
                <el-tag v-if="user.is_friend" type="success" size="small">已是好友</el-tag>
                <el-tag v-else-if="user.has_pending_request && user.request_direction === 'sent'" type="info" size="small">
                  已发送申请
                </el-tag>
                <el-tag v-else-if="user.has_pending_request && user.request_direction === 'received'" type="warning" size="small">
                  待处理
                </el-tag>
                <el-button
                  v-else
                  type="primary"
                  size="small"
                  @click="sendFriendRequest(user)"
                >
                  添加好友
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 好友申请 Tab -->
      <el-tab-pane name="requests">
        <template #label>
          <el-badge :value="pendingCount" :hidden="pendingCount === 0" :max="99">
            好友申请
          </el-badge>
        </template>

        <el-tabs type="card" class="request-tabs">
          <el-tab-pane label="收到的申请">
            <div v-loading="loadingRequests">
              <div v-if="receivedRequests.length === 0" class="empty-state">
                <el-empty description="暂无好友申请" :image-size="80" />
              </div>
              <div v-else class="request-list">
                <div
                  v-for="request in receivedRequests"
                  :key="request.id"
                  class="request-item"
                >
                  <div class="request-avatar" :class="request.from_user_name ? 'student' : 'teacher'">
                    {{ (request.from_user_name || '?').charAt(0) }}
                  </div>
                  <div class="request-info">
                    <div class="request-name">{{ request.from_user_name }}</div>
                    <div class="request-username">{{ request.from_user_username }}</div>
                    <div v-if="request.message" class="request-message">{{ request.message }}</div>
                    <div class="request-time">{{ formatTime(request.created_at) }}</div>
                  </div>
                  <div class="request-actions">
                    <template v-if="request.status === 'pending'">
                      <el-button
                        type="success"
                        size="small"
                        :icon="Check"
                        @click="processRequest(request.id, 'accept')"
                      >
                        接受
                      </el-button>
                      <el-button
                        type="danger"
                        size="small"
                        :icon="Close"
                        @click="processRequest(request.id, 'reject')"
                      >
                        拒绝
                      </el-button>
                    </template>
                    <el-tag v-else-if="request.status === 'accepted'" type="success" size="small">
                      已接受
                    </el-tag>
                    <el-tag v-else type="info" size="small">已拒绝</el-tag>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="发出的申请">
            <div v-loading="loadingRequests">
              <div v-if="sentRequests.length === 0" class="empty-state">
                <el-empty description="暂无发出的申请" :image-size="80" />
              </div>
              <div v-else class="request-list">
                <div
                  v-for="request in sentRequests"
                  :key="request.id"
                  class="request-item"
                >
                  <div class="request-avatar">
                    {{ (request.to_user_name || '?').charAt(0) }}
                  </div>
                  <div class="request-info">
                    <div class="request-name">{{ request.to_user_name }}</div>
                    <div class="request-username">{{ request.to_user_username }}</div>
                    <div v-if="request.message" class="request-message">{{ request.message }}</div>
                    <div class="request-time">{{ formatTime(request.created_at) }}</div>
                  </div>
                  <div class="request-status">
                    <el-tag v-if="request.status === 'pending'" type="warning" size="small">
                      待处理
                    </el-tag>
                    <el-tag v-else-if="request.status === 'accepted'" type="success" size="small">
                      已接受
                    </el-tag>
                    <el-tag v-else type="info" size="small">已拒绝</el-tag>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-tab-pane>

      <!-- 我的好友 Tab -->
      <el-tab-pane label="我的好友" name="friends">
        <div v-loading="loadingFriends">
          <div v-if="friendList.length === 0" class="empty-state">
            <el-empty description="暂无好友" :image-size="80" />
          </div>
          <div v-else class="friend-list">
            <div
              v-for="friend in friendList"
              :key="friend.user_id"
              class="friend-item"
            >
              <div class="friend-avatar-wrapper">
                <div class="friend-avatar" :class="friend.role">
                  {{ friend.name.charAt(0) }}
                </div>
                <span
                  class="status-dot"
                  :style="{ backgroundColor: getStatusColor(friend.status) }"
                />
              </div>
              <div class="friend-info">
                <div class="friend-name">{{ friend.name }}</div>
                <div class="friend-meta">
                  {{ friend.username }}
                  <span v-if="friend.dept">· {{ friend.dept }}</span>
                </div>
                <div class="friend-status" :style="{ color: getStatusColor(friend.status) }">
                  {{ getStatusText(friend.status) }}
                </div>
              </div>
              <div class="friend-actions">
                <el-button
                  type="danger"
                  size="small"
                  :icon="Delete"
                  text
                  @click="deleteFriend(friend)"
                >
                  删除
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>

<style scoped>
.search-section {
  margin-bottom: 20px;
}

.search-results {
  max-height: 450px;
  overflow-y: auto;
}

.empty-state {
  padding: 40px 0;
  text-align: center;
}

.user-list,
.request-list,
.friend-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-item,
.request-item,
.friend-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  transition: all 0.2s;
}

.user-item:hover,
.request-item:hover,
.friend-item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.user-avatar,
.request-avatar,
.friend-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: 500;
  margin-right: 12px;
  flex-shrink: 0;
}

.user-avatar.student,
.request-avatar.student,
.friend-avatar.student {
  background: linear-gradient(135deg, #409EFF, #66B1FF);
}

.user-avatar.teacher,
.request-avatar.teacher,
.friend-avatar.teacher {
  background: linear-gradient(135deg, #52C41A, #73D13D);
}

.user-avatar.admin,
.request-avatar.admin,
.friend-avatar.admin {
  background: linear-gradient(135deg, #F56C6C, #F78989);
}

.friend-avatar-wrapper {
  position: relative;
  margin-right: 12px;
}

.status-dot {
  position: absolute;
  bottom: 2px;
  right: 2px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid #fff;
}

.user-info,
.request-info,
.friend-info {
  flex: 1;
  min-width: 0;
}

.user-name,
.request-name,
.friend-name {
  font-size: 15px;
  font-weight: 500;
  color: #fff;
  margin-bottom: 4px;
}

.user-meta,
.request-username,
.friend-meta {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
}

.user-dept {
  margin-left: 4px;
}

.request-message {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
  margin-top: 4px;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 4px;
}

.request-time,
.friend-status {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 4px;
}

.user-actions,
.request-actions,
.request-status,
.friend-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.request-tabs {
  margin-top: -10px;
}

.request-tabs :deep(.el-tabs__content) {
  padding-top: 16px;
}
</style>
