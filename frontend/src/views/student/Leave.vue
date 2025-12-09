<script setup lang="ts">
/**
 * 学生请假申请页面
 * 包含：申请表单、历史记录、撤回功能
 */
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, UploadFile } from 'element-plus'
import { Plus, Refresh, UploadFilled } from '@element-plus/icons-vue'
import axios from 'axios'

// --- 类型定义 ---
interface LeaveRecord {
  id: number
  course_id: number
  course_name: string
  teacher_id: number
  teacher_name: string
  type: string
  start_time: string
  end_time: string
  reason: string
  file_url?: string
  status: 'pending' | 'approved' | 'rejected' | 'recalled'
  opinion?: string
  create_time: string
}

interface CourseOption {
  id: number
  name: string
  teacher_name: string
}

// --- 状态管理 ---
const activeTab = ref('apply')
const leaveForm = reactive({
  course_id: undefined as number | undefined,
  type: '病假',
  dateRange: [] as string[],
  reason: '',
  file_url: ''
})

const courses = ref<CourseOption[]>([])
const historyLeaves = ref<LeaveRecord[]>([])
const loading = ref(false)
const submitting = ref(false)

const studentId = parseInt(localStorage.getItem('user_id') || '0')
const uploadHeaders = { Authorization: `Bearer ${localStorage.getItem('token')}` }

// --- 初始化 ---
onMounted(() => {
  loadCourses()
  loadHistory()
})

// 加载已选课程
const loadCourses = async () => {
  try {
    const res = await axios.get('http://localhost:8000/api/course/student/list', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    
    // Fetch teacher for each course
    const courseList = res.data
    const coursesWithTeacher = await Promise.all(courseList.map(async (c: any) => {
       try {
           const tRes = await axios.get(`http://localhost:8000/api/course/${c.id}/teacher`, {
              headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
           })
           return { id: c.id, name: c.name, teacher_name: tRes.data.name }
       } catch (e) {
           return { id: c.id, name: c.name, teacher_name: 'Unknown' }
       }
    }))
    courses.value = coursesWithTeacher
  } catch (error) {
    console.error('Failed to load courses', error)
    ElMessage.error('无法加载课程列表')
  }
}

// 加载历史记录
const loadHistory = async () => {
  loading.value = true
  try {
    // 调用 API
    const res = await axios.get('http://localhost:8000/api/leave/student/list', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    historyLeaves.value = res.data.items || res.data // handle pagination wrapper or list
  } catch (error) {
    console.error('Failed to load history', error)
    ElMessage.error('无法加载请假记录')
  } finally {
    loading.value = false
  }
}

// 提交申请
const submitApply = async () => {
  if (!leaveForm.course_id || !leaveForm.dateRange || leaveForm.dateRange.length !== 2 || !leaveForm.reason) {
    ElMessage.warning('请填写完整信息')
    return
  }
  
  const startTime = new Date(leaveForm.dateRange[0])
  const endTime = new Date(leaveForm.dateRange[1])
  
  // 校验时长 <= 7天
  const days = (endTime.getTime() - startTime.getTime()) / (1000 * 3600 * 24)
  if (days > 7) {
    ElMessage.error('请假时长不能超过7天')
    return
  }
  
  submitting.value = true
  try {
    await axios.post('http://localhost:8000/api/leave/apply', {
      course_id: leaveForm.course_id,
      type: leaveForm.type,
      start_time: startTime.toISOString(),
      end_time: endTime.toISOString(),
      reason: leaveForm.reason,
      file_url: leaveForm.file_url
    }, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    
    ElMessage.success('提交成功')
    resetForm()
    activeTab.value = 'history'
    loadHistory()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}

// 撤回申请
const recallApply = (id: number) => {
  ElMessageBox.confirm('确定要撤回这条申请吗？', '提示', {
    type: 'warning'
  }).then(async () => {
    try {
      await axios.post('http://localhost:8000/api/leave/recall', {
        leave_id: id
      }, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      })
      ElMessage.success('撤回成功')
      loadHistory()
    } catch (error) {
      ElMessage.error('撤回失败')
    }
  })
}

// 文件上传成功
const handleUploadSuccess = (response: any) => {
  leaveForm.file_url = response.url
  ElMessage.success('上传成功')
}

// 重置表单
const resetForm = () => {
  leaveForm.course_id = undefined
  leaveForm.type = '病假'
  leaveForm.dateRange = []
  leaveForm.reason = ''
  leaveForm.file_url = ''
}

// 获取状态样式
const getStatusTag = (status: string) => {
  const map: Record<string, string> = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger',
    recalled: 'info'
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    pending: '待审核',
    approved: '已通过',
    rejected: '已拒绝',
    recalled: '已撤回'
  }
  return map[status] || status
}

// 格式化时间
const formatTime = (iso: string) => {
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}
</script>

<template>
  <div class="leave-container">
    <el-tabs v-model="activeTab" class="leave-tabs">
      <!-- 申请请假 Tab -->
      <el-tab-pane label="我要请假" name="apply">
        <div class="apply-panel">
          <div class="panel-header">
            <h3>请假申请</h3>
            <p class="tips">说明：仅可向任课教师请假，单次时长不超过 7 天，每月累计不超过 14 天。</p>
          </div>
          
          <el-form :model="leaveForm" label-width="100px" class="leave-form">
            <el-form-item label="请假课程" required>
              <el-select v-model="leaveForm.course_id" placeholder="选择课程">
                <el-option 
                  v-for="c in courses" 
                  :key="c.id" 
                  :label="`${c.name} (${c.teacher_name})`" 
                  :value="c.id" 
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="请假类型" required>
              <el-radio-group v-model="leaveForm.type">
                <el-radio label="病假">病假</el-radio>
                <el-radio label="事假">事假</el-radio>
                <el-radio label="其他">其他</el-radio>
              </el-radio-group>
            </el-form-item>
            
            <el-form-item label="请假时间" required>
              <el-date-picker
                v-model="leaveForm.dateRange"
                type="datetimerange"
                range-separator="至"
                start-placeholder="开始时间"
                end-placeholder="结束时间"
                :disabled-date="(time) => time.getTime() < Date.now() - 8.64e7"
              />
            </el-form-item>
            
            <el-form-item label="请假理由" required>
              <el-input 
                v-model="leaveForm.reason" 
                type="textarea" 
                :rows="4" 
                placeholder="请输入详细的请假理由..."
              />
            </el-form-item>
            
            <el-form-item label="证明材料">
              <el-upload
                class="upload-demo"
                action="http://localhost:8000/api/leave/upload"
                :headers="uploadHeaders"
                :on-success="handleUploadSuccess"
                :limit="1"
              >
                <el-button type="primary" :icon="UploadFilled">点击上传</el-button>
                <template #tip>
                  <div class="el-upload__tip">支持 jpg/png/pdf 文件，不超过 5MB</div>
                </template>
              </el-upload>
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="submitApply" :loading="submitting">提交申请</el-button>
              <el-button @click="resetForm">重置</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>
      
      <!-- 我的请假 Tab -->
      <el-tab-pane label="我的请假" name="history">
        <div class="history-panel">
          <el-table :data="historyLeaves" v-loading="loading" style="width: 100%">
            <el-table-column prop="course_name" label="课程" width="150" />
            <el-table-column prop="teacher_name" label="审批教师" width="120" />
            <el-table-column prop="type" label="类型" width="80" />
            <el-table-column label="时间段" width="300">
              <template #default="{ row }">
                {{ formatTime(row.start_time) }} - {{ formatTime(row.end_time) }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusTag(row.status)">{{ getStatusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="opinion" label="审批意见" />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button 
                  v-if="row.status === 'pending'" 
                  type="danger" 
                  link 
                  size="small"
                  @click="recallApply(row.id)"
                >
                  撤回
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.leave-container {
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  min-height: calc(100vh - 120px);
}

.apply-panel {
  max-width: 800px;
  margin: 0 auto;
}

.panel-header {
  margin-bottom: 30px;
  border-bottom: 1px solid #EBEEF5;
  padding-bottom: 15px;
}

.panel-header h3 {
  margin: 0 0 10px 0;
  color: #303133;
}

.tips {
  color: #909399;
  font-size: 14px;
  margin: 0;
}

.leave-form {
  margin-top: 20px;
}
</style>
