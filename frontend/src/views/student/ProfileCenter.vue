<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, Lock, Location, Bell, Edit, Check, Close } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// --- 1. 类型定义 ---
interface UserInfo {
  name: string
  studentId: string
  gender: string
  major: string
  grade: string
  class: string
  phone: string
  email: string
  avatar: string
}

interface PasswordForm {
  oldPwd: string
  newPwd: string
  confirmPwd: string
}

interface Address {
  id: number
  recipient: string
  phone: string
  province: string
  city: string
  district: string
  detail: string
  isDefault: boolean
}

interface Message {
  id: number
  title: string
  type: string
  time: string
  status: 'read' | 'unread'
  content: string
}

// --- 2. 状态管理 ---
const activeMenu = ref('info')
const isEditing = ref(false)

// 个人信息
const userInfo = reactive<UserInfo>({
  name: '张三',
  studentId: '20230001',
  gender: '男',
  major: '计算机科学与技术',
  grade: '2023级',
  class: '1班',
  phone: '13800138000',
  email: 'zhangsan@example.com',
  avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png'
})

const originalUserInfo = ref<UserInfo>({ ...userInfo })

// 密码修改
const passwordForm = reactive<PasswordForm>({
  oldPwd: '',
  newPwd: '',
  confirmPwd: ''
})

const passwordRules = {
  oldPwd: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPwd: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少8位', trigger: 'blur' },
    { 
      pattern: /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$/, 
      message: '密码必须包含字母和数字', 
      trigger: 'blur' 
    }
  ],
  confirmPwd: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { 
      validator: (rule: any, value: string, callback: any) => {
        if (value !== passwordForm.newPwd) {
          callback(new Error('两次密码不一致'))
        } else {
          callback()
        }
      }, 
      trigger: 'blur' 
    }
  ]
}

const showPassword = ref(false)
const passwordFormRef = ref()

// 地址管理
const addresses = ref<Address[]>([
  {
    id: 1,
    recipient: '张三',
    phone: '13800138000',
    province: '北京市',
    city: '北京市',
    district: '海淀区',
    detail: '清华大学紫荆公寓1号楼101室',
    isDefault: true
  }
])

const addressDialogVisible = ref(false)
const addressDialogType = ref<'add' | 'edit'>('add')
const currentAddress = reactive<Address>({
  id: 0,
  recipient: '',
  phone: '',
  province: '',
  city: '',
  district: '',
  detail: '',
  isDefault: false
})

// 消息通知
const messages = ref<Message[]>([
  { id: 1, title: '选课成功通知', type: '选课通知', time: '2024-12-01 10:30', status: 'unread', content: '您已成功选修《数据库原理》课程，请按时上课。' },
  { id: 2, title: '成绩发布通知', type: '成绩通知', time: '2024-11-28 14:20', status: 'unread', content: '《高等数学A》课程成绩已发布，您的成绩为92分。' },
  { id: 3, title: '系统维护公告', type: '系统通知', time: '2024-11-25 09:00', status: 'read', content: '系统将于本周六凌晨2:00-4:00进行维护，期间无法访问。' },
  { id: 4, title: '选课提醒', type: '选课通知', time: '2024-11-20 16:45', status: 'read', content: '下学期选课将于12月5日开始，请提前做好准备。' },
  { id: 5, title: '成绩复核通知', type: '成绩通知', time: '2024-11-15 11:30', status: 'unread', content: '成绩复核申请已受理，预计3个工作日内给出结果。' },
  { id: 6, title: '课程调整通知', type: '系统通知', time: '2024-11-10 13:15', status: 'read', content: '《操作系统》课程时间调整为每周三下午2-4节。' },
  { id: 7, title: '奖学金公示', type: '系统通知', time: '2024-11-05 10:00', status: 'read', content: '2023-2024学年奖学金评选结果已公示，请查看。' },
  { id: 8, title: '选课冲突提醒', type: '选课通知', time: '2024-11-01 15:20', status: 'read', content: '您选择的课程存在时间冲突，请及时调整。' }
])

const messageTypeFilter = ref('')
const messageStatusFilter = ref('')
const messageDialogVisible = ref(false)
const currentMessage = ref<Message | null>(null)

const filteredMessages = computed(() => {
  let result = messages.value
  if (messageTypeFilter.value) {
    result = result.filter(m => m.type === messageTypeFilter.value)
  }
  if (messageStatusFilter.value) {
    result = result.filter(m => m.status === messageStatusFilter.value)
  }
  return result
})

const unreadCount = computed(() => messages.value.filter(m => m.status === 'unread').length)

// --- 3. 核心逻辑 ---

// 个人信息编辑
const startEdit = () => {
  isEditing.value = true
}

const cancelEdit = () => {
  Object.assign(userInfo, originalUserInfo.value)
  isEditing.value = false
}

const saveUserInfo = () => {
  // 真实场景下需调用接口保存到数据库，此处为本地演示
  localStorage.setItem('user_info', JSON.stringify(userInfo))
  originalUserInfo.value = { ...userInfo }
  isEditing.value = false
  ElMessage.success('个人信息保存成功')
}

const resetAvatar = () => {
  userInfo.avatar = 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png'
  ElMessage.success('头像已重置为默认头像')
}

// 密码修改
const changePassword = async () => {
  if (!passwordFormRef.value) return
  
  await passwordFormRef.value.validate((valid: boolean) => {
    if (valid) {
      // 校验原密码
      if (passwordForm.oldPwd !== '123456') {
        ElMessage.error('原密码错误')
        return
      }
      
      ElMessage.success('密码修改成功，请重新登录')
      setTimeout(() => {
        localStorage.removeItem('is_login')
        router.push('/login')
      }, 1500)
    }
  })
}

// 地址管理
const openAddressDialog = (type: 'add' | 'edit', address?: Address) => {
  addressDialogType.value = type
  if (type === 'add') {
    Object.assign(currentAddress, {
      id: 0,
      recipient: '',
      phone: '',
      province: '',
      city: '',
      district: '',
      detail: '',
      isDefault: false
    })
  } else if (address) {
    Object.assign(currentAddress, address)
  }
  addressDialogVisible.value = true
}

const saveAddress = () => {
  if (addressDialogType.value === 'add') {
    const newAddress = {
      ...currentAddress,
      id: Date.now()
    }
    addresses.value.push(newAddress)
    ElMessage.success('地址添加成功')
  } else {
    const index = addresses.value.findIndex(a => a.id === currentAddress.id)
    if (index !== -1) {
      addresses.value[index] = { ...currentAddress }
      ElMessage.success('地址修改成功')
    }
  }
  addressDialogVisible.value = false
  localStorage.setItem('user_addresses', JSON.stringify(addresses.value))
}

const deleteAddress = (id: number) => {
  ElMessageBox.confirm('确定要删除该地址吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    addresses.value = addresses.value.filter(a => a.id !== id)
    localStorage.setItem('user_addresses', JSON.stringify(addresses.value))
    ElMessage.success('地址删除成功')
  })
}

const setDefaultAddress = (id: number) => {
  addresses.value.forEach(a => {
    a.isDefault = a.id === id
  })
  localStorage.setItem('user_addresses', JSON.stringify(addresses.value))
  ElMessage.success('默认地址设置成功')
}

// 消息通知
const viewMessage = (message: Message) => {
  currentMessage.value = message
  messageDialogVisible.value = true
  
  // 标记为已读
  if (message.status === 'unread') {
    message.status = 'read'
    localStorage.setItem('user_messages', JSON.stringify(messages.value))
  }
}

// 菜单切换前检查
const beforeMenuChange = (menu: string) => {
  if (activeMenu.value === 'info' && isEditing.value) {
    ElMessageBox.confirm('是否放弃未保存的修改？', '提示', {
      confirmButtonText: '放弃',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(() => {
      cancelEdit()
      activeMenu.value = menu
    })
  } else {
    activeMenu.value = menu
  }
}

// 加载本地数据
const loadLocalData = () => {
  const savedInfo = localStorage.getItem('user_info')
  if (savedInfo) {
    Object.assign(userInfo, JSON.parse(savedInfo))
    originalUserInfo.value = { ...userInfo }
  }
  
  const savedAddresses = localStorage.getItem('user_addresses')
  if (savedAddresses) {
    addresses.value = JSON.parse(savedAddresses)
  }
  
  const savedMessages = localStorage.getItem('user_messages')
  if (savedMessages) {
    messages.value = JSON.parse(savedMessages)
  }
}

loadLocalData()
</script>

<template>
  <div class="profile-center-container">
    <el-card class="profile-card">
      <div class="profile-layout">
        <!-- 左侧菜单 -->
        <div class="left-menu">
          <el-menu :default-active="activeMenu" @select="beforeMenuChange">
            <el-menu-item index="info">
              <el-icon><User /></el-icon>
              <span>个人信息</span>
            </el-menu-item>
            <el-menu-item index="password">
              <el-icon><Lock /></el-icon>
              <span>密码修改</span>
            </el-menu-item>
            <el-menu-item index="address">
              <el-icon><Location /></el-icon>
              <span>地址管理</span>
            </el-menu-item>
            <el-menu-item index="message">
              <el-icon><Bell /></el-icon>
              <span>消息通知</span>
              <el-badge v-if="unreadCount > 0" :value="unreadCount" class="message-badge" />
            </el-menu-item>
          </el-menu>
        </div>

        <!-- 右侧内容区 -->
        <div class="right-content">
          <!-- 个人信息 -->
          <div v-show="activeMenu === 'info'" class="content-section">
            <div class="section-header">
              <h3>个人信息</h3>
              <div class="header-actions">
                <el-button v-if="!isEditing" type="primary" :icon="Edit" @click="startEdit">编辑</el-button>
                <template v-else>
                  <el-button :icon="Check" type="success" @click="saveUserInfo">保存</el-button>
                  <el-button :icon="Close" @click="cancelEdit">取消</el-button>
                </template>
              </div>
            </div>
            
            <el-form :model="userInfo" label-width="100px" class="info-form">
              <el-form-item label="头像">
                <div class="avatar-section">
                  <el-avatar :size="80" :src="userInfo.avatar" />
                  <el-button v-if="isEditing" size="small" @click="resetAvatar" style="margin-left: 20px">重置头像</el-button>
                  <div class="avatar-tip">真实场景下需调用文件上传接口，此处为本地演示</div>
                </div>
              </el-form-item>
              <el-form-item label="姓名">
                <el-input v-model="userInfo.name" :disabled="!isEditing" style="width: 300px" />
              </el-form-item>
              <el-form-item label="学号">
                <el-input v-model="userInfo.studentId" disabled style="width: 300px" />
              </el-form-item>
              <el-form-item label="性别">
                <el-radio-group v-model="userInfo.gender" :disabled="!isEditing">
                  <el-radio label="男">男</el-radio>
                  <el-radio label="女">女</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="专业">
                <el-input v-model="userInfo.major" disabled style="width: 300px" />
              </el-form-item>
              <el-form-item label="年级">
                <el-input v-model="userInfo.grade" disabled style="width: 300px" />
              </el-form-item>
              <el-form-item label="班级">
                <el-input v-model="userInfo.class" disabled style="width: 300px" />
              </el-form-item>
              <el-form-item label="联系电话">
                <el-input v-model="userInfo.phone" :disabled="!isEditing" style="width: 300px" />
              </el-form-item>
              <el-form-item label="邮箱">
                <el-input v-model="userInfo.email" :disabled="!isEditing" style="width: 300px" />
              </el-form-item>
            </el-form>
          </div>

          <!-- 密码修改 -->
          <div v-show="activeMenu === 'password'" class="content-section">
            <div class="section-header">
              <h3>密码修改</h3>
            </div>
            
            <el-form :model="passwordForm" :rules="passwordRules" ref="passwordFormRef" label-width="120px" class="password-form">
              <el-form-item label="原密码" prop="oldPwd">
                <el-input v-model="passwordForm.oldPwd" type="password" style="width: 300px" />
              </el-form-item>
              <el-form-item label="新密码" prop="newPwd">
                <el-input 
                  v-model="passwordForm.newPwd" 
                  :type="showPassword ? 'text' : 'password'" 
                  style="width: 300px"
                >
                  <template #suffix>
                    <el-icon @click="showPassword = !showPassword" style="cursor: pointer">
                      <component :is="showPassword ? 'View' : 'Hide'" />
                    </el-icon>
                  </template>
                </el-input>
              </el-form-item>
              <el-form-item label="确认新密码" prop="confirmPwd">
                <el-input v-model="passwordForm.confirmPwd" type="password" style="width: 300px" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="changePassword">修改密码</el-button>
              </el-form-item>
            </el-form>
          </div>

          <!-- 地址管理 -->
          <div v-show="activeMenu === 'address'" class="content-section">
            <div class="section-header">
              <h3>地址管理</h3>
              <el-button type="primary" @click="openAddressDialog('add')">新增地址</el-button>
            </div>
            
            <div class="address-list">
              <el-card v-for="addr in addresses" :key="addr.id" class="address-card" :class="{ 'default-address': addr.isDefault }">
                <div class="address-header">
                  <span class="recipient">{{ addr.recipient }}</span>
                  <span class="phone">{{ addr.phone }}</span>
                  <el-tag v-if="addr.isDefault" type="success" size="small">默认</el-tag>
                </div>
                <div class="address-detail">
                  {{ addr.province }} {{ addr.city }} {{ addr.district }} {{ addr.detail }}
                </div>
                <div class="address-actions">
                  <el-button link type="primary" @click="openAddressDialog('edit', addr)">编辑</el-button>
                  <el-button link type="danger" @click="deleteAddress(addr.id)">删除</el-button>
                  <el-button v-if="!addr.isDefault" link type="success" @click="setDefaultAddress(addr.id)">设为默认</el-button>
                </div>
              </el-card>
            </div>
          </div>

          <!-- 消息通知 -->
          <div v-show="activeMenu === 'message'" class="content-section">
            <div class="section-header">
              <h3>消息通知</h3>
              <div class="message-filters">
                <el-select v-model="messageTypeFilter" placeholder="消息类型" style="width: 120px; margin-right: 10px" clearable>
                  <el-option label="系统通知" value="系统通知" />
                  <el-option label="选课通知" value="选课通知" />
                  <el-option label="成绩通知" value="成绩通知" />
                </el-select>
                <el-select v-model="messageStatusFilter" placeholder="状态" style="width: 100px" clearable>
                  <el-option label="未读" value="unread" />
                  <el-option label="已读" value="read" />
                </el-select>
              </div>
            </div>
            
            <el-table :data="filteredMessages" style="width: 100%" :row-class-name="({ row }) => row.status === 'unread' ? 'unread-row' : ''">
              <el-table-column prop="title" label="消息标题" min-width="200" />
              <el-table-column prop="type" label="消息类型" width="120" />
              <el-table-column prop="time" label="发送时间" width="180" />
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'unread' ? 'danger' : 'info'" size="small">
                    {{ row.status === 'unread' ? '未读' : '已读' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120">
                <template #default="{ row }">
                  <el-button link type="primary" @click="viewMessage(row)">查看详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 地址弹窗 -->
    <el-dialog
      v-model="addressDialogVisible"
      :title="addressDialogType === 'add' ? '新增地址' : '编辑地址'"
      width="500px"
    >
      <el-form :model="currentAddress" label-width="100px">
        <el-form-item label="收件人">
          <el-input v-model="currentAddress.recipient" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="currentAddress.phone" />
        </el-form-item>
        <el-form-item label="省">
          <el-input v-model="currentAddress.province" />
        </el-form-item>
        <el-form-item label="市">
          <el-input v-model="currentAddress.city" />
        </el-form-item>
        <el-form-item label="区">
          <el-input v-model="currentAddress.district" />
        </el-form-item>
        <el-form-item label="详细地址">
          <el-input v-model="currentAddress.detail" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="currentAddress.isDefault" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addressDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveAddress">确定</el-button>
      </template>
    </el-dialog>

    <!-- 消息详情弹窗 -->
    <el-dialog
      v-model="messageDialogVisible"
      :title="currentMessage?.title"
      width="600px"
    >
      <div v-if="currentMessage" class="message-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="消息类型">{{ currentMessage.type }}</el-descriptions-item>
          <el-descriptions-item label="发送时间">{{ currentMessage.time }}</el-descriptions-item>
        </el-descriptions>
        <div class="message-content">
          <h4>消息内容</h4>
          <p>{{ currentMessage.content }}</p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.profile-center-container {
  height: 100%;
}
.profile-card {
  height: 100%;
}
.profile-layout {
  display: flex;
  height: 100%;
  gap: 20px;
}
.left-menu {
  width: 200px;
  flex-shrink: 0;
  border-right: 1px solid #DCDFE6;
}
.left-menu :deep(.el-menu-item.is-active) {
  background-color: #E6F7FF;
  color: #409EFF;
}
.message-badge {
  margin-left: 10px;
}
.right-content {
  flex: 1;
  overflow: auto;
  padding: 0 20px;
}
.content-section {
  min-height: 400px;
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #DCDFE6;
}
.section-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
.header-actions {
  display: flex;
  gap: 10px;
}
.info-form, .password-form {
  margin-top: 20px;
}
.info-form :deep(.el-form-item) {
  margin-bottom: 20px;
}
.avatar-section {
  display: flex;
  align-items: center;
}
.avatar-tip {
  font-size: 12px;
  color: #909399;
  margin-left: 20px;
}
.address-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 15px;
}
.address-card {
  border: 1px solid #DCDFE6;
  transition: all 0.3s;
}
.address-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.address-card.default-address {
  border-color: #409EFF;
}
.address-header {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 10px;
}
.recipient {
  font-weight: 600;
  font-size: 16px;
}
.phone {
  color: #606266;
}
.address-detail {
  color: #606266;
  margin-bottom: 15px;
  line-height: 1.6;
}
.address-actions {
  display: flex;
  gap: 10px;
}
.message-filters {
  display: flex;
  gap: 10px;
}
:deep(.el-table .unread-row) {
  border-left: 3px solid #F56C6C;
}
:deep(.el-table__body tr:hover > td) {
  background-color: #E6F7FF !important;
}
.message-detail {
  padding: 10px 0;
}
.message-content {
  margin-top: 20px;
}
.message-content h4 {
  margin-bottom: 10px;
  font-size: 14px;
  font-weight: 600;
}
.message-content p {
  line-height: 1.8;
  color: #606266;
}
</style>
