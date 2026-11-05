type ClientEvent = { event: string; method?: string; status?: number; duration_ms?: number; request_id?: string }
let csrfToken = ''
const pending: ClientEvent[] = []
let initialized = false

export function setLoggingCsrf(token: string) { csrfToken = token }
export function logClientEvent(entry: ClientEvent) {
  if (pending.length < 30) pending.push(entry)
}
async function flushLogs() {
  if (!csrfToken || !pending.length) return
  const batch = pending.splice(0, 30)
  try {
    await fetch('/api/v1/client-logs', { method: 'POST', credentials: 'include', keepalive: true,
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken }, body: JSON.stringify(batch) })
  } catch { return }
}
export function initializeClientLogging() {
  if (initialized) return
  initialized = true
  window.addEventListener('error', () => logClientEvent({ event: 'javascript_error' }))
  window.addEventListener('unhandledrejection', () => logClientEvent({ event: 'unhandled_rejection' }))
  for (const level of ['warn', 'error'] as const) {
    const original = console[level].bind(console)
    console[level] = (...args: unknown[]) => { original(...args); logClientEvent({ event: `console_${level}` }) }
  }
  window.setInterval(() => void flushLogs(), 3000)
  window.addEventListener('pagehide', () => void flushLogs())
}