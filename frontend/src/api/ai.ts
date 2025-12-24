export async function streamQA(
  userId: string,
  question: string,
  historyFlag: boolean,
  onChunk: (text: string) => void,
  model?: string
) {
  const res = await fetch('/api/ai_qa/qa/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, question, history_flag: historyFlag, model })
  })
  if (!res.ok || !res.body) {
    throw new Error('AI接口不可用')
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
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
          if (content) onChunk(content)
        } catch {}
      }
    }
  }
}
