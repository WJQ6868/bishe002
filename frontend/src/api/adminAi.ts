import axios from 'axios'

export type AiProvider = 'dashscope_openai' | 'ark_responses'

export type AiFeatureKey = 'customer_service' | 'lesson_plan' | 'course_assistant'

export interface AiModelApiItem {
  id: number
  name: string
  provider: AiProvider
  provider_brand?: string
  model_name: string
  endpoint: string
  api_header?: string | null
  api_version?: string | null
  timeout_seconds: number
  quota_per_hour: number
  temperature?: number | null
  max_output_tokens?: number | null
  enabled: boolean
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface AiModelApiCreate {
  name: string
  provider: AiProvider
  provider_brand?: string
  model_name: string
  endpoint: string
  api_key: string
  api_header?: string | null
  api_version?: string | null
  timeout_seconds: number
  quota_per_hour: number
  temperature?: number | null
  max_output_tokens?: number | null
  enabled: boolean
  is_default: boolean
}

export type AiModelApiUpdate = Partial<AiModelApiCreate>

export interface AiModelApiTestRequest {
  api_id?: number
  provider: AiProvider
  model_name: string
  endpoint: string
  api_key: string
  timeout_seconds: number
  prompt?: string
}

export interface AiModelApiTestResponse {
  ok: boolean
  message: string
  output?: string
}

export interface AiKbSubject {
  id: number
  name: string
  stage?: string | null
  enabled?: boolean
  created_at: string
}

export interface AiKbDocument {
  id: number
  subject_id: number
  knowledge_base_id?: number
  title: string
  original_filename: string
  url: string
  file_ext: string
  file_size: number
  enabled?: boolean
  created_at: string
  updated_at?: string
  chunk_count?: number
}

export interface AiCustomModelItem {
  id: number
  name: string
  remark?: string | null
  enabled: boolean
  base_model_api_id: number
  base_model_name?: string
  primary_subject_id?: number | null
  primary_subject_name?: string | null
  kb_documents?: Array<{ id: number; title: string; subject_id: number; subject_name?: string }>
  created_at: string
  updated_at?: string
}

export interface AiCustomModelCreate {
  name: string
  remark?: string
  enabled: boolean
  base_model_api_id: number
  primary_subject_id?: number | null
  kb_document_ids: number[]
}

export type AiCustomModelUpdate = Partial<AiCustomModelCreate>

export interface AiFeatureBindingOut {
  feature: AiFeatureKey
  custom_model_ids: number[]
}

export interface AiCustomerServiceSettings {
  welcome_str: string
  recommend_questions: string[]
  search_placeholder: string
  system_prompt_template?: string | null
}

export interface AiKnowledgeBaseItem {
  id: number
  slug: string
  name: string
  description?: string | null
  owner_type: string
  owner_user_id?: number | null
  course_id?: number | null
  feature?: string | null
  is_default: boolean
  document_count: number
  chunk_count: number
  created_at: string
  updated_at?: string | null
}

export interface AiKnowledgeBaseCreate {
  name: string
  slug?: string
  description?: string
  feature?: string
  is_default?: boolean
}

export interface AiWorkflowAppItem {
  code: string
  type: string
  name: string
  status: string
  knowledge_base_id?: number | null
  model_api_id?: number | null
  owner_user_id?: number | null
  course_id?: number | null
  settings: Record<string, any>
  updated_at?: string | null
}

export interface AiWorkflowAppUpdate {
  name?: string
  knowledge_base_id?: number | null
  model_api_id?: number | null
  status?: string
  settings?: Record<string, any>
}

// Axios 全局已设置 baseURL=/api（main.ts），这里保持相对路径，避免 /api/api 重复
const BASE_URL = '/admin/ai'

const authHeaders = () => {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export const adminAiApi = {
  async listModelApis() {
    const res = await axios.get<AiModelApiItem[]>(`${BASE_URL}/model-apis`, { headers: authHeaders() })
    return res.data
  },
  async createModelApi(payload: AiModelApiCreate) {
    const res = await axios.post<AiModelApiItem>(`${BASE_URL}/model-apis`, payload, { headers: authHeaders() })
    return res.data
  },
  async updateModelApi(id: number, payload: AiModelApiUpdate) {
    const res = await axios.put<AiModelApiItem>(`${BASE_URL}/model-apis/${id}`, payload, { headers: authHeaders() })
    return res.data
  },
  async deleteModelApi(id: number) {
    await axios.delete(`${BASE_URL}/model-apis/${id}`, { headers: authHeaders() })
  },
  async testModelApi(payload: AiModelApiTestRequest) {
    const res = await axios.post<AiModelApiTestResponse>(`${BASE_URL}/model-apis/test`, payload, { headers: authHeaders() })
    return res.data
  },
  async updateModelKbLinks(modelApiId: number, kbDocumentIds: number[]) {
    const res = await axios.put(`${BASE_URL}/model-apis/${modelApiId}/kb`, { kb_document_ids: kbDocumentIds }, { headers: authHeaders() })
    return res.data
  },

  async listSubjects() {
    const res = await axios.get<AiKbSubject[]>(`${BASE_URL}/kb/subjects`, { headers: authHeaders() })
    return res.data
  },
  async createSubject(name: string) {
    const res = await axios.post<AiKbSubject>(`${BASE_URL}/kb/subjects`, { name }, { headers: authHeaders() })
    return res.data
  },
  async listDocuments(subjectId: number) {
    const res = await axios.get<AiKbDocument[]>(`${BASE_URL}/kb/documents`, {
      headers: authHeaders(),
      params: { subject_id: subjectId }
    })
    return res.data
  },
  async uploadDocument(subjectId: number, title: string, file: File) {
    const form = new FormData()
    form.append('subject_id', String(subjectId))
    form.append('title', title)
    form.append('file', file)
    const res = await axios.post<AiKbDocument>(`${BASE_URL}/kb/upload`, form, {
      headers: { ...authHeaders() }
    })
    return res.data
  },
  async deleteDocument(docId: number) {
    await axios.delete(`${BASE_URL}/kb/documents/${docId}`, { headers: authHeaders() })
  },

  // --------- 定制模型（Dify 编排） ---------
  async listCustomModels() {
    const res = await axios.get<AiCustomModelItem[]>(`${BASE_URL}/custom-models`, { headers: authHeaders() })
    return res.data
  },
  async createCustomModel(payload: AiCustomModelCreate) {
    const res = await axios.post<AiCustomModelItem>(`${BASE_URL}/custom-models`, payload, { headers: authHeaders() })
    return res.data
  },
  async updateCustomModel(id: number, payload: AiCustomModelUpdate) {
    const res = await axios.put<AiCustomModelItem>(`${BASE_URL}/custom-models/${id}`, payload, { headers: authHeaders() })
    return res.data
  },
  async deleteCustomModel(id: number) {
    await axios.delete(`${BASE_URL}/custom-models/${id}`, { headers: authHeaders() })
  },

  // --------- AI 设置：功能绑定 ---------
  async getFeatureBindings(feature: AiFeatureKey) {
    const res = await axios.get<AiFeatureBindingOut>(`${BASE_URL}/feature-bindings/${feature}`, { headers: authHeaders() })
    return res.data
  },
  async saveFeatureBindings(feature: AiFeatureKey, customModelIds: number[]) {
    const res = await axios.put<AiFeatureBindingOut>(`${BASE_URL}/feature-bindings/${feature}`, { custom_model_ids: customModelIds }, { headers: authHeaders() })
    return res.data
  },

  // --------- AI 客服设置 ---------
  async getCustomerServiceSettings() {
    const res = await axios.get<AiCustomerServiceSettings>(`${BASE_URL}/customer-service/settings`, { headers: authHeaders() })
    return res.data
  },
  async updateCustomerServiceSettings(payload: Partial<AiCustomerServiceSettings>) {
    const res = await axios.put<AiCustomerServiceSettings>(`${BASE_URL}/customer-service/settings`, payload, { headers: authHeaders() })
    return res.data
  },

  // --------- AI 工作流：知识库 ---------
  async listWorkflowKnowledgeBases(feature?: string) {
    const res = await axios.get<AiKnowledgeBaseItem[]>(`${BASE_URL}/workflows/knowledge-bases`, {
      headers: authHeaders(),
      params: feature ? { feature } : undefined
    })
    return res.data
  },
  async createWorkflowKnowledgeBase(payload: AiKnowledgeBaseCreate) {
    const res = await axios.post<AiKnowledgeBaseItem>(`${BASE_URL}/workflows/knowledge-bases`, payload, { headers: authHeaders() })
    return res.data
  },
  async updateWorkflowKnowledgeBase(id: number, payload: Partial<AiKnowledgeBaseCreate>) {
    const res = await axios.put<AiKnowledgeBaseItem>(`${BASE_URL}/workflows/knowledge-bases/${id}`, payload, { headers: authHeaders() })
    return res.data
  },
  async deleteWorkflowKnowledgeBase(id: number) {
    await axios.delete(`${BASE_URL}/workflows/knowledge-bases/${id}`, { headers: authHeaders() })
  },
  async listWorkflowDocuments(kbId: number) {
    const res = await axios.get<AiKbDocument[]>(`${BASE_URL}/workflows/knowledge-bases/${kbId}/documents`, { headers: authHeaders() })
    return res.data
  },
  async uploadWorkflowDocument(kbId: number, title: string, file: File) {
    const form = new FormData()
    form.append('title', title)
    form.append('file', file)
    const res = await axios.post<AiKbDocument>(`${BASE_URL}/workflows/knowledge-bases/${kbId}/documents/upload`, form, {
      headers: { ...authHeaders() }
    })
    return res.data
  },
  async createWorkflowDocumentManual(kbId: number, payload: { title: string; content: string }) {
    const res = await axios.post<AiKbDocument>(`${BASE_URL}/workflows/knowledge-bases/${kbId}/documents/manual`, payload, { headers: authHeaders() })
    return res.data
  },
  async deleteWorkflowDocument(docId: number) {
    await axios.delete(`${BASE_URL}/workflows/documents/${docId}`, { headers: authHeaders() })
  },

  // --------- AI 工作流：应用 ---------
  async listWorkflowApps() {
    const res = await axios.get<AiWorkflowAppItem[]>(`${BASE_URL}/workflows/apps`, { headers: authHeaders() })
    return res.data
  },
  async createWorkflowApp(payload: AiWorkflowAppUpdate & { code: string; type: string; name: string }) {
    const res = await axios.post<AiWorkflowAppItem>(`${BASE_URL}/workflows/apps`, payload, { headers: authHeaders() })
    return res.data
  },
  async updateWorkflowApp(code: string, payload: AiWorkflowAppUpdate) {
    const res = await axios.put<AiWorkflowAppItem>(`${BASE_URL}/workflows/apps/${code}`, payload, { headers: authHeaders() })
    return res.data
  },
  async deleteWorkflowApp(code: string) {
    await axios.delete(`${BASE_URL}/workflows/apps/${code}`, { headers: authHeaders() })
  }
}
