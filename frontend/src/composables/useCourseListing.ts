import { computed } from 'vue'
import { useTables } from './useTables'

const DAY_LABELS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const PERIOD_MAP: Record<number, { label: string; time: string }> = {
  0: { label: '第1-2节', time: '08:00-09:40' },
  1: { label: '第3-4节', time: '10:00-11:40' },
  2: { label: '第5-6节', time: '14:00-15:40' },
  3: { label: '第7-8节', time: '16:00-17:40' },
  4: { label: '第9-10节', time: '19:00-20:40' },
  5: { label: '第11-12节', time: '20:40-22:00' }
}

export interface ListedCourse {
  id: number
  name: string
  credit: number
  teacher: string
  remain: number
  type: 'compulsory' | 'elective'
  time: string
}

const formatSchedule = (entries: any[], classrooms: Record<number, any>) => {
  if (!entries.length) return '未排课'
  return entries
    .slice()
    .sort((a, b) => (a.day - b.day) || (a.period - b.period))
    .map((item) => {
      const dayLabel = DAY_LABELS[item.day] || `周${item.day + 1}`
      const periodInfo = PERIOD_MAP[item.period] || { label: `第${item.period + 1}节`, time: '' }
      const classroom = classrooms[item.classroom_id]?.name || '待定教室'
      const timeRange = periodInfo.time ? `(${periodInfo.time})` : ''
      return `${dayLabel} · ${periodInfo.label} · ${classroom}${timeRange}` 
    })
    .join(' / ')
}

export const useCourseListing = () => {
  const requiredTables = ['courses', 'teachers', 'course_selections', 'schedules', 'classrooms']
  const { rows, loading, error, reloadTables, tableStore } = useTables(requiredTables)

  const teacherMap = computed(() => {
    const map: Record<string, any> = {}
    rows('teachers').forEach((teacher: any) => {
      map[teacher.id] = teacher
    })
    return map
  })

  const classroomMap = computed(() => {
    const map: Record<number, any> = {}
    rows('classrooms').forEach((room: any) => {
      map[room.id] = room
    })
    return map
  })

  const selectionCounts = computed(() => {
    const counts: Record<number, number> = {}
    rows('course_selections').forEach((sel: any) => {
      const courseId = sel.course_id
      counts[courseId] = (counts[courseId] || 0) + 1
    })
    return counts
  })

  const schedulesByCourse = computed(() => {
    const grouped: Record<number, any[]> = {}
    rows('schedules').forEach((item: any) => {
      if (!grouped[item.course_id]) {
        grouped[item.course_id] = []
      }
      grouped[item.course_id].push(item)
    })
    return grouped
  })

  const courses = computed<ListedCourse[]>(() => {
    return rows('courses').map((course: any) => {
      const teacher = teacherMap.value[course.teacher_id]
      const scheduleEntries = schedulesByCourse.value[course.id] || []
      const remain = Math.max((course.capacity || 0) - (selectionCounts.value[course.id] || 0), 0)
      return {
        id: course.id,
        name: course.name,
        credit: course.credit,
        teacher: teacher?.name || '未分配教师',
        remain,
        type: course.course_type === '必修' ? 'compulsory' : 'elective',
        time: formatSchedule(scheduleEntries, classroomMap.value)
      }
    })
  })

  return {
    loading,
    error,
    reloadTables,
    tableStore,
    courses
  }
}
