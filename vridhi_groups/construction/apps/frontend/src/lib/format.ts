export const currency = (value?: string | number, code = 'INR') => new Intl.NumberFormat('en-IN', { style: 'currency', currency: code, maximumFractionDigits: 0 }).format(Number(value || 0))
export const dateLabel = (value: string) => new Date(`${value}T00:00:00`).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
export const todayISO = new Date().toISOString().slice(0, 10)
export const todayLabel = new Intl.DateTimeFormat('en-IN', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' }).format(new Date())

export function statusClass(status: string) {
  return status === 'Active' ? 'active' : status === 'On Hold' ? 'hold' : status === 'Completed' ? 'complete' : status === 'Cancelled' ? 'cancelled' : 'planning'
}
