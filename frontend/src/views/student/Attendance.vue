<script setup lang="ts">
/**
 * 学生上课签到页面
 * 包含：输入签到码、签到记录
 */
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Aim } from '@element-plus/icons-vue'
import axios from 'axios'

// --- 类型定义 ---
interface AttendanceRecord {
  id: number
  course_id: number
  course_name: string
  status: string
  sign_time: string
  create_time: string
}

// --- 状态管理 ---
const signCode = ref('')
const signing = ref(false)
const historyRecords = ref<AttendanceRecord[]>([])
const loading = ref(false)

// --- 初始化 ---
onMounted(() => {
  loadHistory()
})

// 提交签到
const submitSign = async () => {
  if (!signCode.value) {
    ElMessage.warning('请输入签到码')
    return
  }
  
  signing.value = true
  try {
    const res = await axios.post('/attendance/sign', {
      code: signCode.value,
      student_id: 0, // 后端会从 token 获取
      location: 'classroom' // 模拟定位
    }, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    
    if (res.data.message === 'Sign in success') {
      ElMessage.success('签到成功！')
      signCode.value = ''
      loadHistory()
    } else {
      ElMessage.warning(res.data.message)
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '签到失败')
  } finally {
    signing.value = false
  }
}

// 加载历史记录
const loadHistory = async () => {
  loading.value = true
  try {
    // 模拟数据：实际应调用 API 获取学生签到记录
    // 这里简单展示几条
    historyRecords.value = [
      {
        id: 1,
        course_id: 1,
        course_name: '高等数学',
        status: '已签到',
        sign_time: '2023-12-05T08:05:00',
        create_time: '2023-12-05T08:00:00'
      },
      {
        id: 2,
        course_id: 2,
        course_name: 'Python程序设计',
        status: '迟到',
        sign_time: '2023-12-04T10:15:00',
        create_time: '2023-12-04T10:00:00'
      }
    ]
  } finally {
    loading.value = false
  }
}

// 格式化时间
const formatTime = (iso: string) => {
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

const getStatusTag = (status: string) => {
  const map: Record<string, string> = {
    '已签到': 'success',
    '迟到': 'warning',
    '未到': 'danger',
    '请假': 'info'
  }
  return map[status] || 'info'
}
</script>

<template>
  <div class="attendance-container">
    <div class="sign-panel">
      <div class="sign-box">
        <div class="icon-box">
          <el-icon :size="60" color="#409EFF"><Aim /></el-icon>
        </div>
        <h3>上课签到</h3>
        <p class="tips">请输入教师提供的签到码完成签到</p>
        
        <div class="input-area">
          <el-input 
            v-model="signCode" 
            placeholder="请输入签到码" 
            size="large"
            style="margin-bottom: 20px"
          />
          <el-button 
            type="primary" 
            size="large" 
            style="width: 100%" 
            @click="submitSign"
            :loading="signing"
          >
            立即签到
          </el-button>
        </div>
      </div>
    </div>
    
    <div class="history-panel">
      <h4>最近签到记录</h4>
      <el-table :data="historyRecords" v-loading="loading" style="width: 100%">
        <el-table-column prop="course_name" label="课程" />
        <el-table-column label="签到时间" width="200">
          <template #default="{ row }">
            {{ formatTime(row.sign_time) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTag(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
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
  gap: 40px;
}

.sign-panel {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #F5F7FA;
  border-radius: 8px;
}

.sign-box {
  width: 300px;
  text-align: center;
  background: #fff;
  padding: 40px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.icon-box {
  margin-bottom: 20px;
}

.tips {
  color: #909399;
  margin-bottom: 30px;
}

.history-panel {
  flex: 1;
  padding: 20px;
}

.history-panel h4 {
  margin-top: 0;
  margin-bottom: 20px;
  padding-left: 10px;
  border-left: 4px solid #409EFF;
}
</style>
