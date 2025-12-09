<script setup lang="ts">
/**
 * 教师工作安排与调课页面
 * 包含：工作日历、调课申请
 */
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

// --- 类型定义 ---
interface WorkSchedule {
  id: number
  time: string
  content: string
  type: '上课' | '开会' | '值班' | '其他'
  remark?: string
}

interface CourseOption {
  id: number
  name: string
}

// --- 状态管理 ---
const activeTab = ref('calendar')
const currentDate = ref(new Date())
const schedules = ref<WorkSchedule[]>([])
const loading = ref(false)
const courses = ref<CourseOption[]>([])

// 调课申请表单
const adjustForm = reactive({
  course_id: undefined as number | undefined,
  old_time: '',
  new_time: '',
  old_classroom: '',
  new_classroom: '',
  reason: ''
})

// --- 初始化 ---
onMounted(() => {
  loadSchedules()
  loadCourses()
})

const loadSchedules = async () => {
  loading.value = true
  try {
    const res = await axios.get('http://localhost:8000/api/work/schedule', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    schedules.value = res.data
  } catch (error) {
    // 模拟数据
    schedules.value = [
      {
        id: 1,
        time: new Date().toISOString(),
        content: '高等数学 (1-2节)',
        type: '上课',
        remark: '教三-201'
      },
      {
        id: 2,
        time: new Date(new Date().getTime() + 86400000).toISOString(),
        content: '教研室会议',
        type: '开会',
        remark: '会议室A'
      }
    ]
  } finally {
    loading.value = false
  }
}

const loadCourses = async () => {
  courses.value = [
    { id: 1, name: '高等数学' },
    { id: 2, name: 'Python程序设计' }
  ]
}

// 提交调课申请
const submitAdjust = async () => {
  if (!adjustForm.course_id || !adjustForm.old_time || !adjustForm.new_time || !adjustForm.reason) {
    ElMessage.warning('请填写完整信息')
    return
  }
  
  try {
    await axios.post('http://localhost:8000/api/work/adjust/apply', adjustForm, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    ElMessage.success('申请提交成功，等待审核')
    // 重置表单
    adjustForm.reason = ''
  } catch (error) {
    ElMessage.error('申请失败')
  }
}

// 获取某一天的日程
const getDaySchedules = (date: Date) => {
  const dateStr = date.toISOString().split('T')[0]
  return schedules.value.filter(s => s.time.startsWith(dateStr))
}

const getScheduleTypeTag = (type: string) => {
  const map: Record<string, string> = {
    '上课': 'primary',
    '开会': 'warning',
    '值班': 'success',
    '其他': 'info'
  }
  return map[type] || 'info'
}

// 格式化时间
const formatTime = (iso: string) => {
  return new Date(iso).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="work-container">
    <div class="header-actions">
      <el-radio-group v-model="activeTab" style="margin-bottom: 20px">
        <el-radio-button label="calendar">工作日历</el-radio-button>
        <el-radio-button label="adjust">调课申请</el-radio-button>
      </el-radio-group>
    </div>
    
    <!-- 工作日历 -->
    <div v-if="activeTab === 'calendar'" class="calendar-panel">
      <el-calendar v-model="currentDate">
        <template #date-cell="{ data }">
          <div class="date-cell-content">
            <p :class="{ 'is-today': data.isSelected }">
              {{ data.day.split('-').slice(1).join('-') }}
              {{ data.isSelected ? '✔️' : '' }}
            </p>
            <div class="schedule-list">
              <div 
                v-for="s in getDaySchedules(data.date)" 
                :key="s.id" 
                class="schedule-item"
              >
                <el-tag size="small" :type="getScheduleTypeTag(s.type)">{{ s.type }}</el-tag>
                <span class="schedule-content">{{ s.content }}</span>
              </div>
            </div>
          </div>
        </template>
      </el-calendar>
    </div>
    
    <!-- 调课申请 -->
    <div v-if="activeTab === 'adjust'" class="adjust-panel">
      <div class="form-card">
        <h3>调课申请单</h3>
        <el-form :model="adjustForm" label-width="100px">
          <el-form-item label="调课课程" required>
            <el-select v-model="adjustForm.course_id" placeholder="选择课程">
              <el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
          </el-form-item>
          
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="原上课时间" required>
                <el-date-picker
                  v-model="adjustForm.old_time"
                  type="datetime"
                  placeholder="选择原时间"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="原教室">
                <el-input v-model="adjustForm.old_classroom" placeholder="选填" />
              </el-form-item>
            </el-col>
          </el-row>
          
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="拟调整时间" required>
                <el-date-picker
                  v-model="adjustForm.new_time"
                  type="datetime"
                  placeholder="选择新时间"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="拟调整教室">
                <el-input v-model="adjustForm.new_classroom" placeholder="选填" />
              </el-form-item>
            </el-col>
          </el-row>
          
          <el-form-item label="调课理由" required>
            <el-input 
              v-model="adjustForm.reason" 
              type="textarea" 
              :rows="4" 
              placeholder="请输入详细理由..."
            />
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" @click="submitAdjust">提交申请</el-button>
            <el-button @click="activeTab = 'calendar'">取消</el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.work-container {
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  min-height: calc(100vh - 120px);
}

.date-cell-content {
  height: 100%;
  overflow: hidden;
}

.schedule-list {
  margin-top: 5px;
  font-size: 12px;
}

.schedule-item {
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.schedule-content {
  margin-left: 4px;
  color: #606266;
}

.adjust-panel {
  display: flex;
  justify-content: center;
  padding-top: 20px;
}

.form-card {
  width: 600px;
  padding: 30px;
  border: 1px solid #EBEEF5;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.form-card h3 {
  text-align: center;
  margin-bottom: 30px;
  color: #303133;
}
</style>
