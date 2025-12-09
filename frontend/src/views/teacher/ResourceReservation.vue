<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Calendar, User, Phone, Timer, CircleCheck, CircleClose, Warning } from '@element-plus/icons-vue'

// --- 1. 类型定义 ---
type ReservationStatus = 'pending' | 'approved' | 'rejected' | 'cancelled'
type ResourceType = 'classroom' | 'lab'

interface Resource {
  id: number
  name: string
  type: string
  capacity: number
  location: string
  devices: string[]
  status: 'idle' | 'in_use'
}

interface TimeSlot {
  id: number
  name: string
  time: string
  available: boolean
}

interface Reservation {
  id: number
  resourceName: string
  type: string
  date: string
  timeSlots: string[]
  purpose: string
  applicant: string
  phone: string
  status: ReservationStatus
  reason?: string // 拒绝原因
  createTime: string
}

// --- 2. 模拟数据 ---
// 可预约资源（同步管理员端空闲资源）
const mockResources: Resource[] = [
  { id: 1, name: '多媒体教室 101', type: 'classroom', capacity: 100, location: '教学楼A-101', devices: ['多媒体', '空调', '投影仪'], status: 'idle' },
  { id: 2, name: '多媒体教室 102', type: 'classroom', capacity: 100, location: '教学楼A-102', devices: ['多媒体', '空调', '投影仪'], status: 'idle' },
  { id: 3, name: '普通教室 106', type: 'classroom', capacity: 60, location: '教学楼A-201', devices: ['空调'], status: 'idle' },
  { id: 4, name: '普通教室 107', type: 'classroom', capacity: 60, location: '教学楼A-202', devices: ['空调'], status: 'idle' },
  { id: 5, name: '计算机实验室 201', type: 'lab', capacity: 40, location: '实验楼B-301', devices: ['电脑', '投影仪'], status: 'idle' },
  { id: 6, name: '物理实验室 202', type: 'lab', capacity: 40, location: '实验楼B-302', devices: ['实验仪器'], status: 'idle' },
]

// 我的预约记录
const mockReservations: Reservation[] = [
  { id: 1, resourceName: '多媒体教室 101', type: 'classroom', date: '2024-05-20', timeSlots: ['08:00-09:40', '10:00-11:40'], purpose: '补课', applicant: '王老师', phone: '13800138000', status: 'approved', createTime: '2024-05-18 10:00' },
  { id: 2, resourceName: '计算机实验室 201', type: 'lab', date: '2024-05-21', timeSlots: ['14:00-15:40'], purpose: '上机实验', applicant: '王老师', phone: '13800138000', status: 'pending', createTime: '2024-05-19 09:00' },
  { id: 3, resourceName: '普通教室 106', type: 'classroom', date: '2024-05-22', timeSlots: ['19:00-20:40'], purpose: '班会', applicant: '王老师', phone: '13800138000', status: 'rejected', reason: '该时段已被占用', createTime: '2024-05-19 14:00' },
]

// 时段定义
const allTimeSlots: TimeSlot[] = [
  { id: 1, name: '第1-2节', time: '08:00-09:40', available: true },
  { id: 2, name: '第3-4节', time: '10:00-11:40', available: true },
  { id: 3, name: '第5-6节', time: '14:00-15:40', available: true },
  { id: 4, name: '第7-8节', time: '16:00-17:40', available: true },
  { id: 5, name: '第9-10节', time: '19:00-20:40', available: true },
]

// --- 3. 状态管理 ---
const activeTab = ref<ResourceType>('classroom')
const showMyReservations = ref(false) // 是否显示我的预约
const loading = ref(false)

// 筛选条件
const filters = reactive({
  date: new Date().toISOString().split('T')[0],
  capacity: undefined as number | undefined,
  devices: [] as string[]
})

// 预约弹窗
const dialogVisible = ref(false)
const currentResource = ref<Resource | null>(null)
const currentSlots = ref<TimeSlot[]>([])
const selectedSlotIds = ref<number[]>([])
const reservationForm = reactive({
  purpose: '',
  applicant: '当前教师', // 模拟默认值
  phone: ''
})

// --- 4. 计算属性 ---
const filteredResources = computed(() => {
  return mockResources.filter(res => {
    // 类型筛选
    if (res.type !== activeTab.value) return false
    
    // 容量筛选
    if (filters.capacity && res.capacity < filters.capacity) return false
    
    // 设备筛选
    if (filters.devices.length > 0) {
      const hasAllDevices = filters.devices.every(dev => res.devices.includes(dev))
      if (!hasAllDevices) return false
    }
    
    return true
  })
})

const myReservationList = ref<Reservation[]>(mockReservations)

// --- 5. 核心逻辑 ---

// 切换视图
const toggleView = () => {
  showMyReservations.value = !showMyReservations.value
}

// 打开预约弹窗
const handleReserve = (row: Resource) => {
  currentResource.value = row
  // 模拟加载时段可用性（随机禁用一些时段）
  currentSlots.value = allTimeSlots.map(slot => ({
    ...slot,
    available: Math.random() > 0.3 // 70%概率可用
  }))
  selectedSlotIds.value = []
  reservationForm.purpose = ''
  reservationForm.phone = ''
  dialogVisible.value = true
}

// 全选/取消全选时段
const handleSelectAllSlots = (val: boolean) => {
  if (val) {
    selectedSlotIds.value = currentSlots.value.filter(s => s.available).map(s => s.id)
  } else {
    selectedSlotIds.value = []
  }
}

// 提交预约
const submitReservation = () => {
  if (selectedSlotIds.value.length === 0) {
    ElMessage.warning('请至少选择一个时段')
    return
  }
  if (!reservationForm.purpose) {
    ElMessage.warning('请填写预约用途')
    return
  }
  if (!reservationForm.phone) {
    ElMessage.warning('请填写联系电话')
    return
  }

  loading.value = true
  setTimeout(() => {
    const newReservation: Reservation = {
      id: Date.now(),
      resourceName: currentResource.value!.name,
      type: currentResource.value!.type,
      date: filters.date,
      timeSlots: currentSlots.value.filter(s => selectedSlotIds.value.includes(s.id)).map(s => `${s.time}`),
      purpose: reservationForm.purpose,
      applicant: reservationForm.applicant,
      phone: reservationForm.phone,
      status: 'approved', // 模拟自动通过
      createTime: new Date().toLocaleString()
    }
    
    myReservationList.value.unshift(newReservation)
    ElMessage.success('预约提交成功（模拟自动审核通过）')
    dialogVisible.value = false
    loading.value = false
  }, 800)
}

// 取消预约
const handleCancel = (row: Reservation) => {
  ElMessageBox.confirm('确定要取消该预约吗？', '提示', {
    type: 'warning'
  }).then(() => {
    row.status = 'cancelled'
    ElMessage.success('预约已取消')
  })
}

// 状态标签颜色
const getStatusTagType = (status: ReservationStatus) => {
  const map: Record<ReservationStatus, string> = {
    pending: '',
    approved: 'success',
    rejected: 'danger',
    cancelled: 'info'
  }
  return map[status]
}

const getStatusLabel = (status: ReservationStatus) => {
  const map: Record<ReservationStatus, string> = {
    pending: '待审核',
    approved: '已通过',
    rejected: '已拒绝',
    cancelled: '已取消'
  }
  return map[status]
}

// 禁用过去日期
const disabledDate = (time: Date) => {
  return time.getTime() < Date.now() - 8.64e7
}
</script>

<template>
  <div class="reservation-container">
    <!-- 顶部导航 -->
    <div class="top-bar">
      <el-tabs v-model="activeTab" class="type-tabs" v-if="!showMyReservations">
        <el-tab-pane label="教室预约" name="classroom" />
        <el-tab-pane label="实验室预约" name="lab" />
      </el-tabs>
      <div class="page-title" v-else>我的预约记录</div>
      
      <el-button 
        :type="showMyReservations ? 'default' : 'primary'" 
        @click="toggleView"
      >
        {{ showMyReservations ? '返回预约' : '我的预约' }}
      </el-button>
    </div>

    <!-- 预约主界面 -->
    <div class="main-content" v-if="!showMyReservations">
      <!-- 左侧筛选 -->
      <div class="filter-panel">
        <div class="filter-title">预约条件筛选</div>
        <el-form label-position="top">
          <el-form-item label="预约日期">
            <el-date-picker 
              v-model="filters.date" 
              type="date" 
              placeholder="选择日期" 
              value-format="YYYY-MM-DD"
              :disabled-date="disabledDate"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="容纳人数 (≥)">
            <el-input-number v-model="filters.capacity" :min="1" style="width: 100%" />
          </el-form-item>
          <el-form-item label="设备要求">
            <el-checkbox-group v-model="filters.devices" class="device-group">
              <el-checkbox label="多媒体" />
              <el-checkbox label="空调" />
              <el-checkbox label="投影仪" />
              <el-checkbox label="实验仪器" v-if="activeTab === 'lab'" />
              <el-checkbox label="电脑" v-if="activeTab === 'lab'" />
            </el-checkbox-group>
          </el-form-item>
        </el-form>
        <div class="filter-tip">
          <el-icon><Warning /></el-icon>
          <span>仅显示空闲且符合设备要求的资源</span>
        </div>
      </div>

      <!-- 右侧列表 -->
      <div class="list-panel">
        <el-table :data="filteredResources" style="width: 100%" height="100%">
          <el-table-column prop="name" label="资源名称" min-width="150" />
          <el-table-column prop="location" label="位置" width="150" />
          <el-table-column prop="capacity" label="容量" width="80" align="center" />
          <el-table-column label="设备配置" min-width="200">
            <template #default="{ row }">
              <el-tag v-for="dev in row.devices" :key="dev" size="small" style="margin-right: 5px" type="info">{{ dev }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="handleReserve(row)">预约</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 我的预约列表 -->
    <div class="my-reservations" v-else>
      <el-table :data="myReservationList" style="width: 100%" border>
        <el-table-column prop="resourceName" label="资源名称" width="180" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            {{ row.type === 'classroom' ? '教室' : '实验室' }}
          </template>
        </el-table-column>
        <el-table-column prop="date" label="预约日期" width="120" />
        <el-table-column label="预约时段" width="200">
          <template #default="{ row }">
            <div v-for="slot in row.timeSlots" :key="slot">{{ slot }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="purpose" label="用途" min-width="150" />
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)">{{ getStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button 
              v-if="row.status === 'pending' || row.status === 'approved'"
              type="danger" 
              link 
              size="small" 
              @click="handleCancel(row)"
            >
              取消预约
            </el-button>
            <el-tooltip 
              v-if="row.status === 'rejected'" 
              :content="row.reason" 
              placement="top"
            >
              <el-button type="info" link size="small">查看原因</el-button>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 预约弹窗 -->
    <el-dialog v-model="dialogVisible" title="资源预约申请" width="600px">
      <div v-if="currentResource" class="dialog-content">
        <div class="resource-info">
          <div class="info-item"><strong>资源：</strong>{{ currentResource.name }}</div>
          <div class="info-item"><strong>日期：</strong>{{ filters.date }}</div>
        </div>

        <div class="slot-selection">
          <div class="section-title">
            <span>选择时段</span>
            <el-checkbox @change="handleSelectAllSlots">全选</el-checkbox>
          </div>
          <div class="slots-grid">
            <div 
              v-for="slot in currentSlots" 
              :key="slot.id"
              class="slot-item"
              :class="{ 
                'disabled': !slot.available, 
                'selected': selectedSlotIds.includes(slot.id) 
              }"
              @click="slot.available && (selectedSlotIds.includes(slot.id) ? selectedSlotIds = selectedSlotIds.filter(id => id !== slot.id) : selectedSlotIds.push(slot.id))"
            >
              <div class="slot-name">{{ slot.name }}</div>
              <div class="slot-time">{{ slot.time }}</div>
              <div class="slot-status" v-if="!slot.available">已占用</div>
            </div>
          </div>
        </div>

        <el-form :model="reservationForm" label-width="80px" style="margin-top: 20px">
          <el-form-item label="预约用途" required>
            <el-input v-model="reservationForm.purpose" placeholder="请输入课程名称或活动用途" />
          </el-form-item>
          <el-form-item label="申请人">
            <el-input v-model="reservationForm.applicant" disabled />
          </el-form-item>
          <el-form-item label="联系电话" required>
            <el-input v-model="reservationForm.phone" placeholder="请输入联系电话" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitReservation" :loading="loading">提交申请</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.reservation-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 15px;
}
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  padding: 10px 20px;
  border-radius: 4px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
  height: 50px;
}
.type-tabs {
  flex: 1;
}
:deep(.el-tabs__header) {
  margin: 0;
}
.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.main-content {
  flex: 1;
  display: flex;
  gap: 15px;
  overflow: hidden;
}
.filter-panel {
  width: 280px;
  background: #fff;
  padding: 20px;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
}
.filter-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 20px;
  color: #303133;
}
.device-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.filter-tip {
  margin-top: auto;
  padding: 10px;
  background: #fdf6ec;
  color: #e6a23c;
  font-size: 12px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.list-panel {
  flex: 1;
  background: #fff;
  padding: 20px;
  border-radius: 4px;
  overflow: hidden;
}

.my-reservations {
  flex: 1;
  background: #fff;
  padding: 20px;
  border-radius: 4px;
  overflow: auto;
}

/* 弹窗样式 */
.resource-info {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}
.section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  font-weight: 600;
}
.slots-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.slot-item {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 10px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
}
.slot-item:hover {
  border-color: #52C41A; /* 教师端绿色 */
}
.slot-item.selected {
  background-color: #F0F9EB;
  border-color: #52C41A;
  color: #52C41A;
}
.slot-item.disabled {
  background-color: #f5f7fa;
  border-color: #e4e7ed;
  color: #c0c4cc;
  cursor: not-allowed;
}
.slot-name {
  font-weight: 600;
  font-size: 14px;
}
.slot-time {
  font-size: 12px;
  margin-top: 5px;
}
.slot-status {
  position: absolute;
  top: 0;
  right: 0;
  background: #909399;
  color: #fff;
  font-size: 10px;
  padding: 2px 4px;
  border-bottom-left-radius: 4px;
}
</style>
