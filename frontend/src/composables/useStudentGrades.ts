import { computed } from 'vue'
import { useTables } from '@/composables/useTables'

export interface StudentGradeDetail {
  usualScore: number
  midtermScore: number
  finalScore: number
  comment: string
}

export interface StudentGradeRecord {
  id: number
  courseName: string
  courseId: string
  credit: number
  score: number
  gpa: number
  assessmentType: string
  semester: string
  teacherName: string
  details: StudentGradeDetail
}

export const calculateGPA = (score: number): number => {
  if (score < 60) return 0
  return Math.max(0, Number(((score / 10) - 5).toFixed(1)))
}

export const getGradeLevel = (score: number): string => {
  if (score >= 90) return '优秀'
  if (score >= 80) return '良好'
  if (score >= 60) return '及格'
  return '不及格'
}

export const getGradeLevelColor = (score: number): string => {
  if (score >= 80) return '#52C41A'
  if (score < 60) return '#F56C6C'
  return '#303133'
}

export const useStudentGrades = () => {
  const studentAccount = localStorage.getItem('user_account') || ''
  const { rows, loading, error, reloadTables } = useTables(['grades', 'courses', 'teachers'])

  const courseMap = computed<Record<number, any>>(() => {
    const map: Record<number, any> = {}
    rows('courses').forEach((course: any) => {
      map[course.id] = course
    })
    return map
  })

  const teacherMap = computed<Record<string, any>>(() => {
    const map: Record<string, any> = {}
    rows('teachers').forEach((teacher: any) => {
      map[teacher.id] = teacher
    })
    return map
  })

  const grades = computed<StudentGradeRecord[]>(() => {
    return rows('grades')
      .filter((grade: any) => !studentAccount || grade.student_id === studentAccount)
      .map((grade: any) => {
        const course = courseMap.value[grade.course_id]
        const teacher = course ? teacherMap.value[course.teacher_id] : undefined
        const semester = course?.create_time ? course.create_time.slice(0, 7) : '未分类'
        const scoreValue = Number(grade.score) || 0
        return {
          id: grade.id,
          courseName: course?.name || '未设置课程',
          courseId: course ? String(course.id) : String(grade.course_id),
          credit: course?.credit || 0,
          score: Math.round(scoreValue),
          gpa: calculateGPA(scoreValue),
          assessmentType: grade.exam_type === 'final' ? '考试' : '考查',
          semester,
          teacherName: teacher?.name || course?.teacher_id || '未设置',
          details: {
            usualScore: Math.round(scoreValue * 0.3),
            midtermScore: Math.round(scoreValue * 0.3),
            finalScore: Math.round(scoreValue * 0.4),
            comment: '来源于数据库成绩记录'
          }
        }
      })
  })

  return {
    grades,
    loading,
    error,
    reloadTables
  }
}
