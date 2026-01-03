const API_PREFIX = (import.meta as any).env?.VITE_API_BASE_URL || '/api'
const withPrefix = (path: string) => `${API_PREFIX.replace(/\/$/, '')}${path}`

export async function streamQA(
  userId: string,
  question: string,
  historyFlag: boolean,
  onChunk: (text: string) => void,
  model?: string,
  courseId?: number,
  workflow?: string
) {
  const res = await fetch(withPrefix('/ai_qa/qa/stream'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, question, history_flag: historyFlag, model, course_id: courseId, workflow })
  })
  if (!res.ok || !res.body) {
    throw new Error('AI 调用失败')
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let got = false
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      const s = line.trim()
      if (s.startsWith('data:')) {
        const jsonStr = s.slice(5).trim()
        try {
          const obj = JSON.parse(jsonStr)
          const content = obj.content || ''
          if (content) {
            got = true
            onChunk(content)
          }
        } catch {}
      }
    }
  }
  return got
}

export async function streamCustomerServiceQA(
  userId: string,
  question: string,
  historyFlag: boolean,
  onChunk: (text: string) => void,
  model?: string,
  courseId?: number,
  workflow?: string
) {
  const res = await fetch(withPrefix('/ai_qa/customer-service/stream'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream,application/json' },
    body: JSON.stringify({ user_id: userId, question, history_flag: historyFlag, model, course_id: courseId, workflow })
  })
  if (!res.ok || !res.body) {
    throw new Error('AI 调用失败')
  }

  // 后端已改为非流式 JSON 优先，先检查 content-type
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) {
    const data = await res.json()
    const content = data?.content || data?.message || ''
    if (content) onChunk(content)
    return !!content
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let got = false
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      const s = line.trim()
      if (s.startsWith('data:')) {
        const jsonStr = s.slice(5).trim()
        try {
          const obj = JSON.parse(jsonStr)
          const content = obj.content || ''
          if (content) {
            got = true
            onChunk(content)
          }
        } catch {}
      }
    }
  }
  return got
}
