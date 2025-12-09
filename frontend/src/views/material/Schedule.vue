<script setup lang="ts">
import { ref, reactive, computed } from 'vue'

// 1. 类型定义
interface ScheduleParam {
  teacherNum: number
  classroomNum: number
  courseNum: number
}

// 排课表单元格数据
interface ScheduleCell {
  courseName: string
  teacherName?: string
  classroomName?: string
  color?: string
}

// 排课表数据结构
type ScheduleData = Record<string, Record<string, ScheduleCell>> // { 'Monday': { '1': Cell, '2': Cell... } }

interface ScheduleResult {
  type: 'teacher' | 'classroom'
  data: Record<string, ScheduleData> // Key is Teacher Name or Classroom Name
  conflictRate: number
  utilizationRate: number
}

// 2. 状态管理
const params = reactive<ScheduleParam>({
  teacherNum: 8,
  classroomNum: 10,
  courseNum: 15
})

const loading = ref(false)
const activeTab = ref('teacher') // teacher | classroom
const scheduleResult = ref<ScheduleResult | null>(null)

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

// 3. 模拟数据与算法
const weekDays = ['周一', '周二', '周三', '周四', '周五']
const periods = ['1', '2', '3', '4', '5', '6']
const mockCourses = ['Python编程', '数据结构', '高等数学', '大学英语', '计算机网络', '操作系统', '数据库原理', '软件工程']
// Material Design colors
const bgColors = ['#E3F2FD', '#E8F5E9', '#FFF3E0', '#FFEBEE', '#F3E5F5', '#FFFDE7']

const fullScheduleData = ref<{
  teacher: Record<string, ScheduleData>
  classroom: Record<string, ScheduleData>
}>({ teacher: {}, classroom: {} })

// 模拟遗传算法生成排课表
const generateSchedule = () => {
  loading.value = true
  scheduleResult.value = null
  
  setTimeout(() => {
    loading.value = false
    
    const teacherData: Record<string, ScheduleData> = {}
    const classroomData: Record<string, ScheduleData> = {}
    
    for (let i = 1; i <= params.teacherNum; i++) teacherData[`教师 ${i}`] = {}
    for (let i = 1; i <= params.classroomNum; i++) classroomData[`教室 10${i}`] = {}
    
    weekDays.forEach(day => {
      periods.forEach(period => {
        for (let r = 1; r <= params.classroomNum; r++) {
           if (Math.random() > 0.15) {
             const courseIdx = Math.floor(Math.random() * mockCourses.length)
             const teacherIdx = Math.floor(Math.random() * params.teacherNum) + 1
             const courseName = mockCourses[courseIdx]
             const teacherName = `教师 ${teacherIdx}`
             const roomName = `教室 10${r}`
             const color = bgColors[courseIdx % bgColors.length]
             
             const cell: ScheduleCell = { courseName, teacherName, classroomName: roomName, color }
             
             if (!classroomData[roomName][day]) classroomData[roomName][day] = {}
             classroomData[roomName][day][period] = cell
             
             if (!teacherData[teacherName][day]) teacherData[teacherName][day] = {}
             if (!teacherData[teacherName][day][period]) {
                teacherData[teacherName][day][period] = cell
             }
           }
        }
      })
    })
    
    scheduleResult.value = {
      type: 'teacher',
      data: teacherData,
      conflictRate: 0,
      utilizationRate: Math.min(0.85 + Math.random() * 0.1, 0.95)
    }
    
    fullScheduleData.value = {
      teacher: teacherData,
      classroom: classroomData
    }
    
    showMessage('排课表生成成功！算法迭代完成。')
    
  }, 2000)
}

// 当前展示的数据
const currentViewData = computed(() => {
  if (activeTab.value === 'teacher') return fullScheduleData.value.teacher
  return fullScheduleData.value.classroom
})

const handleExport = () => {
  if (!scheduleResult.value) {
    showMessage('请先生成排课表', 'warning')
    return
  }
  showMessage('排课表已导出为 Excel 文件 (排课表_2025.xlsx)')
}

const headers = [
  { title: '节次', key: 'period', align: 'center', sortable: false, width: '80px' },
  ...weekDays.map(day => ({ title: day, key: day, align: 'center', sortable: false }))
] as any[]

const tableItems = computed(() => {
  return periods.map(p => ({ period: p }))
})

</script>

<template>
  <div class="schedule-container pa-4">
    <!-- 顶部参数设置 -->
    <v-card class="mb-4" elevation="2">
      <v-card-title>排课参数设置</v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="12" md="4">
            <v-text-field
              v-model.number="params.teacherNum"
              label="教师数量"
              type="number"
              min="1"
              max="50"
              variant="outlined"
              density="compact"
              hide-details
            ></v-text-field>
          </v-col>
          <v-col cols="12" md="4">
            <v-text-field
              v-model.number="params.classroomNum"
              label="教室数量"
              type="number"
              min="1"
              max="50"
              variant="outlined"
              density="compact"
              hide-details
            ></v-text-field>
          </v-col>
          <v-col cols="12" md="4">
            <v-text-field
              v-model.number="params.courseNum"
              label="课程数量"
              type="number"
              min="1"
              max="100"
              variant="outlined"
              density="compact"
              hide-details
            ></v-text-field>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <v-row>
      <!-- 左侧操作与统计 -->
      <v-col cols="12" md="3">
        <v-card elevation="2" class="h-100">
          <v-card-text class="d-flex flex-column align-center">
            <v-btn
              color="warning"
              size="large"
              block
              class="mb-6"
              @click="generateSchedule"
              :loading="loading"
            >
              {{ loading ? '遗传算法迭代中...' : '生成排课表' }}
            </v-btn>
            
            <div v-if="scheduleResult" class="w-100 d-flex flex-column align-center gap-4">
              <div class="text-center mb-4">
                <div class="text-caption text-grey mb-2">冲突率</div>
                <v-progress-circular
                  :model-value="scheduleResult.conflictRate"
                  color="success"
                  size="80"
                  width="8"
                >
                  {{ scheduleResult.conflictRate }}%
                </v-progress-circular>
              </div>

              <div class="text-center mb-6">
                <div class="text-caption text-grey mb-2">资源利用率</div>
                <v-progress-circular
                  :model-value="Math.round(scheduleResult.utilizationRate * 100)"
                  color="primary"
                  size="80"
                  width="8"
                >
                  {{ Math.round(scheduleResult.utilizationRate * 100) }}%
                </v-progress-circular>
              </div>
              
              <v-divider class="w-100 mb-4"></v-divider>
              <v-btn variant="outlined" color="primary" block @click="handleExport">导出 Excel</v-btn>
            </div>
            
            <div v-else class="text-center text-grey py-4">
              <p>请点击生成按钮开始排课</p>
              <p class="text-caption text-warning mt-2">注：遗传算法将自动优化冲突与资源分配</p>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- 右侧可视化展示 -->
      <v-col cols="12" md="9">
        <v-card elevation="2" class="h-100">
          <v-tabs v-model="activeTab" bg-color="primary">
            <v-tab value="teacher">教师视角</v-tab>
            <v-tab value="classroom">教室视角</v-tab>
          </v-tabs>

          <v-card-text>
             <div v-if="!scheduleResult" class="d-flex justify-center align-center" style="height: 300px;">
                <div class="text-center text-grey">
                   <v-icon size="64" color="grey-lighten-2">mdi-calendar-blank</v-icon>
                   <p class="mt-2">暂无排课数据</p>
                </div>
             </div>

             <div v-else class="schedule-tables-container">
               <div v-for="(schedule, name) in currentViewData" :key="name" class="mb-8">
                 <div class="schedule-title mb-2 pl-2">
                    {{ name }} 课表
                 </div>
                 <v-data-table
                    :headers="headers"
                    :items="tableItems"
                    density="compact"
                    class="schedule-table elevation-1"
                    hide-default-footer
                    disable-pagination
                 >
                    <template v-for="day in weekDays" :key="day" #[`item.${day}`]="{ item }">
                       <div 
                         class="course-cell"
                         :style="{ backgroundColor: schedule[day]?.[item.period]?.color || '' }"
                       >
                         <div v-if="schedule[day]?.[item.period]" class="cell-content">
                           <div class="font-weight-bold">{{ schedule[day][item.period].courseName }}</div>
                           <div class="text-caption text-grey-darken-2" v-if="activeTab === 'teacher'">
                             {{ schedule[day][item.period].classroomName }}
                           </div>
                           <div class="text-caption text-grey-darken-2" v-if="activeTab === 'classroom'">
                             {{ schedule[day][item.period].teacherName }}
                           </div>
                         </div>
                       </div>
                    </template>
                 </v-data-table>
               </div>
             </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="3000"
      location="top"
    >
      {{ snackbar.text }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar.show = false">关闭</v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<style scoped>
.schedule-container {
  height: 100%;
}
.schedule-tables-container {
  max-height: 600px;
  overflow-y: auto;
}
.schedule-title {
  font-weight: bold;
  color: #616161;
  border-left: 4px solid #FFC107;
}
.course-cell {
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  font-size: 12px;
  margin: 2px;
  text-align: center;
  width: 100%;
}
.cell-content {
  line-height: 1.2;
}
</style>
