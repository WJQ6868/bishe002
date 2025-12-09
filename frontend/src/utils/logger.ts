import axios from 'axios'

const API_LOG_URL = '/api/log/frontend'

export const sendLog = (level: string, message: string, data?: any) => {
  // Prevent infinite loop if logging the log request itself
  if (data?.url?.includes('/api/log/frontend')) return

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
