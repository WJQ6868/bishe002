import axios from 'axios'

export interface MajorItem {
  id: number
  name: string
}

export interface ClassItem {
  id: number
  name: string
  student_count: number
}

export interface StudentItem {
  id: number
  student_code: string
  name: string
}

export interface CourseItem {
  id: number
  name: string
  credit: number
  class_hours: number
}

export interface TeacherItem {
  teacher_id: string
  name: string
}

export const fetchMajors = () =>
  axios.get<{ items: MajorItem[] }>('/api/major/list').then((res) => res.data.items)

export const fetchClasses = (majorId: number) =>
  axios
    .get<{ items: ClassItem[] }>('/api/major/class/list', { params: { major_id: majorId } })
    .then((res) => res.data.items)

export const fetchStudents = (classId: number) =>
  axios
    .get<{ items: StudentItem[] }>('/api/class/student/list', { params: { class_id: classId } })
    .then((res) => res.data.items)

export const fetchCourses = (majorId: number) =>
  axios
    .get<{ items: CourseItem[] }>('/api/major/course/list', { params: { major_id: majorId } })
    .then((res) => res.data.items)

export const fetchCourseTeachers = (courseId: number) =>
  axios
    .get<{ items: TeacherItem[] }>('/api/course/teacher/list', { params: { course_id: courseId } })
    .then((res) => res.data.items)
