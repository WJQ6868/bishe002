import axios from 'axios'

export interface CollegeItem {
  id: number
  name: string
  code: string
  status: number
}

export interface MajorItem {
  id: number
  name: string
  code: string | null
  status: number
  college_id: number | null
}

export interface ClassItem {
  id: number
  name: string
  student_count: number
}

export interface AcademicClassItem {
  id: number
  name: string
  code: string | null
  status: number
  student_count: number
  major_id: number
  major_name?: string | null
  // legacy fields (kept for backward compatibility)
  teacher_id?: string | null
  teacher_name?: string | null
  // new fields: head teacher (班主任)
  head_teacher_no?: string | null
  head_teacher_name?: string | null
}

export interface StudentItem {
  id: number
  student_code: string
  name: string
}

export interface AcademicStudentItem {
  id: number
  student_code: string
  name: string
  gender: number | null
  mobile: string | null
  status: number
  class_id: number
  class_name?: string | null
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

export const fetchColleges = () =>
  axios.get<{ items: CollegeItem[] }>('/api/college/list').then((res) => res.data.items)

export const addCollege = (payload: { name: string; code: string; status?: number }) =>
  axios.post('/api/college/add', payload)

export const updateCollege = (id: number, payload: Partial<{ name: string; code: string; status: number }>) =>
  axios.put(`/api/college/${id}`, payload)

export const deleteCollege = (id: number) => axios.delete(`/api/college/${id}`)

export const fetchMajors = (collegeId?: number) =>
  axios
    .get<{ items: MajorItem[] }>('/api/major/list', { params: { college_id: collegeId } })
    .then((res) => res.data.items)

export const addMajor = (payload: { name: string; code: string; status?: number; college_id?: number }) =>
  axios.post('/api/major/add', payload)

export const updateMajor = (id: number, payload: Partial<{ name: string; code: string; status: number; college_id: number }>) =>
  axios.put(`/api/major/${id}`, payload)

export const deleteMajor = (id: number) => axios.delete(`/api/major/${id}`)

export const fetchClasses = (majorId: number) =>
  axios
    .get<{ items: ClassItem[] }>('/api/major/class/list', { params: { major_id: majorId } })
    .then((res) => res.data.items)

export const fetchAcademicClasses = (params: { college_id?: number; major_id?: number } = {}) =>
  axios.get<{ items: AcademicClassItem[] }>('/api/class/list', { params }).then((res) => res.data.items)

export const addAcademicClass = (payload: {
  major_id: number
  name: string
  code?: string | null
  status?: number
  teacher_id?: string | null
  student_count?: number
}) => axios.post('/api/class/add', payload)

export const updateAcademicClass = (id: number, payload: Partial<{ major_id: number; name: string; code: string | null; status: number; teacher_id: string | null; student_count: number }>) =>
  axios.put(`/api/class/${id}`, payload)

export const bindClassTeacher = (id: number, teacher_id: string) =>
  axios.put(`/api/class/${id}/teacher`, { teacher_id })

export const bindClassHeadTeacher = (id: number, teacher_no: string | null) =>
  axios.put(`/api/class/${id}/head-teacher`, { teacher_no })

export const deleteAcademicClass = (id: number) => axios.delete(`/api/class/${id}`)

export const fetchStudents = (classId: number) =>
  axios
    .get<{ items: StudentItem[] }>('/api/class/student/list', { params: { class_id: classId } })
    .then((res) => res.data.items)

export const fetchAcademicStudents = (params: { class_id?: number } = {}) =>
  axios.get<{ items: AcademicStudentItem[] }>('/api/student/list', { params }).then((res) => res.data.items)

export const getAcademicStudent = (id: number) => axios.get<AcademicStudentItem>(`/api/student/${id}`).then((res) => res.data)

export const addAcademicStudent = (payload: {
  class_id: number
  student_code: string
  name: string
  gender?: number | null
  mobile?: string | null
  status?: number
}) => axios.post('/api/student/add', payload)

export const updateAcademicStudent = (id: number, payload: Partial<{ class_id: number; student_code: string; name: string; gender: number | null; mobile: string | null; status: number }>) =>
  axios.put(`/api/student/${id}`, payload)

export const deleteAcademicStudent = (id: number) => axios.delete(`/api/student/${id}`)

export const fetchCourses = (majorId: number) =>
  axios
    .get<{ items: CourseItem[] }>('/api/major/course/list', { params: { major_id: majorId } })
    .then((res) => res.data.items)

export const fetchCourseTeachers = (courseId: number) =>
  axios
    .get<{ items: TeacherItem[] }>('/api/course/teacher/list', { params: { course_id: courseId } })
    .then((res) => res.data.items)
