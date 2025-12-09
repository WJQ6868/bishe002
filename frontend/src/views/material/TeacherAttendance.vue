<script setup lang="ts">
/**
 * 教师上课点名页面 (Material Design)
 * 包含：二维码点名、手动点名、签到统计
 */
import { ref, reactive, onMounted, computed } from 'vue'
import { useTheme } from 'vuetify'
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
const search = ref('')

const snackbar = reactive({
  show: false,
  text: '',
  color: 'success'
})

const showSnackbar = (text: string, color: 'success' | 'error' | 'warning' = 'success') => {
  snackbar.text = text
  snackbar.color = color
  snackbar.show = true
}

// 二维码相关
const qrCodeUrl = ref('')
const qrCodeExpire = ref<Date | null>(null)
const qrCodeTimer = ref<any>(null)
const isQrCodeActive = ref(false)
const timeLeft = ref('')

// 统计数据
const stats = computed(() => {
  const total = students.value.length
  const present = students.value.filter(s => s.status === '已签到').length
  const late = students.value.filter(s => s.status === '迟到').length
  const absent = students.value.filter(s => s.status === '未到').length
  const leave = students.value.filter(s => s.status === '请假').length
  return [
    { label: '应到', value: total, color: 'primary', icon: 'mdi-account-group' },
    { label: '实到', value: present, color: 'success', icon: 'mdi-account-check' },
    { label: '迟到', value: late, color: 'warning', icon: 'mdi-clock-alert' },
    { label: '未到', value: absent, color: 'grey', icon: 'mdi-account-off' },
    { label: '请假', value: leave, color: 'purple', icon: 'mdi-account-minus' }
  ]
})

// --- 表格配置 ---
const headers = [
  { title: '学号', key: 'student_id', align: 'start' },
  { title: '姓名', key: 'name', align: 'start' },
  { title: '状态', key: 'status', align: 'center' },
  { title: '签到时间', key: 'sign_time', align: 'center' },
  { title: '操作', key: 'actions', align: 'center', sortable: false }
]

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
    
    // 模拟实时签到效果
    simulateSign()
    
  } catch (error) {
    showSnackbar('生成二维码失败，请重试', 'error')
  }
}

// 倒计时
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
}

// 获取状态颜色
const getStatusColor = (status: string) => {
  const map: Record<string, string> = {
    '已签到': '#4CAF50', // signed
    '迟到': '#FF9800',   // late
    '未到': '#9E9E9E',   // unSigned
    '请假': '#9C27B0'    // leave
  }
  return map[status] || 'grey'
}

const getStatusIcon = (status: string) => {
    const map: Record<string, string> = {
    '已签到': 'mdi-check-circle',
    '迟到': 'mdi-clock-alert',
    '未到': 'mdi-close-circle',
    '请假': 'mdi-minus-circle'
  }
  return map[status] || 'mdi-help-circle'
}

// 导出签到表
const exportTable = () => {
  // 模拟导出
  const a = document.createElement('a')
  a.href = '#'
  a.download = '签到表.xlsx'
  a.click()
}
</script>

<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <div class="d-flex align-center mb-4">
          <h2 class="text-h5 font-weight-bold mr-4">上课点名</h2>
          <v-select
            v-model="currentCourseId"
            :items="courses"
            item-title="name"
            item-value="id"
            label="当前课程"
            variant="outlined"
            density="compact"
            hide-details
            style="max-width: 200px"
            prepend-inner-icon="mdi-book-open-variant"
            @update:model-value="loadStudents"
          ></v-select>
        </div>
      </v-col>
    </v-row>

    <!-- 统计卡片 -->
    <v-row class="mb-4">
      <v-col v-for="stat in stats" :key="stat.label" cols="12" sm="6" md="2">
        <v-card :color="stat.color" variant="tonal" class="text-center py-2">
          <v-icon :icon="stat.icon" size="large" class="mb-1"></v-icon>
          <div class="text-subtitle-2">{{ stat.label }}</div>
          <div class="text-h6 font-weight-bold">{{ stat.value }}</div>
        </v-card>
      </v-col>
    </v-row>

    <v-card elevation="2" class="rounded-lg">
      <v-tabs v-model="activeTab" color="primary">
        <v-tab value="qrcode">
          <v-icon start>mdi-qrcode-scan</v-icon>
          二维码点名
        </v-tab>
        <v-tab value="manual">
          <v-icon start>mdi-playlist-check</v-icon>
          手动点名
        </v-tab>
      </v-tabs>

      <v-window v-model="activeTab">
        <!-- 二维码点名 -->
        <v-window-item value="qrcode">
          <v-card-text class="text-center py-8">
            <div v-if="!isQrCodeActive" class="d-flex flex-column align-center">
              <v-icon size="100" color="grey-lighten-1" class="mb-4">mdi-qrcode</v-icon>
              <v-btn
                color="primary"
                size="x-large"
                prepend-icon="mdi-play"
                @click="generateQrCode"
                :disabled="!currentCourseId"
              >
                生成签到二维码
              </v-btn>
              <p class="text-grey mt-4">有效期 5 分钟，点击生成后学生即可扫码签到</p>
            </div>
            
            <div v-else class="d-flex flex-column align-center">
              <div class="text-h4 font-weight-bold primary--text mb-2">{{ timeLeft }}</div>
              <div class="text-subtitle-1 mb-4">请使用手机扫描下方二维码</div>
              
              <v-img
                :src="qrCodeUrl"
                width="300"
                height="300"
                class="mx-auto mb-4 elevation-2 rounded"
              ></v-img>
              
              <v-btn color="error" variant="text" @click="isQrCodeActive = false">
                停止点名
              </v-btn>
            </div>
          </v-card-text>
        </v-window-item>

        <!-- 手动点名 -->
        <v-window-item value="manual">
          <v-card-title class="d-flex align-center">
            <v-text-field
              v-model="search"
              prepend-inner-icon="mdi-magnify"
              label="搜索学生"
              single-line
              hide-details
              variant="outlined"
              density="compact"
              class="mr-4"
              style="max-width: 300px"
            ></v-text-field>
            <v-spacer></v-spacer>
            <v-btn
              color="success"
              prepend-icon="mdi-microsoft-excel"
              variant="outlined"
              @click="exportTable"
            >
              导出签到表
            </v-btn>
          </v-card-title>

          <v-data-table
            :headers="headers"
            :items="students"
            :search="search"
            :loading="loading"
            hover
          >
            <template v-slot:item.status="{ item }">
              <v-menu location="bottom center">
                <template v-slot:activator="{ props }">
                  <v-chip
                    v-bind="props"
                    :color="getStatusColor(item.status)"
                    label
                    size="small"
                    class="cursor-pointer"
                  >
                    <v-icon start size="small">{{ getStatusIcon(item.status) }}</v-icon>
                    {{ item.status }}
                    <v-icon end size="small">mdi-chevron-down</v-icon>
                  </v-chip>
                </template>
                <v-list density="compact">
                  <v-list-item
                    v-for="status in ['已签到', '迟到', '未到', '请假']"
                    :key="status"
                    :value="status"
                    @click="changeStatus(item, status as any)"
                  >
                    <template v-slot:prepend>
                      <v-icon :color="getStatusColor(status)" size="small">{{ getStatusIcon(status) }}</v-icon>
                    </template>
                    <v-list-item-title>{{ status }}</v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-menu>
            </template>
            
            <template v-slot:item.actions="{ item }">
              <v-btn
                icon="mdi-pencil"
                size="small"
                variant="text"
                color="primary"
                title="备注"
              ></v-btn>
            </template>
          </v-data-table>
        </v-window-item>
      </v-window>
    </v-card>

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
  </v-container>
</template>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}
</style>
