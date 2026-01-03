<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import { useTables } from '@/composables/useTables'

interface ScheduleCell {
  courseName: string
  teacherName?: string
  classroomName?: string
  color?: string
}

type ScheduleData = Record<string, Record<string, ScheduleCell>>

interface ScheduleEntryPayload {
  course_id: number
  teacher_id: string
  classroom_id: number
  day: number
  period: number
}

interface ScheduleStats {
  fitness: number
  utilization: number
  conflict_rate: number
}

const activeTab = ref<'teacher' | 'classroom'>('teacher')
const viewSource = ref<'db' | 'preview'>('db')

const weekDays = ['周一', '周二', '周三', '周四', '周五']
const periods = ['1', '2', '3', '4', '5', '6']
const colors = ['#ecf5ff', '#f0f9eb', '#fdf6ec', '#fef0f0', '#e8f3ff', '#fff7e6']

const { rows, loading: tableLoading, reloadTables } = useTables(['schedules', 'courses', 'teachers', 'classrooms'])

const teacherRows = computed(() => rows('teachers') || [])
const courseRows = computed(() => rows('courses') || [])
const classroomRows = computed(() => rows('classrooms') || [])
const scheduleRows = computed(() => rows('schedules') || [])

const selectedTeacherIds = ref<string[]>([])
const selectedCourseIds = ref<number[]>([])
const selectedClassroomIds = ref<number[]>([])
const generateLoading = ref(false)
const saveLoading = ref(false)
const previewEntries = ref<ScheduleEntryPayload[]>([])
const gaStats = ref<ScheduleStats | null>(null)

watch(
  teacherRows,
  (list) => {
    if (list.length && selectedTeacherIds.value.length === 0) {
      selectedTeacherIds.value = list.map((teacher: any) => String(teacher.id))
    }
  },
  { immediate: true }
)

watch(
  courseRows,
  (list) => {
    if (list.length && selectedCourseIds.value.length === 0) {
      selectedCourseIds.value = list.map((course: any) => Number(course.id))
    }
  },
  { immediate: true }
)

watch(
  classroomRows,
  (list) => {
    if (list.length && selectedClassroomIds.value.length === 0) {
      selectedClassroomIds.value = list.map((room: any) => Number(room.id))
    }
  },
  { immediate: true }
)

const courseMap = computed<Record<number, any>>(() => {
  const map: Record<number, any> = {}
  courseRows.value.forEach((course: any) => {
    map[Number(course.id)] = course
  })
  return map
})

const teacherMap = computed<Record<string, any>>(() => {
  const map: Record<string, any> = {}
  teacherRows.value.forEach((teacher: any) => {
    map[String(teacher.id)] = teacher
  })
  return map
})

const classroomMap = computed<Record<number, any>>(() => {
  const map: Record<number, any> = {}
  classroomRows.value.forEach((room: any) => {
    map[Number(room.id)] = room
  })
  return map
})

const formatCourseLabel = (course: any) => {
  const teacherName = teacherMap.value[String(course.teacher_id ?? course.teacherId)]?.name
  return teacherName ? `${course.name}（${teacherName}）` : course.name
}

const buildScheduleDataFromRecords = (
  records: ScheduleEntryPayload[],
  groupBy: 'teacher' | 'classroom'
) => {
  const data: Record<string, ScheduleData> = {}
  const colorCache = new Map<number, string>()

  records.forEach((item: any) => {
    const teacherId = String(item.teacher_id)
    const teacherName = teacherMap.value[teacherId]?.name ?? `教师 ${teacherId}`
    const classroomName = classroomMap.value[item.classroom_id]?.name ?? `教室 ${item.classroom_id}`
    const courseName = courseMap.value[item.course_id]?.name ?? `课程 ${item.course_id}`
    const dayLabel = weekDays[item.day] ?? `周${item.day + 1}`
    const periodLabel = (item.period + 1).toString()
    const groupingKey = groupBy === 'teacher' ? teacherName : classroomName

    if (!colorCache.has(item.course_id)) {
      colorCache.set(item.course_id, colors[colorCache.size % colors.length])
    }

    if (!data[groupingKey]) data[groupingKey] = {}
    if (!data[groupingKey][dayLabel]) data[groupingKey][dayLabel] = {}

    data[groupingKey][dayLabel][periodLabel] = {
      courseName,
      teacherName,
      classroomName,
      color: colorCache.get(item.course_id)
    }
  })

  return data
}

const teacherScheduleDataDb = computed(() =>
  buildScheduleDataFromRecords(scheduleRows.value as any, 'teacher')
)
const classroomScheduleDataDb = computed(() =>
  buildScheduleDataFromRecords(scheduleRows.value as any, 'classroom')
)
const teacherScheduleDataPreview = computed(() =>
  buildScheduleDataFromRecords(previewEntries.value, 'teacher')
)
const classroomScheduleDataPreview = computed(() =>
  buildScheduleDataFromRecords(previewEntries.value, 'classroom')
)

const hasPreviewData = computed(() => previewEntries.value.length > 0)

const currentViewData = computed(() => {
  if (viewSource.value === 'preview' && hasPreviewData.value) {
    return activeTab.value === 'teacher'
      ? teacherScheduleDataPreview.value
      : classroomScheduleDataPreview.value
  }
  return activeTab.value === 'teacher' ? teacherScheduleDataDb.value : classroomScheduleDataDb.value
})

const teacherCount = computed(() => teacherRows.value.length)
const classroomCount = computed(() => classroomRows.value.length)
const courseCount = computed(() => courseRows.value.length)

const classroomCountForView = computed(() => {
  if (viewSource.value === 'preview' && hasPreviewData.value && selectedClassroomIds.value.length) {
    return selectedClassroomIds.value.length
  }
  return classroomCount.value
})

const totalSchedulesDb = computed(() => scheduleRows.value.length)
const totalSchedulesPreview = computed(() => previewEntries.value.length)
const totalSchedules = computed(() => {
  if (viewSource.value === 'preview' && hasPreviewData.value) {
    return totalSchedulesPreview.value
  }
  return totalSchedulesDb.value
})

const totalSlots = computed(() => classroomCountForView.value * weekDays.length * periods.length)

const utilizationRate = computed(() => {
  if (viewSource.value === 'preview' && hasPreviewData.value) {
    if (!totalSlots.value) return 0
    const util = gaStats.value?.utilization
    if (typeof util === 'number') {
      return Math.min(100, Math.round(util * 100))
    }
    return Math.min(100, Math.round((totalSchedulesPreview.value / totalSlots.value) * 100))
  }
  if (!totalSlots.value) return 0
  return Math.min(100, Math.round((totalSchedulesDb.value / totalSlots.value) * 100))
})

const conflictCountDb = computed(() => {
  const teacherKey = new Map<string, number>()
  const classroomKey = new Map<string, number>()
  scheduleRows.value.forEach((item: any) => {
    const tKey = `${item.teacher_id}-${item.day}-${item.period}`
    const cKey = `${item.classroom_id}-${item.day}-${item.period}`
    teacherKey.set(tKey, (teacherKey.get(tKey) || 0) + 1)
    classroomKey.set(cKey, (classroomKey.get(cKey) || 0) + 1)
  })

  let conflicts = 0
  teacherKey.forEach((count) => {
    if (count > 1) conflicts += count - 1
  })
  classroomKey.forEach((count) => {
    if (count > 1) conflicts += count - 1
  })
  return conflicts
})

const conflictRate = computed(() => {
  if (viewSource.value === 'preview' && hasPreviewData.value) {
    if (!totalSchedulesPreview.value) return 0
    const conflicts = gaStats.value?.conflict_rate ?? 0
    return Math.min(100, Math.round((conflicts / totalSchedulesPreview.value) * 100))
  }
  if (!totalSchedulesDb.value) return 0
  return Math.min(100, Math.round((conflictCountDb.value / totalSchedulesDb.value) * 100))
})

const hasScheduleData = computed(() => {
  if (viewSource.value === 'preview') {
    return hasPreviewData.value
  }
  return totalSchedulesDb.value > 0
})

watch(hasPreviewData, (has) => {
  if (!has && viewSource.value === 'preview') {
    viewSource.value = 'db'
  }
})

const refreshSchedule = async () => {
  viewSource.value = 'db'
  await reloadTables(true)
  ElMessage.success('排课数据已同步')
}

const buildGeneratePayload = () => {
  const teachers = teacherRows.value
    .filter((teacher: any) => selectedTeacherIds.value.includes(String(teacher.id)))
    .map((teacher: any) => ({
      id: String(teacher.id),
      name: teacher.name
    }))

  const courses = courseRows.value
    .filter((course: any) => selectedCourseIds.value.includes(Number(course.id)))
    .map((course: any) => ({
      id: Number(course.id),
      name: course.name,
      teacher_id: String(course.teacher_id ?? course.teacherId),
      is_required: String(course.course_type ?? '').includes('必修')
    }))

  const classrooms = classroomRows.value
    .filter((room: any) => selectedClassroomIds.value.includes(Number(room.id)))
    .map((room: any) => ({
      id: Number(room.id),
      name: room.name,
      capacity: Number(room.capacity),
      is_multimedia: Boolean(room.is_multimedia)
    }))

  return { teachers, courses, classrooms }
}

const generateSchedule = async () => {
  if (
    !selectedTeacherIds.value.length ||
    !selectedCourseIds.value.length ||
    !selectedClassroomIds.value.length
  ) {
    ElMessage.warning('请选择至少一名教师、一门课程和一个可用教室')
    return
  }
  generateLoading.value = true
  try {
    const payload = buildGeneratePayload()
    const { data } = await axios.post('/api/schedule/generate', payload)
    previewEntries.value = data.entries || []
    gaStats.value = {
      fitness: data.fitness,
      utilization: data.utilization,
      conflict_rate: data.conflict_rate
    }
    viewSource.value = 'preview'
    ElMessage.success('排课方案已生成，请查看预览结果')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '排课生成失败，请稍后重试')
  } finally {
    generateLoading.value = false
  }
}

const saveSchedule = async () => {
  if (!previewEntries.value.length) {
    ElMessage.warning('请先生成排课结果')
    return
  }
  try {
    await ElMessageBox.confirm(
      '确定要将当前排课结果写入数据库吗？保存后会覆盖原有数据。',
      '提示',
      { type: 'warning' }
    )
  } catch {
    return
  }

  saveLoading.value = true
  try {
    await axios.post('/api/schedule/save', {
      entries: previewEntries.value,
      clear_existing: true
    })
    ElMessage.success('排课结果已写入数据库')
    previewEntries.value = []
    gaStats.value = null
    viewSource.value = 'db'
    await reloadTables(true)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '保存排课失败，请重试')
  } finally {
    saveLoading.value = false
  }
}

const handleExport = () => {
  if (!hasScheduleData.value) {
    ElMessage.warning('暂无排课数据可导出')
    return
  }
  ElMessage.success('排课表已导出到 Excel（示例功能）')
}
</script>

<template>
  <div class="schedule-manage-container">
    <el-card class="param-card">
      <template #header>
        <div class="card-header">
          <span>排课概览</span>
        </div>
      </template>
      <div class="param-summary">
        <div class="summary-item">
          <span>教师数量</span>
          <strong>{{ teacherCount }}</strong>
        </div>
        <div class="summary-item">
          <span>教室数量</span>
          <strong>{{ classroomCount }}</strong>
        </div>
        <div class="summary-item">
          <span>课程数量</span>
          <strong>{{ courseCount }}</strong>
        </div>
        <div class="summary-item">
          <span>排课条目</span>
          <strong>{{ totalSchedules }}</strong>
        </div>
      </div>
    </el-card>

    <div class="main-content">
      <div class="left-panel">
        <el-card class="action-card">
          <template #header>
            <span>排课条件</span>
          </template>
          <el-form label-position="top" class="generation-form">
            <el-form-item label="选择课程">
              <el-select
                v-model="selectedCourseIds"
                multiple
                collapse-tags
                filterable
                placeholder="请选择要排课的课程"
              >
                <el-option
                  v-for="course in courseRows"
                  :key="course.id"
                  :label="formatCourseLabel(course)"
                  :value="Number(course.id)"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="选择教师">
              <el-select
                v-model="selectedTeacherIds"
                multiple
                collapse-tags
                filterable
                placeholder="请选择参与排课的教师"
              >
                <el-option
                  v-for="teacher in teacherRows"
                  :key="teacher.id"
                  :label="teacher.name"
                  :value="String(teacher.id)"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="选择教室">
              <el-select
                v-model="selectedClassroomIds"
                multiple
                collapse-tags
                filterable
                placeholder="请选择可用教室"
              >
                <el-option
                  v-for="room in classroomRows"
                  :key="room.id"
                  :label="room.name"
                  :value="Number(room.id)"
                />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                :loading="generateLoading"
                style="width: 100%"
                @click="generateSchedule"
              >
                {{ generateLoading ? '正在排课...' : '生成排课方案' }}
              </el-button>
            </el-form-item>
            <el-form-item v-if="hasPreviewData">
              <el-button
                type="success"
                :loading="saveLoading"
                style="width: 100%"
                @click="saveSchedule"
              >
                保存至数据库
              </el-button>
            </el-form-item>
          </el-form>
          <el-alert
            v-if="gaStats"
            type="info"
            show-icon
            :closable="false"
            class="ga-stats"
          >
            <p>适应度：{{ gaStats.fitness?.toFixed(3) ?? '-' }}</p>
            <p>资源利用率：{{ Math.round((gaStats.utilization ?? 0) * 100) }}%</p>
            <p>冲突数：{{ gaStats.conflict_rate ?? 0 }}</p>
          </el-alert>
        </el-card>

        <el-card style="margin-top: 20px">
          <div class="action-area">
            <el-button
              type="warning"
              size="large"
              style="width: 100%; margin-bottom: 20px"
              @click="refreshSchedule"
              :loading="tableLoading"
            >
              {{ tableLoading ? '同步中...' : '同步数据库数据' }}
            </el-button>

            <div v-if="hasScheduleData" class="stats-area">
              <div class="stat-item">
                <span class="label">冲突率</span>
                <el-progress type="dashboard" :percentage="conflictRate" status="success" :width="80">
                  <template #default="{ percentage }">
                    <span class="percentage-value">{{ percentage }}%</span>
                  </template>
                </el-progress>
              </div>
              <div class="stat-item">
                <span class="label">资源利用率</span>
                <el-progress type="dashboard" :percentage="utilizationRate" :width="80" />
              </div>
              <el-divider />
              <el-button type="primary" plain style="width: 100%" @click="handleExport">
                导出 Excel
              </el-button>
            </div>

            <div v-else class="empty-stats">
              <p>请先点击“生成排课方案”开始安排课程</p>
              <p class="algo-note">提示：遗传算法会自动优化冲突与资源利用率</p>
            </div>
          </div>
        </el-card>
      </div>

      <div class="right-panel">
        <el-card class="table-card">
          <template #header>
            <div class="table-header">
              <el-tabs v-model="activeTab">
                <el-tab-pane label="教师视角" name="teacher" />
                <el-tab-pane label="教室视角" name="classroom" />
              </el-tabs>
              <div class="table-controls">
                <el-radio-group v-model="viewSource" size="small">
                  <el-radio-button label="db">数据库</el-radio-button>
                  <el-radio-button label="preview" :disabled="!hasPreviewData">预览</el-radio-button>
                </el-radio-group>
                <el-tag
                  size="small"
                  :type="viewSource === 'db' ? 'success' : 'warning'"
                  class="view-tag"
                >
                  {{ viewSource === 'db' ? '数据库记录' : '预览结果' }}
                </el-tag>
              </div>
              <div class="legend">
                <span class="legend-dot" style="background: #f0f9eb"></span> 空闲
                <span class="legend-dot" style="background: #ecf5ff; margin-left: 10px"></span> 已排
              </div>
            </div>
          </template>

          <div v-if="!hasScheduleData" class="empty-table">
            <el-empty description="暂无排课数据" />
          </div>

          <div v-else class="schedule-tables-container">
            <div v-for="(schedule, name) in currentViewData" :key="name" class="single-schedule">
              <div class="schedule-title">{{ name }} 课表</div>
              <el-table :data="periods.map((p) => ({ period: p }))" border size="small" style="width: 100%">
                <el-table-column prop="period" label="节次" width="60" align="center" />
                <el-table-column v-for="day in weekDays" :key="day" :label="day" align="center">
                  <template #default="{ row }">
                    <div
                      class="course-cell"
                      :style="{ backgroundColor: schedule[day]?.[row.period]?.color || '' }"
                    >
                      <div v-if="schedule[day]?.[row.period]" class="cell-content">
                        <div class="c-name">{{ schedule[day][row.period].courseName }}</div>
                        <div class="c-info" v-if="activeTab === 'teacher'">
                          {{ schedule[day][row.period].classroomName }}
                        </div>
                        <div class="c-info" v-else>
                          {{ schedule[day][row.period].teacherName }}
                        </div>
                      </div>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<style scoped>
.schedule-manage-container {
  height: 100%;
}
.param-card {
  margin-bottom: 20px;
}
.param-summary {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}
.summary-item {
  flex: 1;
  min-width: 120px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 12px;
  text-align: center;
}
.summary-item span {
  display: block;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.summary-item strong {
  display: block;
  font-size: 20px;
  color: var(--primary-color);
  margin-top: 4px;
}
.main-content {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}
.left-panel {
  width: 280px;
}
.right-panel {
  flex: 1;
}
.ga-stats {
  margin-top: 12px;
}
.stats-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
}
.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 5px;
}
.percentage-value {
  font-size: 14px;
  font-weight: bold;
}
.empty-stats {
  text-align: center;
  color: var(--el-text-color-secondary);
  padding: 20px 0;
}
.algo-note {
  font-size: 12px;
  margin-top: 10px;
  color: #e6a23c;
}
.table-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.table-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.legend {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.legend-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 5px;
  border: 1px solid var(--border-color);
}
.view-tag {
  margin-left: auto;
}
.schedule-tables-container {
  max-height: 600px;
  overflow-y: auto;
}
.single-schedule {
  margin-bottom: 30px;
}
.schedule-title {
  font-weight: bold;
  margin-bottom: 10px;
  color: var(--el-text-color-primary);
  border-left: 4px solid var(--primary-color);
  padding-left: 10px;
}
.course-cell {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  font-size: 12px;
}
.cell-content {
  text-align: center;
  line-height: 1.4;
}
.c-name {
  font-weight: bold;
}
.c-info {
  color: var(--el-text-color-secondary);
  font-size: 10px;
}
</style>
