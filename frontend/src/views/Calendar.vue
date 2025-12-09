<template>
  <div class="calendar-container">
    <div class="header">
      <h2>校历安排</h2>
      <div v-if="isAdmin" class="actions">
        <el-button type="primary" @click="handleAddEvent">添加事件</el-button>
        <el-upload
          class="upload-btn"
          action="http://localhost:8000/api/calendar/import"
          :headers="uploadHeaders"
          :show-file-list="false"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          accept=".xlsx,.xls"
        >
          <el-button type="success">导入 Excel</el-button>
        </el-upload>
      </div>
    </div>

    <el-calendar v-model="currentDate">
      <template #date-cell="{ data }">
        <div class="calendar-cell" @click.stop="handleDateClick(data)">
          <div class="date-num" :class="{ 'is-today': isToday(data.day) }">
            {{ data.day.split('-').slice(2).join('') }}
            <span v-if="isToday(data.day)" class="today-text">今天</span>
          </div>
          <div class="events">
            <div
              v-for="event in getEventsForDate(data.day)"
              :key="event.id"
              class="event-item"
              :class="getEventClass(event.type)"
              @click.stop="handleEventClick(event)"
            >
              {{ event.title }}
            </div>
          </div>
        </div>
      </template>
    </el-calendar>

    <!-- 事件编辑/添加弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'add' ? '添加校历事件' : '编辑校历事件'"
      width="500px"
    >
      <el-form :model="form" label-width="80px">
        <el-form-item label="事件名称">
          <el-input v-model="form.title" placeholder="请输入事件名称" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.type" placeholder="请选择类型">
            <el-option label="节假日" value="节假日" />
            <el-option label="考试" value="考试" />
            <el-option label="活动" value="活动" />
            <el-option label="教学" value="教学" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="地点">
          <el-input v-model="form.location" placeholder="请输入地点" />
        </el-form-item>
        <el-form-item label="关联班级">
          <el-input v-model="form.related_classes" placeholder="例如: 1班, 2班 (可选)" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button v-if="dialogType === 'edit'" type="danger" @click="handleDelete">删除</el-button>
          <el-button type="primary" @click="handleSubmit">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

interface CalendarEvent {
  id?: number
  title: string
  type: string
  start_date: string
  end_date: string
  location?: string
  related_classes?: string
  description?: string
}

const currentDate = ref(new Date())
const events = ref<CalendarEvent[]>([])
const dialogVisible = ref(false)
const dialogType = ref<'add' | 'edit'>('add')
const dateRange = ref<[string, string]>(['', ''])
const uploadHeaders = { Authorization: `Bearer ${localStorage.getItem('token')}` }

const form = ref<CalendarEvent>({
  title: '',
  type: '活动',
  start_date: '',
  end_date: '',
  location: '',
  related_classes: '',
  description: ''
})

// 判断当前用户是否为管理员
const isAdmin = computed(() => {
  const role = localStorage.getItem('role')
  return role === 'admin'
})

// 获取当月事件
const fetchEvents = async () => {
  try {
    const response = await axios.get('http://localhost:8000/api/calendar/events', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    events.value = response.data
  } catch (error) {
    console.error('获取校历事件失败', error)
    ElMessage.error('获取校历事件失败')
  }
}

// 获取指定日期的事件
const getEventsForDate = (date: string) => {
  return events.value.filter(event => {
    return date >= event.start_date && date <= event.end_date
  })
}

// 判断是否是今天
const isToday = (date: string) => {
  const today = new Date()
  const d = new Date(date)
  return d.getDate() === today.getDate() &&
         d.getMonth() === today.getMonth() &&
         d.getFullYear() === today.getFullYear()
}

// 事件样式
const getEventClass = (type: string) => {
  const map: Record<string, string> = {
    '节假日': 'event-holiday',
    '考试': 'event-exam',
    '活动': 'event-activity',
    '教学': 'event-teaching',
    '其他': 'event-other'
  }
  return map[type] || 'event-other'
}

// 点击日期
const handleDateClick = (data: { day: string }) => {
  if (isAdmin.value) {
    dialogType.value = 'add'
    form.value = {
      title: '',
      type: '活动',
      start_date: data.day,
      end_date: data.day,
      location: '',
      related_classes: '',
      description: ''
    }
    dateRange.value = [data.day, data.day]
    dialogVisible.value = true
  }
}

// 点击添加按钮
const handleAddEvent = () => {
  const todayStr = new Date().toISOString().split('T')[0]
  handleDateClick({ day: todayStr })
}

// 点击事件
const handleEventClick = (event: CalendarEvent) => {
  if (isAdmin.value) {
    dialogType.value = 'edit'
    form.value = { ...event }
    dateRange.value = [event.start_date, event.end_date]
    dialogVisible.value = true
  } else {
    // 普通用户查看详情
    ElMessageBox.alert(
      `
      <p><strong>时间:</strong> ${event.start_date} 至 ${event.end_date}</p>
      <p><strong>类型:</strong> ${event.type}</p>
      <p><strong>地点:</strong> ${event.location || '无'}</p>
      <p><strong>关联班级:</strong> ${event.related_classes || '无'}</p>
      <p><strong>备注:</strong> ${event.description || '无'}</p>
      `,
      event.title,
      { dangerouslyUseHTMLString: true }
    )
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!form.value.title) {
    ElMessage.warning('请输入事件名称')
    return
  }
  if (!dateRange.value || dateRange.value.length !== 2) {
    ElMessage.warning('请选择时间范围')
    return
  }

  form.value.start_date = dateRange.value[0]
  form.value.end_date = dateRange.value[1]

  try {
    const headers = { Authorization: `Bearer ${localStorage.getItem('token')}` }
    if (dialogType.value === 'add') {
      await axios.post('http://localhost:8000/api/calendar/events', form.value, { headers })
      ElMessage.success('添加成功')
    } else {
      await axios.put(`http://localhost:8000/api/calendar/events/${form.value.id}`, form.value, { headers })
      ElMessage.success('更新成功')
    }
    dialogVisible.value = false
    fetchEvents()
  } catch (error) {
    console.error('操作失败', error)
    ElMessage.error('操作失败')
  }
}

// 删除事件
const handleDelete = async () => {
  if (!form.value.id) return
  
  try {
    await ElMessageBox.confirm('确定要删除这个事件吗?', '提示', {
      type: 'warning'
    })
    
    await axios.delete(`http://localhost:8000/api/calendar/events/${form.value.id}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    ElMessage.success('删除成功')
    dialogVisible.value = false
    fetchEvents()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败', error)
      ElMessage.error('删除失败')
    }
  }
}

// 上传成功
const handleUploadSuccess = (response: any) => {
  ElMessage.success(response.message || '导入成功')
  fetchEvents()
}

// 上传失败
const handleUploadError = (error: any) => {
  ElMessage.error('导入失败: ' + (error.response?.data?.detail || '未知错误'))
}

onMounted(() => {
  fetchEvents()
})
</script>

<style scoped>
.calendar-container {
  padding: 20px;
  background-color: #fff;
  border-radius: 8px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.actions {
  display: flex;
  gap: 10px;
}

.upload-btn {
  display: inline-block;
}

.calendar-cell {
  height: 100%;
  padding: 4px;
  overflow: hidden;
}

.date-num {
  font-size: 14px;
  margin-bottom: 4px;
}

.date-num.is-today {
  color: #409eff;
  font-weight: bold;
}

.today-text {
  font-size: 12px;
  margin-left: 4px;
}

.events {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.event-item {
  font-size: 12px;
  padding: 2px 4px;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.event-holiday {
  background-color: #f56c6c; /* Red */
}

.event-exam {
  background-color: #e6a23c; /* Orange */
}

.event-activity {
  background-color: #67c23a; /* Green */
}

.event-teaching {
  background-color: #409eff; /* Blue */
}

.event-other {
  background-color: #909399; /* Grey */
}

/* 调整日历高度以适应屏幕 */
:deep(.el-calendar-table .el-calendar-day) {
  height: 100px;
}
</style>
