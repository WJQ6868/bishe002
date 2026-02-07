const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

type StreamHandler = (chunk: string) => void

interface StreamQaPayload {
  user_id: string
  question: string
  history_flag: boolean
  model?: string
  course_id?: number
  workflow?: string
}

const buildHeaders = () => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream'
  }
  const token = localStorage.getItem('token')
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  return headers
}

const parseSseChunk = (raw: string, onChunk: StreamHandler) => {
  if (!raw) return
  const normalized = raw.replace(/\r\n/g, '\n')
  const lines = normalized.split('\n')
  for (const line of lines) {
    if (!line.startsWith('data:')) continue
    const payload = line.slice(5).trim()
    if (!payload || payload === '[DONE]') continue
    try {
      const parsed = JSON.parse(payload)
      const content = parsed?.content ?? parsed?.message ?? ''
      if (content) onChunk(String(content))
    } catch {
      onChunk(payload)
    }
  }
}

export const streamQA = async (
  userId: string,
  question: string,
  historyFlag: boolean,
  onChunk: StreamHandler,
  model?: string,
  courseId?: number,
  workflow?: string
) => {
  const payload: StreamQaPayload = {
    user_id: userId,
    question,
    history_flag: historyFlag,
    model,
    course_id: courseId,
    workflow
  }

  const res = await fetch(`${API_BASE}/ai_qa/qa/stream`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(payload)
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || res.statusText)
  }

  const contentType = res.headers.get('content-type') || ''
  if (!contentType.includes('text/event-stream')) {
    const text = await res.text().catch(() => '')
    if (text) {
      try {
        const parsed = JSON.parse(text)
        const content = parsed?.content ?? parsed?.detail ?? parsed?.message ?? text
        onChunk(String(content))
      } catch {
        onChunk(text)
      }
    }
    return
  }

  const reader = res.body?.getReader()
  if (!reader) return
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    buffer = buffer.replace(/\r\n/g, '\n')
    let idx = buffer.indexOf('\n\n')
    while (idx !== -1) {
      const raw = buffer.slice(0, idx).trim()
      buffer = buffer.slice(idx + 2)
      parseSseChunk(raw, onChunk)
      idx = buffer.indexOf('\n\n')
    }
  }

  if (buffer.trim()) {
    parseSseChunk(buffer.trim(), onChunk)
  }
}
