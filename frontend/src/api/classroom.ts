import axios from 'axios'

export type ResourceStatus = 'in_use' | 'idle' | 'maintenance' | 'scrapped' | 'normal'

export interface ClassroomPayload {
  name: string
  capacity: number
  is_multimedia?: boolean
  code?: string
  location?: string
  devices?: string[]
  status?: ResourceStatus
  remark?: string
}

export interface ClassroomResponse extends ClassroomPayload {
  id: number
  is_multimedia: boolean
  code: string
  devices: string[]
  status: ResourceStatus
}

const BASE_URL = '/classroom'

const authHeaders = () => {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export const classroomApi = {
  async list() {
    const res = await axios.get<ClassroomResponse[]>(`${BASE_URL}/list`, {
      headers: authHeaders()
    })
    return res.data
  },
  async create(payload: ClassroomPayload) {
    const res = await axios.post<ClassroomResponse>(`${BASE_URL}`, payload, {
      headers: authHeaders()
    })
    return res.data
  },
  async update(id: number, payload: Partial<ClassroomPayload>) {
    const res = await axios.put<ClassroomResponse>(`${BASE_URL}/${id}`, payload, {
      headers: authHeaders()
    })
    return res.data
  },
  async remove(id: number) {
    await axios.delete(`${BASE_URL}/${id}`, {
      headers: authHeaders()
    })
  }
}
