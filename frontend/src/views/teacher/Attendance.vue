<script setup lang="ts">
/**
 * 教师上课点名页面
 * 包含：二维码点名、手动点名、签到统计
 */
import { ref, reactive, onMounted, computed, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import QRCode from 'qrcode'
import axios from 'axios'

// --- 类型定义 ---
interface Student {
  id: number
  name: string
  student_id: string // 学号
  status: '已签到' | '迟到' | '未到' | '请假'
  sign_time?: string
  remark?: string
}

interface CourseOption {
  id: number
  name: string
}

// --- 状态管理 ---
const activeTab = ref('qrcode')
const currentCourseId = ref<number | undefined>(undefined)
const courses = ref<CourseOption[]>([])
const students = ref<Student[]>([])
const loading = ref(false)

// 二维码相关
const qrCodeUrl = ref('')
const qrCodeExpire = ref<Date | null>(null)
const qrCodeTimer = ref<any>(null)
const isQrCodeActive = ref(false)

// 统计数据
const stats = computed(() => {
  const total = students.value.length
  const present = students.value.filter(s => s.status === '已签到').length
  const late = students.value.filter(s => s.status === '迟到').length
  const absent = students.value.filter(s => s.status === '未到').length
  const leave = students.value.filter(s => s.status === '请假').length
  return { total, present, late, absent, leave }
})

// --- 初始化 ---
onMounted(() => {
  loadCourses()
})

// 加载课程
const loadCourses = async () => {
  // 模拟数据
  courses.value = [
    { id: 1, name: '高等数学' },
    { id: 2, name: 'Python程序设计' }
  ]
  if (courses.value.length > 0) {
    currentCourseId.value = courses.value[0].id
    loadStudents()
  }
}

// 加载学生列表 (模拟)
const loadStudents = () => {
  loading.value = true
  // 模拟生成 30 名学生
  const mockStudents: Student[] = []
  for (let i = 1; i <= 30; i++) {
    mockStudents.push({
      id: 2000 + i,
      name: `学生${i}`,
      student_id: `20230${i < 10 ? '0' + i : i}`,
      status: '未到'
    })
  }
  students.value = mockStudents
  loading.value = false
}

// 生成二维码
const generateQrCode = async () => {
  if (!currentCourseId.value) return
  
  try {
    const res = await axios.post('http://localhost:8000/api/attendance/create', {
      course_id: currentCourseId.value,
      duration: 5 // 5分钟有效期
    }, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    
    const code = res.data.code
    qrCodeExpire.value = new Date(res.data.expire_time)
    
    // 生成二维码图片
    qrCodeUrl.value = await QRCode.toDataURL(JSON.stringify({
      code: code,
      type: 'attendance'
    }))
    
    isQrCodeActive.value = true
    startTimer()
    ElMessage.success('签到二维码已生成')
    
    // 模拟实时签到效果
    simulateSign()
    
  } catch (error) {
    ElMessage.error('生成二维码失败')
  }
}

// 倒计时
const timeLeft = ref('')
const startTimer = () => {
  if (qrCodeTimer.value) clearInterval(qrCodeTimer.value)
  
  qrCodeTimer.value = setInterval(() => {
    if (!qrCodeExpire.value) return
    
    const now = new Date()
    const diff = qrCodeExpire.value.getTime() - now.getTime()
    
    if (diff <= 0) {
      timeLeft.value = '已过期'
      isQrCodeActive.value = false
      clearInterval(qrCodeTimer.value)
    } else {
      const m = Math.floor(diff / 60000)
      const s = Math.floor((diff % 60000) / 1000)
      timeLeft.value = `${m}:${s < 10 ? '0' + s : s}`
    }
  }, 1000)
}

// 模拟签到 (演示用)
const simulateSign = () => {
  let count = 0
  const interval = setInterval(() => {
    if (count >= 25 || !isQrCodeActive.value) {
      clearInterval(interval)
      return
    }
    
    // 随机选一个未到的学生签到
    const absentStudents = students.value.filter(s => s.status === '未到')
    if (absentStudents.length > 0) {
      const randomStudent = absentStudents[Math.floor(Math.random() * absentStudents.length)]
      randomStudent.status = '已签到'
      randomStudent.sign_time = new Date().toLocaleTimeString()
    }
    count++
  }, 2000) // 每2秒签到一个
}

// 手动修改状态
const changeStatus = (student: Student, status: Student['status']) => {
  student.status = status
  if (status === '已签到') {
    student.sign_time = new Date().toLocaleTimeString()
  } else {
    student.sign_time = undefined
  }
  // 实际应调用 API 更新
}

// 导出签到表
const exportTable = () => {
  ElMessage.success('正在导出签到表...')
}
</script>

<template>
  <div class="attendance-container">
    <div class="header-bar">
      <div class="course-select">
        <span>当前课程：</span>
        <el-select v-model="currentCourseId" @change="loadStudents" style="width: 200px">
          <el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </div>
      
      <el-radio-group v-model="activeTab">
        <el-radio-button label="qrcode">二维码点名</el-radio-button>
        <el-radio-button label="manual">手动点名</el-radio-button>
      </el-radio-group>
    </div>
    
    <!-- 二维码点名 -->
    <div v-if="activeTab === 'qrcode'" class="qrcode-panel">
      <div class="qr-area">
        <div v-if="!isQrCodeActive" class="qr-placeholder">
          <el-button type="primary" size="large" @click="generateQrCode">开始点名</el-button>
          <p>生成二维码，学生扫码签到</p>
        </div>
        <div v-else class="qr-content">
          <img :src="qrCodeUrl" alt="签到二维码" />
          <div class="timer">
            剩余时间：<span>{{ timeLeft }}</span>
          </div>
          <p class="status-text">正在签到中...</p>
        </div>
      </div>
      
      <div class="realtime-stats">
        <h4>实时签到数据</h4>
        <div class="stat-cards">
          <div class="stat-card present">
            <div class="num">{{ stats.present }}</div>
            <div class="label">已签到</div>
          </div>
          <div class="stat-card absent">
            <div class="num">{{ stats.absent }}</div>
            <div class="label">未签到</div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 手动点名 -->
    <div v-if="activeTab === 'manual'" class="manual-panel">
      <div class="toolbar">
        <el-input placeholder="搜索姓名/学号" style="width: 200px" prefix-icon="Search" />
        <el-button type="success" @click="exportTable">导出签到表</el-button>
      </div>
      
      <el-table :data="students" height="500" v-loading="loading">
        <el-table-column prop="student_id" label="学号" width="120" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column label="状态" width="300">
          <template #default="{ row }">
            <el-radio-group v-model="row.status" size="small" @change="(val) => changeStatus(row, val)">
              <el-radio-button label="已签到" />
              <el-radio-button label="迟到" />
              <el-radio-button label="请假" />
              <el-radio-button label="未到" />
            </el-radio-group>
          </template>
        </el-table-column>
        <el-table-column prop="sign_time" label="签到时间" width="150" />
        <el-table-column label="备注">
          <template #default="{ row }">
            <el-input v-model="row.remark" size="small" placeholder="添加备注" />
          </template>
        </el-table-column>
      </el-table>
    </div>
    
    <!-- 底部统计 -->
    <div class="footer-stats">
      <span>应到：{{ stats.total }} 人</span>
      <span class="success">实到：{{ stats.present }} 人</span>
      <span class="warning">迟到：{{ stats.late }} 人</span>
      <span class="info">请假：{{ stats.leave }} 人</span>
      <span class="danger">缺勤：{{ stats.absent }} 人</span>
    </div>
  </div>
</template>

<style scoped>
.attendance-container {
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  min-height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
}

.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #EBEEF5;
}

.qrcode-panel {
  display: flex;
  justify-content: center;
  gap: 50px;
  padding: 40px 0;
}

.qr-area {
  text-align: center;
}

.qr-placeholder {
  width: 300px;
  height: 300px;
  background: #F5F7FA;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  border-radius: 8px;
  color: #909399;
}

.qr-content img {
  width: 300px;
  height: 300px;
}

.timer {
  font-size: 24px;
  font-weight: bold;
  color: #409EFF;
  margin: 10px 0;
}

.stat-cards {
  display: flex;
  gap: 20px;
  margin-top: 20px;
}

.stat-card {
  width: 120px;
  height: 120px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #fff;
}

.stat-card.present { background: #67C23A; }
.stat-card.absent { background: #F56C6C; }

.stat-card .num { font-size: 36px; font-weight: bold; }
.stat-card .label { font-size: 14px; opacity: 0.9; }

.manual-panel {
  flex: 1;
}

.toolbar {
  margin-bottom: 15px;
  display: flex;
  justify-content: space-between;
}

.footer-stats {
  margin-top: auto;
  padding-top: 20px;
  border-top: 1px solid #EBEEF5;
  display: flex;
  gap: 30px;
  font-size: 16px;
}

.success { color: #67C23A; }
.warning { color: #E6A23C; }
.danger { color: #F56C6C; }
.info { color: #909399; }
</style>
