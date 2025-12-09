<script setup lang="ts">
/**
 * 校历安排 (Material Design 适配版)
 * 
 * Material Design 适配说明：
 * 1. 使用 Vuetify Grid 系统 (v-row, v-col) 实现自定义日历视图，替代 el-calendar
 * 2. 使用 v-dialog 和 v-card 实现事件添加/编辑弹窗
 * 3. 事件使用 v-chip 展示，不同类型对应不同 Material 颜色
 * 4. 支持文件上传导入 Excel (v-file-input)
 */
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

// --- 类型定义 ---
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

// --- 状态管理 ---
const currentDate = ref(new Date())
const events = ref<CalendarEvent[]>([])
const dialogVisible = ref(false)
const dialogType = ref<'add' | 'edit'>('add')
const dateRange = ref<string[]>([]) // Vuetify date picker uses array
const loading = ref(false)
const snackbar = ref({ show: false, text: '', color: 'success' })

// 表单数据
const form = ref<CalendarEvent>({
  title: '',
  type: '活动',
  start_date: '',
  end_date: '',
  location: '',
  related_classes: '',
  description: ''
})

const eventTypes = ['节假日', '考试', '活动', '教学', '其他']

// --- 计算属性 ---
const isAdmin = computed(() => {
  const role = localStorage.getItem('user_role') // Check consistent key
  return role === 'admin'
})

const currentMonthLabel = computed(() => {
  return currentDate.value.toLocaleString('zh-CN', { year: 'numeric', month: 'long' })
})

// --- 日历逻辑 ---
const calendarDays = computed(() => {
  const year = currentDate.value.getFullYear()
  const month = currentDate.value.getMonth()
  
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  
  const days = []
  
  // 补全上个月的日期
  const startDayOfWeek = firstDay.getDay() || 7 // 1 (Mon) - 7 (Sun)
  for (let i = 1; i < startDayOfWeek; i++) {
    const d = new Date(year, month, 1 - i)
    days.unshift({ date: d, isCurrentMonth: false })
  }
  
  // 当前月的日期
  for (let i = 1; i <= lastDay.getDate(); i++) {
    days.push({ date: new Date(year, month, i), isCurrentMonth: true })
  }
  
  // 补全下个月的日期，凑齐 42 格 (6行)
  const remaining = 42 - days.length
  for (let i = 1; i <= remaining; i++) {
    const d = new Date(year, month + 1, i)
    days.push({ date: d, isCurrentMonth: false })
  }
  
  return days
})

// --- 方法 ---
const fetchEvents = async () => {
  loading.value = true
  try {
    const response = await axios.get('http://localhost:8000/api/calendar/events', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    events.value = response.data
  } catch (error) {
    // 模拟数据
    events.value = [
      { id: 1, title: '期末考试', type: '考试', start_date: '2023-12-20', end_date: '2023-12-22' },
      { id: 2, title: '元旦放假', type: '节假日', start_date: '2024-01-01', end_date: '2024-01-03' }
    ]
  } finally {
    loading.value = false
  }
}

const getEventsForDate = (date: Date) => {
  const dateStr = formatDate(date)
  return events.value.filter(event => {
    return dateStr >= event.start_date && dateStr <= event.end_date
  })
}

const formatDate = (date: Date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const isToday = (date: Date) => {
  return formatDate(date) === formatDate(new Date())
}

const getEventColor = (type: string) => {
  const map: Record<string, string> = {
    '节假日': 'error',
    '考试': 'warning',
    '活动': 'success',
    '教学': 'primary',
    '其他': 'grey'
  }
  return map[type] || 'grey'
}

// 切换月份
const prevMonth = () => {
  currentDate.value = new Date(currentDate.value.getFullYear(), currentDate.value.getMonth() - 1, 1)
}

const nextMonth = () => {
  currentDate.value = new Date(currentDate.value.getFullYear(), currentDate.value.getMonth() + 1, 1)
}

// 点击日期
const handleDateClick = (date: Date) => {
  if (isAdmin.value) {
    const dateStr = formatDate(date)
    dialogType.value = 'add'
    form.value = {
      title: '',
      type: '活动',
      start_date: dateStr,
      end_date: dateStr,
      location: '',
      related_classes: '',
      description: ''
    }
    // Vuetify date picker expects Date object or string depending on config, usually string YYYY-MM-DD works
    // But for range, we might need a separate handling or just use two inputs
    // Simplifying: just set default start/end
    dialogVisible.value = true
  }
}

// 点击事件
const handleEventClick = (event: CalendarEvent, e: Event) => {
  e.stopPropagation()
  if (isAdmin.value) {
    dialogType.value = 'edit'
    form.value = { ...event }
    dialogVisible.value = true
  } else {
    // 简单展示详情
    showSnackbar(`${event.title}: ${event.start_date} ~ ${event.end_date}`, 'info')
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!form.value.title) {
    showSnackbar('请输入事件名称', 'warning')
    return
  }
  
  // 简单校验日期
  if (!form.value.start_date || !form.value.end_date) {
     showSnackbar('请选择完整时间范围', 'warning')
     return
  }

  try {
    const headers = { Authorization: `Bearer ${localStorage.getItem('token')}` }
    if (dialogType.value === 'add') {
      await axios.post('http://localhost:8000/api/calendar/events', form.value, { headers })
      showSnackbar('添加成功', 'success')
    } else {
      await axios.put(`http://localhost:8000/api/calendar/events/${form.value.id}`, form.value, { headers })
      showSnackbar('更新成功', 'success')
    }
    dialogVisible.value = false
    fetchEvents()
  } catch (error) {
    showSnackbar('操作失败', 'error')
  }
}

const showSnackbar = (text: string, color: string) => {
  snackbar.value = { show: true, text, color }
}

// Excel 导入
const handleImport = async (files: File[]) => {
  if (!files.length) return
  const formData = new FormData()
  formData.append('file', files[0])
  
  try {
    await axios.post('http://localhost:8000/api/calendar/import', formData, {
      headers: { 
        'Content-Type': 'multipart/form-data',
        Authorization: `Bearer ${localStorage.getItem('token')}` 
      }
    })
    showSnackbar('导入成功', 'success')
    fetchEvents()
  } catch (error) {
    showSnackbar('导入失败', 'error')
  }
}

onMounted(() => {
  fetchEvents()
})
</script>

<template>
  <v-container fluid class="fill-height align-start pa-0">
    <v-card class="mx-4 mt-4 flex-grow-1" elevation="2">
      <!-- 头部工具栏 -->
      <v-toolbar color="white" flat>
        <v-btn icon @click="prevMonth">
          <v-icon>mdi-chevron-left</v-icon>
        </v-btn>
        <v-toolbar-title class="text-center font-weight-bold text-h6">
          {{ currentMonthLabel }}
        </v-toolbar-title>
        <v-btn icon @click="nextMonth">
          <v-icon>mdi-chevron-right</v-icon>
        </v-btn>
        
        <v-spacer></v-spacer>
        
        <div v-if="isAdmin" class="d-flex align-center mr-4">
          <v-btn
            prepend-icon="mdi-plus"
            color="primary"
            variant="elevated"
            class="mr-2"
            @click="handleDateClick(new Date())"
          >
            添加事件
          </v-btn>
          
          <!-- 隐藏的文件输入，通过按钮触发 -->
           <v-file-input
              label="导入 Excel"
              variant="outlined"
              density="compact"
              hide-details
              prepend-icon="mdi-file-excel"
              accept=".xlsx,.xls"
              class="excel-import-input"
              @update:modelValue="handleImport"
            ></v-file-input>
        </div>
      </v-toolbar>

      <v-divider></v-divider>

      <!-- 星期表头 -->
      <v-row no-gutters class="bg-grey-lighten-4">
        <v-col v-for="day in ['周一', '周二', '周三', '周四', '周五', '周六', '周日']" :key="day" class="text-center py-2 font-weight-bold text-grey-darken-2">
          {{ day }}
        </v-col>
      </v-row>

      <v-divider></v-divider>

      <!-- 日历网格 -->
      <div class="calendar-grid">
        <div 
          v-for="(item, index) in calendarDays" 
          :key="index"
          class="calendar-cell"
          :class="{ 'not-current-month': !item.isCurrentMonth, 'today': isToday(item.date) }"
          @click="handleDateClick(item.date)"
        >
          <div class="date-number">
            {{ item.date.getDate() }}
            <span v-if="isToday(item.date)" class="today-badge">今天</span>
          </div>
          
          <div class="events-list">
            <v-chip
              v-for="event in getEventsForDate(item.date)"
              :key="event.id"
              :color="getEventColor(event.type)"
              size="x-small"
              class="event-chip mb-1 w-100 justify-start px-1"
              label
              @click="handleEventClick(event, $event)"
            >
              <span class="text-truncate">{{ event.title }}</span>
            </v-chip>
          </div>
        </div>
      </div>
    </v-card>

    <!-- 事件编辑弹窗 -->
    <v-dialog v-model="dialogVisible" max-width="500px">
      <v-card>
        <v-card-title class="bg-primary text-white">
          {{ dialogType === 'add' ? '添加校历事件' : '编辑校历事件' }}
        </v-card-title>
        <v-card-text class="pt-4">
          <v-form>
            <v-text-field
              v-model="form.title"
              label="事件名称"
              variant="outlined"
              prepend-inner-icon="mdi-format-title"
            ></v-text-field>
            
            <v-select
              v-model="form.type"
              :items="eventTypes"
              label="类型"
              variant="outlined"
              prepend-inner-icon="mdi-tag-outline"
            ></v-select>
            
            <v-row>
              <v-col cols="6">
                <v-text-field
                  v-model="form.start_date"
                  label="开始日期"
                  type="date"
                  variant="outlined"
                ></v-text-field>
              </v-col>
              <v-col cols="6">
                <v-text-field
                  v-model="form.end_date"
                  label="结束日期"
                  type="date"
                  variant="outlined"
                ></v-text-field>
              </v-col>
            </v-row>
            
            <v-text-field
              v-model="form.location"
              label="地点"
              variant="outlined"
              prepend-inner-icon="mdi-map-marker"
            ></v-text-field>
            
            <v-textarea
              v-model="form.description"
              label="备注"
              variant="outlined"
              rows="3"
            ></v-textarea>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="dialogVisible = false">取消</v-btn>
          <v-btn color="primary" variant="elevated" @click="handleSubmit">确定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000">
      {{ snackbar.text }}
    </v-snackbar>
  </v-container>
</template>

<style scoped>
.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  grid-auto-rows: minmax(100px, 1fr);
  border-left: 1px solid #e0e0e0;
  border-bottom: 1px solid #e0e0e0;
}

.calendar-cell {
  border-right: 1px solid #e0e0e0;
  border-top: 1px solid #e0e0e0;
  padding: 4px;
  min-height: 100px;
  cursor: pointer;
  transition: background-color 0.2s;
  display: flex;
  flex-direction: column;
}

.calendar-cell:hover {
  background-color: #f5f5f5;
}

.not-current-month {
  background-color: #fafafa;
  color: #bdbdbd;
}

.today {
  background-color: #e3f2fd;
}

.date-number {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.today-badge {
  font-size: 10px;
  color: #1976d2;
  font-weight: bold;
}

.events-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}

.event-chip {
  cursor: pointer;
}

.excel-import-input {
  width: 150px;
}
</style>
