<script setup lang="ts">
/**
 * 教师工作安排与调课页面 (Material Design)
 * 包含：工作日历、调课申请
 */
import { ref, reactive, onMounted, computed } from 'vue'
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
const schedules = ref<WorkSchedule[]>([])
const loading = ref(false)
const courses = ref<CourseOption[]>([])
const currentDate = ref(new Date())

// 调课申请表单
const adjustForm = reactive({
  course_id: undefined as number | undefined,
  old_time: null as Date | null,
  new_time: null as Date | null,
  old_classroom: '',
  new_classroom: '',
  reason: ''
})
const formValid = ref(false)

const snackbar = reactive({
  show: false,
  text: '',
  color: 'success'
})

const showMessage = (text: string, color: 'success' | 'error' | 'warning' = 'success') => {
  snackbar.text = text
  snackbar.color = color
  snackbar.show = true
}

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
    return
  }
  
  try {
    await axios.post('http://localhost:8000/api/work/adjust/apply', {
        ...adjustForm,
        old_time: adjustForm.old_time?.toISOString(),
        new_time: adjustForm.new_time?.toISOString()
    }, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
    // 重置表单
    adjustForm.reason = ''
    adjustForm.old_classroom = ''
    adjustForm.new_classroom = ''
    showMessage('调课申请已提交', 'success')
  } catch (error) {
    showMessage('申请提交失败', 'error')
  }
}

// 获取日程类型颜色
const getScheduleTypeColor = (type: string) => {
  const map: Record<string, string> = {
    '上课': 'primary',
    '开会': 'warning',
    '值班': 'success',
    '其他': 'grey'
  }
  return map[type] || 'grey'
}

const getScheduleTypeIcon = (type: string) => {
    const map: Record<string, string> = {
    '上课': 'mdi-teach',
    '开会': 'mdi-account-group',
    '值班': 'mdi-shield-account',
    '其他': 'mdi-calendar-text'
  }
  return map[type] || 'mdi-circle-small'
}

// 分组日程 (按日期)
const groupedSchedules = computed(() => {
    const groups: Record<string, WorkSchedule[]> = {}
    schedules.value.forEach(s => {
        const date = new Date(s.time).toLocaleDateString()
        if (!groups[date]) groups[date] = []
        groups[date].push(s)
    })
    return groups
})
</script>

<template>
  <v-container fluid>
    <v-card elevation="2" class="rounded-lg">
      <v-tabs v-model="activeTab" color="primary">
        <v-tab value="calendar">
          <v-icon start>mdi-calendar-month</v-icon>
          工作日历
        </v-tab>
        <v-tab value="adjust">
          <v-icon start>mdi-swap-horizontal</v-icon>
          调课申请
        </v-tab>
      </v-tabs>

      <v-window v-model="activeTab">
        <!-- 工作日历 -->
        <v-window-item value="calendar">
          <v-card-text>
            <div v-if="Object.keys(groupedSchedules).length === 0" class="text-center py-8 text-grey">
                <v-icon size="64" class="mb-2">mdi-calendar-blank</v-icon>
                <p>暂无工作安排</p>
            </div>
            
            <v-timeline v-else align="start" side="end">
              <v-timeline-item
                v-for="(items, date) in groupedSchedules"
                :key="date"
                dot-color="primary"
                size="small"
              >
                <template v-slot:opposite>
                  <div class="text-h6 font-weight-bold">{{ date }}</div>
                </template>
                
                <v-card v-for="item in items" :key="item.id" class="mb-2" variant="outlined">
                    <v-card-item>
                        <template v-slot:prepend>
                             <v-icon :color="getScheduleTypeColor(item.type)" class="mr-2">{{ getScheduleTypeIcon(item.type) }}</v-icon>
                        </template>
                        <v-card-title class="text-subtitle-1">{{ item.content }}</v-card-title>
                        <v-card-subtitle>
                             <v-chip size="x-small" :color="getScheduleTypeColor(item.type)" label class="mr-2">{{ item.type }}</v-chip>
                             {{ new Date(item.time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) }}
                        </v-card-subtitle>
                    </v-card-item>
                    <v-card-text v-if="item.remark" class="pt-0 text-caption text-grey">
                        备注: {{ item.remark }}
                    </v-card-text>
                </v-card>
              </v-timeline-item>
            </v-timeline>
          </v-card-text>
        </v-window-item>

        <!-- 调课申请 -->
        <v-window-item value="adjust">
          <v-container>
             <v-row justify="center">
                 <v-col cols="12" md="8">
                     <v-card variant="flat">
                         <v-card-title>填写调课申请单</v-card-title>
                         <v-card-text>
                             <v-form v-model="formValid" @submit.prevent="submitAdjust">
                                <v-select
                                    v-model="adjustForm.course_id"
                                    :items="courses"
                                    item-title="name"
                                    item-value="id"
                                    label="调课课程"
                                    variant="outlined"
                                    prepend-inner-icon="mdi-book"
                                    :rules="[v => !!v || '请选择课程']"
                                ></v-select>
                                
                                <v-row>
                                    <v-col cols="12" md="6">
                                        <v-text-field
                                            v-model="adjustForm.old_time"
                                            label="原上课时间"
                                            type="datetime-local"
                                            variant="outlined"
                                            prepend-inner-icon="mdi-clock-start"
                                            :rules="[v => !!v || '请选择原时间']"
                                        ></v-text-field>
                                    </v-col>
                                    <v-col cols="12" md="6">
                                        <v-text-field
                                            v-model="adjustForm.old_classroom"
                                            label="原教室 (选填)"
                                            variant="outlined"
                                            prepend-inner-icon="mdi-map-marker"
                                        ></v-text-field>
                                    </v-col>
                                </v-row>
                                
                                <v-row>
                                    <v-col cols="12" md="6">
                                        <v-text-field
                                            v-model="adjustForm.new_time"
                                            label="拟调整时间"
                                            type="datetime-local"
                                            variant="outlined"
                                            prepend-inner-icon="mdi-clock-end"
                                            :rules="[v => !!v || '请选择新时间']"
                                        ></v-text-field>
                                    </v-col>
                                    <v-col cols="12" md="6">
                                        <v-text-field
                                            v-model="adjustForm.new_classroom"
                                            label="拟调整教室 (选填)"
                                            variant="outlined"
                                            prepend-inner-icon="mdi-map-marker-plus"
                                        ></v-text-field>
                                    </v-col>
                                </v-row>
                                
                                <v-textarea
                                    v-model="adjustForm.reason"
                                    label="调课原因"
                                    variant="outlined"
                                    prepend-inner-icon="mdi-text-box"
                                    rows="3"
                                    :rules="[v => !!v || '请输入原因']"
                                ></v-textarea>
                                
                                <v-btn
                                    type="submit"
                                    color="primary"
                                    block
                                    size="large"
                                    :disabled="!formValid"
                                    prepend-icon="mdi-send"
                                >
                                    提交申请
                                </v-btn>
                             </v-form>
                         </v-card-text>
                     </v-card>
                 </v-col>
             </v-row>
          </v-container>
        </v-window-item>
      </v-window>
    </v-card>
  </v-container>
</template>
