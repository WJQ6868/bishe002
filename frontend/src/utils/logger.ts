import axios from 'axios'

const API_LOG_URL = import.meta.env.VITE_FRONTEND_LOG_API || ''

export const sendLog = (level: string, message: string, data?: any) => {
  if (!API_LOG_URL) return
  // Prevent infinite loop if logging the log request itself
  if (data?.url?.includes(API_LOG_URL)) return

  const entry = {
    level,
    message,
    timestamp: new Date().toISOString(),
    data
  }
  
  // Use fetch to avoid axios interceptor loops
  try {
    fetch(API_LOG_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(entry)
    }).catch(err => console.error('Failed to send log', err))
  } catch (e) {
      console.error(e)
  }
}
