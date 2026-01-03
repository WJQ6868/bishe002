<template>
  <div class="calendar-container">
    <div class="header">
      <div class="title-wrap">
        <h2>校历安排</h2>
        <div class="title-sub">支持月历/年历查看</div>
      </div>

      <div class="actions">
        <el-radio-group v-model="viewMode" class="view-switch" size="small">
          <el-radio-button label="month">月历</el-radio-button>
          <el-radio-button label="year">年历</el-radio-button>
        </el-radio-group>

        <template v-if="viewMode === 'year'">
          <el-button @click="prevYear">上一年</el-button>
          <el-tag type="info" effect="plain">{{ currentYear }} 年</el-tag>
          <el-button @click="nextYear">下一年</el-button>
        </template>

        <template v-if="isAdmin">
          <el-button type="primary" @click="handleAddEvent">添加事件</el-button>
          <el-upload
            class="upload-btn"
            action="/api/calendar/import"
            :headers="uploadHeaders"
            :show-file-list="false"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            accept=".xlsx,.xls"
          >
            <el-button type="success">导入表格</el-button>
          </el-upload>
        </template>
      </div>
    </div>

    <!-- 月历视图 -->
    <el-calendar v-if="viewMode === 'month'" v-model="currentDate">
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

    <!-- 年历视图 -->
    <div v-else class="year-view">
      <div class="year-grid">
        <div v-for="m in 12" :key="m" class="month-card">
          <div class="month-header">
            <div class="month-title">{{ getMonthLabel(m - 1) }}</div>
            <div class="month-meta">{{ currentYear }} 年</div>
          </div>

          <div class="mini-weekdays">
            <div v-for="w in weekLabels" :key="w" class="mini-weekday">{{ w }}</div>
          </div>

          <div class="mini-days">
            <div
              v-for="d in getMonthGrid(currentYear, m - 1)"
              :key="d.date"
              class="mini-day"
              :class="{
                'is-out': !d.isCurrentMonth,
                'is-today': d.isToday,
                'has-event': d.eventCount > 0
              }"
              @click.stop="handleYearDayClick(d.date)"
            >
              <span class="mini-day-num">{{ d.day }}</span>
              <span v-if="d.eventCount > 0" class="mini-dot"></span>
            </div>
          </div>
        </div>
      </div>
    </div>

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
const viewMode = ref<'month' | 'year'>('month')

const currentYear = computed(() => currentDate.value.getFullYear())
const weekLabels = ['一', '二', '三', '四', '五', '六', '日']

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

const prevYear = () => {
  currentDate.value = new Date(currentYear.value - 1, currentDate.value.getMonth(), 1)
}

const nextYear = () => {
  currentDate.value = new Date(currentYear.value + 1, currentDate.value.getMonth(), 1)
}

const getMonthLabel = (monthIndex: number) => {
  // 1月 ~ 12月
  return `${monthIndex + 1}月`
}

const pad2 = (n: number) => String(n).padStart(2, '0')

const formatYmd = (date: Date) => {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`
}

const getMonthGrid = (year: number, monthIndex: number) => {
  // 生成 6 行 * 7 列（42格）的月份网格；周一作为第一列
  const first = new Date(year, monthIndex, 1)
  const last = new Date(year, monthIndex + 1, 0)
  const firstWeekdayMonBased = (first.getDay() + 6) % 7 // Mon=0..Sun=6
  const start = new Date(year, monthIndex, 1 - firstWeekdayMonBased)

  const todayStr = formatYmd(new Date())
  const out: Array<{ date: string; day: number; isCurrentMonth: boolean; isToday: boolean; eventCount: number }> = []
  for (let i = 0; i < 42; i++) {
    const d = new Date(start)
    d.setDate(start.getDate() + i)
    const dateStr = formatYmd(d)
    const isCurrent = d.getMonth() === monthIndex
    const eventCount = getEventsForDate(dateStr).length
    out.push({
      date: dateStr,
      day: d.getDate(),
      isCurrentMonth: isCurrent,
      isToday: dateStr === todayStr,
      eventCount
    })
  }
  return out
}

const handleYearDayClick = (dateStr: string) => {
  if (isAdmin.value) {
    handleDateClick({ day: dateStr })
    return
  }
  const dayEvents = getEventsForDate(dateStr)
  if (dayEvents.length === 0) {
    ElMessage.info('当天暂无事件')
    return
  }
  if (dayEvents.length === 1) {
    handleEventClick(dayEvents[0])
    return
  }
  const list = dayEvents
    .map(e => `<li style="margin: 6px 0;">
      <span style="display:inline-block;min-width:56px;color:var(--el-text-color-secondary);">${e.type}</span>
      <span style="color:var(--el-text-color-primary);">${e.title}</span>
    </li>`)
    .join('')
  ElMessageBox.alert(
    `<div style="padding: 4px 0;">
      <div style="margin-bottom: 8px;color:var(--el-text-color-secondary);">${dateStr}</div>
      <ul style="padding-left: 18px;margin:0;">${list}</ul>
    </div>`,
    '当天事件',
    { dangerouslyUseHTMLString: true }
  )
}

// 获取当月事件
const fetchEvents = async () => {
  try {
    const response = await axios.get('/calendar/events', {
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
      <p><strong>时间：</strong> ${event.start_date} 至 ${event.end_date}</p>
      <p><strong>类型：</strong> ${event.type}</p>
      <p><strong>地点：</strong> ${event.location || '无'}</p>
      <p><strong>关联班级：</strong> ${event.related_classes || '无'}</p>
      <p><strong>备注：</strong> ${event.description || '无'}</p>
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
      await axios.post('/calendar/events', form.value, { headers })
      ElMessage.success('添加成功')
    } else {
      await axios.put(`/calendar/events/${form.value.id}`, form.value, { headers })
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
    await ElMessageBox.confirm('确定要删除这个事件吗？', '提示', {
      type: 'warning'
    })
    
    await axios.delete(`/calendar/events/${form.value.id}`, {
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
  ElMessage.error('导入失败：' + (error.response?.data?.detail || '未知错误'))
}

onMounted(() => {
  fetchEvents()
})
</script>

<style scoped>
.calendar-container {
  padding: 20px;
  background-color: var(--card-bg);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  border: 1px solid var(--border-color);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  min-height: 100%;
  padding-bottom: 28px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 14px 14px;
  border-radius: 12px;
  background: rgba(0, 242, 254, 0.05);
  border: 1px solid var(--border-color);
}

.title-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title-sub {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.view-switch {
  margin-right: 6px;
}

.header h2 {
  margin: 0;
  font-size: 22px;
  letter-spacing: 0.2px;
  color: var(--el-text-color-primary);
}

.actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.upload-btn {
  display: inline-block;
}

.year-view {
  width: 100%;
}

.year-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

@media (max-width: 1200px) {
  .year-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .year-grid {
    grid-template-columns: 1fr;
  }
}

.month-card {
  background: var(--card-bg);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  padding: 12px;
}

.month-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 2px 2px 10px;
}

.month-title {
  font-weight: 800;
  color: var(--el-text-color-primary);
}

.month-meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.mini-weekdays {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 4px;
  padding: 6px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
}

.mini-weekday {
  text-align: center;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-weight: 600;
}

.mini-days {
  margin-top: 8px;
  padding: 6px;
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 4px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
}

.mini-day {
  position: relative;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  cursor: pointer;
  color: var(--el-text-color-primary);
  background: transparent;
  border: 1px solid transparent;
  transition: transform 0.15s ease, box-shadow 0.15s ease, background-color 0.15s ease;
  user-select: none;
}

.mini-day:hover {
  transform: translateY(-1px);
  box-shadow: var(--el-box-shadow-light);
  background: var(--el-fill-color-light);
}

.mini-day.is-out {
  color: var(--el-text-color-secondary);
  opacity: 0.55;
}

.mini-day.is-today {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-weight: 700;
}

.mini-day.has-event {
  border-color: var(--el-color-primary-light-7);
}

.mini-day-num {
  font-size: 12px;
}

.mini-dot {
  position: absolute;
  bottom: 4px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--el-color-primary);
  box-shadow: 0 0 0 2px var(--el-bg-color-overlay);
}

.calendar-cell {
  height: 100%;
  padding: 8px;
  overflow: hidden;
  border-radius: 10px;
  transition: background-color 0.2s ease, box-shadow 0.2s ease;
}

.calendar-cell:hover {
  background: var(--el-fill-color-light);
  box-shadow: inset 0 0 0 1px var(--el-border-color-lighter);
}

.date-num {
  font-size: 14px;
  margin-bottom: 4px;
  color: var(--el-text-color-primary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.date-num.is-today {
  color: var(--el-color-primary);
  font-weight: bold;
}

.today-text {
  font-size: 12px;
  padding: 0 6px;
  border-radius: 999px;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-8);
}

.events {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.event-item {
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 999px;
  color: var(--el-color-white);
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.4;
  box-shadow: var(--el-box-shadow-lighter);
  border: 1px solid transparent;
  transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
}

.event-item:hover {
  transform: translateY(-1px);
  opacity: 0.95;
  box-shadow: var(--el-box-shadow-light);
}

.event-holiday {
  background-color: var(--el-color-danger);
}

.event-exam {
  background-color: var(--el-color-warning);
}

.event-activity {
  background-color: var(--el-color-success);
}

.event-teaching {
  background-color: var(--el-color-primary);
}

.event-other {
  background-color: var(--el-text-color-secondary);
}

/* Element Plus 日历整体细节优化 */
:deep(.el-calendar) {
  --el-calendar-border-color: var(--el-border-color-lighter);
}

:deep(.el-calendar__header) {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  background: rgba(255, 255, 255, 0.03);
  margin-bottom: 12px;
}

:deep(.el-calendar__title) {
  font-weight: 700;
  color: var(--el-text-color-primary);
}

:deep(.el-calendar__button-group .el-button) {
  border-radius: 999px;
}

:deep(.el-calendar-table) {
  border-radius: 12px;
  overflow: hidden;
}

:deep(.el-calendar-table th) {
  color: var(--el-text-color-secondary);
  font-weight: 600;
  background: rgba(255, 255, 255, 0.03);
}

:deep(.el-calendar-table td .el-calendar-day) {
  height: 112px;
  padding: 6px;
}

:deep(.el-calendar-table td.is-selected) {
  background: var(--el-color-primary-light-9);
}

/* 调整日历高度以适应屏幕 */
:deep(.el-calendar-table .el-calendar-day) {
  height: 112px;
}
</style>
