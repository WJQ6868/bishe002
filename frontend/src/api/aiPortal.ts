import axios from 'axios'

export interface PublicAiModelApi {
  id: number
  name: string
  provider: string
  model_name: string
  endpoint: string
  enabled: boolean
  is_default: boolean
  updated_at?: string
}

export interface TeacherCourse {
  id: number
  name: string
}

export interface TeacherKbDocument {
  id: number
  course_id?: number | null
  subject: string
  title: string
  original_filename: string
  url: string
  file_ext: string
  file_size: number
  created_at: string
  updated_at?: string
}

export interface StudentCourseAiItem {
  course_id: number
  course_name: string
  teacher_id?: string | null
  teacher_name: string
  teacher_kb_updated_at?: string | null
  selected_model_api_id?: number | null
  favorite: boolean
}

export interface CustomerServiceConfig {
  welcome_str: string
  recommend_questions: string[]
  search_placeholder: string
  system_prompt_template?: string | null
}

export interface LessonPlanTask {
  id: number
  title: string
  outline?: string | null
  course_id?: number | null
  status: string
  result?: string | null
  error_message?: string | null
  knowledge_base_id?: number | null
  model_api_id?: number | null
  created_at: string
  updated_at?: string | null
  completed_at?: string | null
}

export interface LessonPlanTaskCreatePayload {
  title: string
  outline?: string
  course_id?: number
}

export interface LessonPlanTaskResultPayload {
  status?: string
  result?: string
  error_message?: string
}

export interface AiWorkflowApp {
  code: string
  type: string
  name: string
  status: string
  knowledge_base_id?: number | null
  model_api_id?: number | null
  owner_user_id?: number | null
  course_id?: number | null
  settings?: Record<string, any>
  updated_at?: string | null
}

const authHeaders = () => {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export const aiPortalApi = {
  async listPublicModelApis() {
    const res = await axios.get<PublicAiModelApi[]>('/ai/public/model-apis', { headers: authHeaders() })
    return res.data
  },

  async getCustomerServiceConfig() {
    const res = await axios.get<CustomerServiceConfig>('/ai/customer-service/config', { headers: authHeaders() })
    return res.data
  },

  async listCustomerServiceApps() {
    const res = await axios.get<AiWorkflowApp[]>('/ai/customer-service/apps', { headers: authHeaders() })
    return res.data
  },

  async listCourseAssistantApps(courseId?: number) {
    const res = await axios.get<AiWorkflowApp[]>('/ai/course-assistant/apps', {
      headers: authHeaders(),
      params: courseId ? { course_id: courseId } : undefined
    })
    return res.data
  },

  // teacher
  async listTeacherCourses() {
    const res = await axios.get<TeacherCourse[]>('/ai/teacher/courses', { headers: authHeaders() })
    return res.data
  },
  async listTeacherKbDocuments(courseId?: number) {
    const res = await axios.get<TeacherKbDocument[]>('/ai/teacher/kb/documents', {
      headers: authHeaders(),
      params: courseId ? { course_id: courseId } : undefined
    })
    return res.data
  },
  async uploadTeacherKbDocument(params: { title: string; subject?: string; course_id?: number; file: File }) {
    const form = new FormData()
    form.append('title', params.title)
    form.append('subject', params.subject || '')
    if (params.course_id) form.append('course_id', String(params.course_id))
    form.append('file', params.file)
    const res = await axios.post<TeacherKbDocument>('/ai/teacher/kb/upload', form, {
      headers: { ...authHeaders() }
    })
    return res.data
  },
  async updateTeacherKbDocument(docId: number, payload: { title?: string; subject?: string; course_id?: number | null }) {
    const res = await axios.put<TeacherKbDocument>(`/ai/teacher/kb/documents/${docId}`, payload, { headers: authHeaders() })
    return res.data
  },
  async replaceTeacherKbDocument(docId: number, file: File) {
    const form = new FormData()
    form.append('file', file)
    const res = await axios.post<TeacherKbDocument>(`/ai/teacher/kb/documents/${docId}/replace`, form, {
      headers: { ...authHeaders() }
    })
    return res.data
  },
  async deleteTeacherKbDocument(docId: number) {
    await axios.delete(`/ai/teacher/kb/documents/${docId}`, { headers: authHeaders() })
  },

  // student
  async listStudentCourseAis() {
    const res = await axios.get<StudentCourseAiItem[]>('/ai/student/course-ai/list', { headers: authHeaders() })
    return res.data
  },
  async selectStudentCourseAi(courseId: number, modelApiId: number | null) {
    await axios.put('/ai/student/course-ai/select', { course_id: courseId, model_api_id: modelApiId }, { headers: authHeaders() })
  },
  async favoriteStudentCourseAi(courseId: number, favorite: boolean) {
    await axios.put('/ai/student/course-ai/favorite', { course_id: courseId, favorite }, { headers: authHeaders() })
  },
  // lesson plan tasks
  async listLessonPlanTasks(courseId?: number) {
    const res = await axios.get<LessonPlanTask[]>('/ai/teacher/lesson-plan/tasks', {
      headers: authHeaders(),
      params: courseId ? { course_id: courseId } : undefined
    })
    return res.data
  },
  async createLessonPlanTask(payload: LessonPlanTaskCreatePayload) {
    const res = await axios.post<LessonPlanTask>('/ai/teacher/lesson-plan/tasks', payload, { headers: authHeaders() })
    return res.data
  },
  async updateLessonPlanTaskResult(taskId: number, payload: LessonPlanTaskResultPayload) {
    const res = await axios.put<LessonPlanTask>(`/ai/teacher/lesson-plan/tasks/${taskId}/result`, payload, { headers: authHeaders() })
    return res.data
  }
}

