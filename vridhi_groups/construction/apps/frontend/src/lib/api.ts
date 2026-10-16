import { logClientEvent, setLoggingCsrf } from './logging'

export type Page<T> = { items: T[]; page: number; page_size: number; total: number }
export type AuditModule = 'overview' | 'procurement' | 'inventory' | 'cashflow' | 'labor' | 'audit'
export type ProjectAuditEntry = { id: string; username: string; name: string; occurred_at: string; activity: string; action: string; record_type: string; record_id: string | null; details: Record<string, unknown> | null }
export type ProjectModulePermission = { access: 'allow' | 'block'; read: { export_report: boolean }; write: { mode: 'all' | 'partial'; actions: Record<string, boolean> } }
export type ProjectPermissions = Record<'overview' | 'procurement' | 'inventory' | 'cashflow' | 'labor' | 'users', ProjectModulePermission>
export type User = { id: string; username: string; email: string | null; phone?: string | null; name: string; global_access?: boolean; global_permissions?: ProjectPermissions | null; users_permissions?: ProjectModulePermission | null; audit_permissions?: ProjectModulePermission | null; active?: boolean; assigned_project_ids?: string[]; assigned_projects?: string[]; project_permissions?: Record<string, ProjectPermissions | null>; manageable_actions?: string[]; capabilities?: string[]; permissions?: Record<string, { read: boolean; write: boolean; export_report?: boolean; reset_password?: boolean; activate_deactivate?: boolean; delete_user?: boolean; history?: boolean }> }
export type UserHistoryEntry = { id: string; action: string; entity_type: string; entity_id: string | null; occurred_at: string; actor: string; details: Record<string, unknown> | null }
export type Project = { id: string; name: string; location: string; status: string; eligible_statuses: string[]; baseline_budget: string; contract_value?: string; actual_cost?: string; hold_reason?: string | null; currency: string; start_date: string; version: number; permissions?: ProjectPermissions | null }
export type Session = { user: User; expires_at: string; csrf_token: string }
export type RBACResource = { resource: 'overview' | 'procurement' | 'inventory' | 'cashflow' | 'users'; label: string; description: string }
export type RBACMatrix = Record<string, Record<RBACResource['resource'], { read: boolean; write: boolean }>>
export type RBACConfiguration = { roles: { name: string; description: string; is_system: boolean }[]; resources: RBACResource[]; matrix: RBACMatrix }
export type Dashboard = { project_id: string; as_of: string; currency: string; budget: string; approved_contract_value: string; actual_cost: string; open_commitments: string; invoiced_amount: string; cash_received: string; forecast_cost: string; margin_percent: string; labor_cost_breakdown?: { contract_claims: string; direct_workers: string }; cost_breakdown: { category: string; amount: string | null; recorded: boolean }[]; monthly_costs: { month: string; amount: string }[] }
export type PurchaseOrder = { id: string; number: string; order_date: string; vendor: { id: string; name: string }; item_names: string[]; currency: string; total: string; paid_to_date: string; balance: string; payment_status: string; approval_status: string; version: number; can_edit: boolean; can_add_payment: boolean; can_view_history: boolean; image?: { filename: string; available: boolean; url: string } | null }
export type PurchaseOrderDetail = PurchaseOrder & { lines: { id: string; item: { id: string; sku: string; name: string; category: string; unit_of_measure: string; classification: string }; description: string; quantity: string; unit_price: string; line_total: string; accepted_quantity: string; open_quantity: string }[]; image?: { filename: string; available: boolean; url: string } | null }
export type InventoryRow = { item: { id: string; sku: string; name: string; category: string; unit_of_measure: string; classification: string }; vendor_name?: string; vendor_names?: string[]; ordered_quantity: string; open_order_quantity: string; received_quantity: string; consumed_quantity: string; available_quantity: string; unit_cost?: string; valuation?: string }
export type InventoryTransaction = { id: string; item_id: string; item_name: string; sku: string; unit_of_measure: string; category: string; transaction_type: 'receipt' | 'issue' | 'allocation'; quantity: string; unit_cost: string; reference: string | null; notes: string | null; po_number: string | null; recorded_by: string; occurred_at: string }
export type Timecard = { id: string; project_id: string; employee: { name: string }; cost_code: { name: string }; work_date: string; regular_hours: string; overtime_hours: string; labor_cost?: string; status: string; version: number; permitted_actions: string[] }
export type LaborLedger = { currency: string; summary: { worker_count: number; total_earned: string; total_paid: string; payable: string; total_work_entries: number; work_units: { unit: string; quantity: string }[] }; workers: { id: string; name: string; trade: string; phone: string | null; active: boolean; version: number; earned: string; paid: string; payable: string; work_entry_count: number; work_units: { unit: string; quantity: string }[] }[]; work_entries: { id: string; worker_id: string; worker_name: string; trade: string; work_date: string; description: string; quantity: string; unit: string; rate: string; amount: string }[]; payments: { id: string; worker_id: string; worker_name: string; payment_date: string; amount: string; payment_mode: string; reference: string | null; comment: string | null }[] }
export type LaborPlanDocument = { id: string; filename: string; category: string; uploaded_at: string; comment: string }
export type LaborContractDocument = { id: string; contract_id: string; contract_number: string; subcontractor_name: string; filename: string; content_type: string; byte_size: number; uploaded_at: string; uploaded_by: string; comment: string; url: string }
export type LaborContractAddendum = { id: string; plan_document_id: string; plan_filename: string; reason: string; previous_value: string; revised_value: string; status: string; submitted_at: string; submitted_by: string | null; decided_at: string | null; decided_by: string | null; decision_comment: string | null; document_filename: string | null; document_content_type: string | null; document_byte_size: number | null; document_url: string | null }
export type LaborContractRecord = { id: string; contract_number: string; subcontractor_name: string; scope: string; pricing_type: 'unit_rate' | 'lump_sum'; currency: string; contract_value: string; unit: string | null; unit_rate: string | null; baseline_document_id: string | null; baseline_document: string | null; status: string; version: number; certified: string; paid: string; payable: string; claims: { id: string; claim_number: string; period_start: string; period_end: string; work_description: string; quantity: string | null; amount: string; paid: string; payable: string; status: string; decision_comment: string | null; payments: { id: string; payment_date: string; amount: string; payment_mode: string; reference: string | null; comment: string | null }[] }[]; addenda: LaborContractAddendum[] }
export type LaborContractsLedger = { currency: string; contracts: LaborContractRecord[]; plan_documents: LaborPlanDocument[] }
export type BillingRow = { id: string; application_number: string; description: string; period_start: string; period_end: string; status: string; currency: string; current_work_total: string; retainage_total: string; net_billable: string; version: number }
export type Payment = { id: string; amount: string; payment_date: string; payment_mode?: string; reference?: string; comment?: string }
export type CashFlow = { currency: string; approved_contract_value: string; billed_work: string; invoiced_amount: string; cash_received: string; outstanding_invoices: string; retainage_held: string; retainage_released: string; as_of: string; applications: { id: string; application_number: string; description: string; submitted_date: string; billed_amount: string; received_amount: string; outstanding_amount: string; status: string }[]; receipts: { id: string; received_date: string; amount: string; payment_method: string; reference: string | null; comment: string | null; billing_entry_id: string | null; application_number: string | null; application_description: string | null; recorded_by: string }[] }

function formatApiError(value: unknown): string {
  if (typeof value === 'string' && value.trim()) return value
  if (Array.isArray(value)) {
    const messages = value.map(entry => {
      if (typeof entry === 'string') return entry
      if (!entry || typeof entry !== 'object') return ''
      const error = entry as { loc?: unknown[]; msg?: unknown; message?: unknown }
      const field = Array.isArray(error.loc)
        ? error.loc.filter(part => typeof part === 'string' && part !== 'body' && part !== 'query').join('.')
        : ''
      const message = typeof error.msg === 'string' ? error.msg : typeof error.message === 'string' ? error.message : ''
      if (!message) return ''
      return field ? `${field}: ${message}` : message
    }).filter(Boolean)
    if (messages.length) return messages.join('; ')
  }
  if (value && typeof value === 'object') {
    const error = value as { message?: unknown; detail?: unknown; errors?: unknown }
    if (typeof error.message === 'string') return error.message
    if (error.detail !== undefined) return formatApiError(error.detail)
    if (error.errors !== undefined) return formatApiError(error.errors)
    try { return JSON.stringify(value) } catch { return 'The server returned an unreadable error response.' }
  }
  return 'The request could not be completed. Please check the form and try again.'
}

export class ApiError extends Error {
  status: number
  code?: string
  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}
let csrfToken = ''
export const setCsrf = (token: string) => { csrfToken = token; setLoggingCsrf(token) }

async function request<T>(path: string, init: RequestInit = {}, csrf?: string): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const token = csrf || csrfToken
  if (['POST', 'PATCH', 'PUT', 'DELETE'].includes(init.method || 'GET') && token) headers.set('X-CSRF-Token', token)
  const started = performance.now()
  let response: Response
  try {
    response = await fetch(`/api/v1${path}`, { ...init, headers, credentials: 'include' })
  } catch (error) {
    logClientEvent({ event: 'api_network_error', method: init.method || 'GET' })
    throw error
  }
  if (!(path === '/me' && response.status === 401)) {
    logClientEvent({ event: 'api_response', method: init.method || 'GET', status: response.status,
      duration_ms: Math.round(performance.now() - started), request_id: response.headers.get('X-Request-ID') || undefined })
  }
  if (response.status === 204) return undefined as T
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const message = body?.error?.message ?? body?.detail ?? body?.message ?? `Request failed (${response.status})`
    throw new ApiError(formatApiError(message), response.status, body?.error?.code)
  }
  return body as T
}
const json = (method: string, value?: unknown): RequestInit => ({ method, body: value === undefined ? undefined : JSON.stringify(value) })

export const api = {
  recordActivity: (projectId: string, module: AuditModule, activity: 'visit' | 'export') => request<void>(`/projects/${projectId}/activities`, json('POST', { module, activity })),
  projectAudit: (projectId: string, page: number, pageSize: number, search: string, startTime = '', endTime = '') => request<Page<ProjectAuditEntry>>(`/projects/${projectId}/audit-log?${new URLSearchParams({ page: String(page), page_size: String(pageSize), search, ...(startTime ? { start_time: startTime } : {}), ...(endTime ? { end_time: endTime } : {}) })}`),
  exportProjectAudit: async (projectId: string, search: string, startTime = '', endTime = '') => {
    await api.recordActivity(projectId, 'audit', 'export')
    const response = await fetch(`/api/v1/projects/${projectId}/audit-log?${new URLSearchParams({ export: '1', search, ...(startTime ? { start_time: startTime } : {}), ...(endTime ? { end_time: endTime } : {}) })}`, { credentials: 'include' })
    if (!response.ok) { const body = await response.json().catch(() => null); throw new ApiError(formatApiError(body?.detail || body?.error?.message || 'Could not export Audit Log'), response.status) }
    const url = URL.createObjectURL(await response.blob())
    const link = document.createElement('a')
    link.href = url
    link.download = `project-${projectId}-audit-log.csv`
    link.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  },
  bootstrap: () => request<{ csrf_token: string; authenticated: boolean }>('/auth/bootstrap').then(result => { setCsrf(result.csrf_token); return result }),
  me: () => request<User & { capabilities: string[] }>('/me'),
  login: (username: string, password: string, csrf: string) => request<Session>('/auth/login', json('POST', { username, password }), csrf).then(result => { setCsrf(result.csrf_token); return result }),
  logout: (csrf: string) => request<void>('/auth/logout', json('POST'), csrf),
  projects: () => request<Page<Project>>('/me/projects?page=1&page_size=100'),
  createProject: (input: { name: string; location: string; baseline_budget: string; contract_value: string; start_date: string; status: 'Planning' | 'Active'; plan_comment: string; plan_document: File | null }, csrf: string) => {
    const body = new FormData()
    body.set('name', input.name)
    body.set('location', input.location)
    body.set('baseline_budget', input.baseline_budget)
    body.set('contract_value', input.contract_value)
    body.set('start_date', input.start_date)
    body.set('status', input.status)
    body.set('currency', 'INR')
    if (input.plan_document) {
      body.set('plan_comment', input.plan_comment)
      body.set('plan_document', input.plan_document)
    }
    return request<Project>('/projects', { method: 'POST', body }, csrf)
  },
  dashboard: (id: string) => request<Dashboard>(`/projects/${id}/dashboard`),
  valueHistory: (id: string) => request<Page<{ id: string; changed_at: string; previous_value: string; new_value: string; changed_by: string; filename: string; comment: string }>>(`/projects/${id}/value-history`),
  documents: (id: string) => request<Page<{ id: string; filename: string; content_type: string; uploaded_at: string; uploaded_by: string; comment: string; current_value: string | null; new_estimate: string | null }>>(`/projects/${id}/documents`),
  uploadPlan: (id: string, file: File, comment: string, currentValue: string, newEstimate: string) => {
    const body = new FormData()
    body.set('plan_document', file)
    body.set('plan_comment', comment)
    body.set('current_value', currentValue)
    body.set('new_estimate', newEstimate)
    return request<{ id: string; filename: string }>(`/projects/${id}/documents`, { method: 'POST', body })
  },
  updateProjectStatus: (project: Project, input: { status: string; comment: string; hold_reason: string; confirm_complete: boolean }) => request<Project>(`/projects/${project.id}/status?expected_version=${project.version}`, json('PATCH', input)),
  statusHistory: (id: string) => request<Page<{ id: string; previous_status: string | null; new_status: string; comment: string; occurred_at: string; actor: { name: string } }>>(`/projects/${id}/status-history`),
  purchaseOrders: (id: string, page = 1, pageSize = 20, search = '', paymentStatus = '') => request<Page<PurchaseOrder>>(`/projects/${id}/purchase-orders?page=${page}&page_size=${pageSize}${search ? `&search=${encodeURIComponent(search)}` : ''}${paymentStatus ? `&payment_status=${encodeURIComponent(paymentStatus)}` : ''}`),
  procurementSummary: (id: string) => request<{ order_count: number; currency: string; total_ordered: string; total_paid: string; outstanding_balance: string; as_of: string }>(`/projects/${id}/procurement-summary`),
  purchaseOrder: (projectId: string, id: string) => request<PurchaseOrderDetail>(`/projects/${projectId}/purchase-orders/${id}`),
  vendors: () => request<Page<{ id: string; name: string; active: boolean }>>('/vendors'),
  inventoryItems: () => request<Page<{ id: string; sku: string; name: string; category: string; unit_of_measure: string; classification: string }>>('/inventory-items'),
  savePurchaseOrder: (projectId: string, input: { vendor_id?: string; vendor_name?: string; order_date: string; lines: { item_id?: string; item_name?: string; category?: string; description: string; quantity: string; unit_price: string }[]; paid_amount?: string; payment_mode?: 'Gpay' | 'Bank transfer' | 'Cash' | 'Other'; payment_comment?: string }, csrf: string, edit?: { id: string; version: number }, image?: File | null) => {
    const body = image && !edit ? new FormData() : undefined
    if (body) {
      body.set('payload', JSON.stringify(input))
      body.set('image', image as File)
    }
    return request<PurchaseOrderDetail>(`/projects/${projectId}/purchase-orders${edit ? `/${edit.id}?expected_version=${edit.version}` : ''}`, body ? { method: 'POST', body } : json(edit ? 'PATCH' : 'POST', input), csrf)
  },
  addPayment: (projectId: string, orderId: string, input: { amount: string; payment_date: string; payment_mode: 'Gpay' | 'Bank transfer' | 'Cash' | 'Other'; reference?: string; comment?: string }, csrf: string, key: string) => request<{ payment: Payment; purchase_order: PurchaseOrder }>(`/projects/${projectId}/purchase-orders/${orderId}/payments`, { ...json('POST', input), headers: { 'Idempotency-Key': key } }, csrf),
  payments: (projectId: string, orderId: string, page = 1, pageSize = 5) => request<Page<Payment & { recorded_at: string; recorded_by: { name: string }; receipt?: { filename: string; available: boolean } | null }>>(`/projects/${projectId}/purchase-orders/${orderId}/payments?page=${page}&page_size=${pageSize}`),
  inventory: (id: string) => request<Page<InventoryRow>>(`/projects/${id}/inventory`),
  inventorySummary: (id: string) => request<{ catalog_item_count: number; stocked_item_count: number; total_received_units?: string; total_consumed_units?: string; total_available_units?: string; low_stock_count?: number; out_of_stock_count?: number; valuation_amount?: string | null; currency: string; as_of: string }>(`/projects/${id}/inventory-summary`),
  inventoryTransactions: (id: string, itemId?: string) => request<Page<InventoryTransaction>>(`/projects/${id}/inventory/transactions${itemId ? `?item_id=${itemId}` : ''}`),
  recordInventoryTransaction: (id: string, input: { item_id: string; transaction_type: 'receipt' | 'issue'; quantity: string; unit_cost?: string; transaction_date: string; purchase_order_line_id?: string; reference?: string; notes?: string }, csrf: string) => request<InventoryTransaction>(`/projects/${id}/inventory/transactions`, json('POST', input), csrf),
  billingSummary: (id: string) => request<{ currency: string; approved_contract_value: string; billed_work: string; invoiced_amount: string; cash_received: string; outstanding_invoices: string; retainage_held: string; retainage_released: string; as_of: string }>(`/projects/${id}/billing-summary`),
  cashFlow: (id: string) => request<CashFlow>(`/projects/${id}/cash-flow`),
  recordCashReceipt: (id: string, input: { billing_entry_id?: string; received_date: string; amount: string; payment_method: 'Bank transfer' | 'Cheque' | 'Cash' | 'Gpay' | 'Other'; reference?: string; comment?: string }, csrf: string) => request<{ id: string; received_date: string; amount: string; payment_method: string; reference: string | null; comment: string | null; billing_entry_id: string | null }>(`/projects/${id}/cash-receipts`, json('POST', input), csrf),
  billings: (id: string) => request<Page<BillingRow & { description?: string }>>(`/projects/${id}/progress-billings`),
  createBilling: (id: string, input: { description: string; submitted_date: string; amount: string }, csrf: string) => request<BillingRow>(`/projects/${id}/progress-billings`, json('POST', input), csrf),
  timecards: (id: string) => request<Page<Timecard>>(`/projects/${id}/timecards`),
  attendanceSummary: (id: string) => request<{ regular_hours: string; overtime_hours: string; pending_count: number; approved_count: number; labor_cost: string; currency: string }>(`/projects/${id}/attendance-summary`),
  createTimecard: (id: string, input: { employee_name: string; cost_code: string; work_date: string; regular_hours: string; hourly_rate: string }, csrf: string) => request<Timecard>(`/projects/${id}/timecards`, json('POST', input), csrf),
  laborLedger: (id: string) => request<LaborLedger>(`/projects/${id}/labor`),
  createLaborWorker: (id: string, input: { name: string; trade: string; phone?: string }, csrf: string) => request<{ id: string; name: string; trade: string; phone: string | null; active: boolean; version: number }>(`/projects/${id}/labor/workers`, json('POST', input), csrf),
  updateLaborWorker: (id: string, workerId: string, input: { name: string; trade: string; phone?: string; expected_version: number }, csrf: string) => request<{ id: string; name: string; trade: string; phone: string | null; active: boolean; version: number }>(`/projects/${id}/labor/workers/${workerId}`, json('PUT', input), csrf),
  setLaborWorkerActive: (id: string, workerId: string, active: boolean, csrf: string) => request<{ id: string; active: boolean; version: number }>(`/projects/${id}/labor/workers/${workerId}/status`, json('PATCH', { active }), csrf),
  createLaborWorkEntry: (id: string, input: { worker_id: string; work_date: string; description: string; quantity: string; unit: 'day' | 'hour' | 'piece'; rate: string }, csrf: string) => request<{ id: string; worker_id: string; worker_name: string; work_date: string; description: string; quantity: string; unit: string; rate: string; amount: string }>(`/projects/${id}/labor/work-entries`, json('POST', input), csrf),
  createLaborWagePayment: (id: string, input: { worker_id: string; payment_date: string; amount: string; payment_mode: 'Cash' | 'Bank transfer' | 'Gpay' | 'Cheque' | 'Other'; reference?: string; comment?: string }, csrf: string) => request<{ id: string; worker_id: string; worker_name: string; payment_date: string; amount: string; payment_mode: string; reference: string | null; comment: string | null }>(`/projects/${id}/labor/payments`, json('POST', input), csrf),
  laborContracts: (id: string) => request<LaborContractsLedger>(`/projects/${id}/labor/contracts`),
  laborContractDocuments: (id: string) => request<{ items: LaborContractDocument[]; total: number }>(`/projects/${id}/labor/documents`),
  createLaborContract: (id: string, input: { subcontractor_name: string; scope: string; pricing_type: 'unit_rate' | 'lump_sum'; contract_value: string; unit?: string; unit_rate?: string; baseline_document_id?: string; document?: File | null }, csrf: string) => {
    const body = new FormData()
    Object.entries(input).forEach(([key, value]) => { if (value instanceof File) body.set('contract_document', value); else if (value != null) body.set(key, String(value)) })
    return request<LaborContractRecord>(`/projects/${id}/labor/contracts`, { method: 'POST', body }, csrf)
  },
  createLaborAddendum: (id: string, contractId: string, input: { plan_document_id: string; reason: string; revised_value: string; document?: File | null }, csrf: string) => {
    const body = new FormData()
    Object.entries(input).forEach(([key, value]) => { if (value instanceof File) body.set('addendum_document', value); else if (value != null) body.set(key, String(value)) })
    return request<{ id: string; contract_id: string; previous_value: string; revised_value: string; status: string }>(`/projects/${id}/labor/contracts/${contractId}/addenda`, { method: 'POST', body }, csrf)
  },
  decideLaborAddendum: (id: string, addendumId: string, input: { decision: 'approve' | 'reject'; comment?: string }, csrf: string) => request<{ id: string; status: string; contract_value: string }>(`/projects/${id}/labor/addenda/${addendumId}/decision`, json('POST', input), csrf),
  createLaborClaim: (id: string, contractId: string, input: { period_start: string; period_end: string; work_description: string; quantity?: string; amount: string }, csrf: string) => request<{ id: string; claim_number: string; status: string; amount: string }>(`/projects/${id}/labor/contracts/${contractId}/claims`, json('POST', input), csrf),
  decideLaborClaim: (id: string, claimId: string, input: { decision: 'approve' | 'reject'; comment?: string }, csrf: string) => request<{ id: string; status: string }>(`/projects/${id}/labor/claims/${claimId}/decision`, json('POST', input), csrf),
  payLaborClaim: (id: string, claimId: string, input: { payment_date: string; amount: string; payment_mode: 'Cash' | 'Bank transfer' | 'Gpay' | 'Cheque' | 'Other'; reference?: string; comment?: string }, csrf: string) => request<{ id: string; claim_id: string; amount: string; payment_date: string; payment_mode: string; reference: string | null }>(`/projects/${id}/labor/claims/${claimId}/payments`, json('POST', input), csrf),
  resetUserPassword: (userId: string, password: string, csrf: string) => request<{ status: string }>(`/users/${userId}/reset-password`, json('POST', { password }), csrf),
  userHistory: (userId: string, page: number, pageSize: number, search: string) => request<Page<UserHistoryEntry>>(`/users/${userId}/history?page=${page}&page_size=${pageSize}&search=${encodeURIComponent(search)}`),
  setUserActive: (userId: string, active: boolean, csrf: string) => request<{ active: boolean }>(`/users/${userId}/status`, json('PATCH', { active }), csrf),
  deleteUser: (userId: string, csrf: string) => request<{ status: string }>(`/users/${userId}`, json('DELETE'), csrf),
  users: async () => {
    const firstPage = await request<Page<User>>('/users?page=1&page_size=100')
    const items = [...firstPage.items]
    for (let page = 2; page <= Math.ceil(firstPage.total / 100); page += 1) {
      const nextPage = await request<Page<User>>(`/users?page=${page}&page_size=100`)
      items.push(...nextPage.items)
    }
    return { ...firstPage, items }
  },
  createUser: (input: { name: string; email: string | null; phone: string | null; username: string; password: string; project_ids: string[]; project_permissions: Record<string, ProjectPermissions>; global_access: boolean; global_permissions?: ProjectPermissions; users_permissions?: ProjectModulePermission; audit_permissions?: ProjectModulePermission }, csrf: string) => request<User>('/users', json('POST', input), csrf),
  updateUser: (userId: string, input: { name: string; email: string | null; phone: string | null; username: string; password?: string; project_ids: string[]; project_permissions: Record<string, ProjectPermissions>; global_access: boolean; global_permissions?: ProjectPermissions; users_permissions?: ProjectModulePermission; audit_permissions?: ProjectModulePermission }, csrf: string) => request<User>(`/users/${userId}`, json('PUT', input), csrf),
  rolePermissions: () => request<RBACConfiguration>('/users/permissions'),
  saveRolePermissions: (matrix: RBACMatrix, csrf: string) => request<{ matrix: RBACMatrix }>('/users/permissions', json('PUT', { matrix }), csrf),
}
