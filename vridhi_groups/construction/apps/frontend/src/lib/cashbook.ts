export const cashKinds = {
  owner_capital: 'Owner capital',
  owner_withdrawal: 'Owner withdrawal',
  company_expense: 'Company spending',
  project_received: 'Project cash received',
  project_funding: 'Project funding',
  other_receipt: 'Other receipt',
  opening_in: 'Starting balance (+)',
  opening_out: 'Starting balance (−)',
  paid: 'Paid',
  salary: 'Salary',
  borrowings: 'Borrowings',
} as const

export function cashAmount(value: string) {
  if (!/^-?\d+(\.\d{1,2})?$/.test(value)) throw new Error('Invalid cashbook monetary value returned by the server.')
  const [whole, fraction = ''] = value.replace(/^-/, '').split('.')
  // Keep the database's exact paise even above JavaScript's safe-number range.
  const grouped = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(BigInt(whole))
  return `${value.startsWith('-') ? '-' : ''}${grouped}.${fraction.padEnd(2, '0')}`
}
export type CashKind = keyof typeof cashKinds
export type CashDirection = 'in' | 'out'
export type CashOptionInput = { option_type: 'category' | 'type'; kind: CashKind; parent: string; name: string; first_type?: string; direction: CashDirection }
export type CashOption = Omit<CashOptionInput, 'first_type' | 'direction'> & { id: string; direction: CashDirection | null }
export const cashCategories: Record<CashKind, string[]> = {
  owner_capital: ['Capital contribution'],
  owner_withdrawal: ['Owner withdrawal'],
  company_expense: ['Company purchases', 'Company labor', 'Furniture', 'Plumbing', 'Building maintenance', 'Rent', 'Utilities', 'Transport', 'Miscellaneous'],
  project_received: ['Project transfer'],
  project_funding: ['Project transfer'],
  other_receipt: ['Other company receipt'],
  opening_in: ['Opening balance'],
  opening_out: ['Opening balance'],
  paid: ['Paid to Pending', 'Paid to Shop', 'Paid to Electricity', 'Paid to Wifi'],
  salary: ['Salary to Contractors', 'Salary to Manager', 'Salary to Security', 'Salary to Driver'],
  borrowings: ['Loan received', 'Loan repayment – principal', 'Loan interest'],
}
export type CashFilters = { start: string; end: string; search: string; kind: CashKind | ''; custom_category: string; category: string; direction: 'in' | 'out' | ''; status: 'posted' | 'voided' | 'all'; lender?: string }
export type CashInput = {
  request_id: string; transaction_date: string; kind: CashKind; custom_category?: string | null; category: string; amount: string;
  party: string; description: string; account: string; payment_mode: 'Bank transfer' | 'Cash' | 'UPI' | 'Cheque' | 'Other';
  reference: string | null; project_id: string | null;
}
export type BorrowingInput = {
  request_id: string; action: 'loan' | 'repayment'; transaction_date: string; lender: string; principal: string; interest: string;
  description: string; account: string; payment_mode: CashInput['payment_mode']; reference: string | null;
}
export type ResultInput = { request_id: string; project_id: string; as_of: string; amount: string; basis: string }
export type ResultCalculation = {
  contract_value: string; materials: string; wages: string; contractors: string; amount: string;
  recorded_cost: string; fingerprint: string; formula_version: string;
}
export type ResultApproval = {
  id: string; project_id: string; project_name: string; as_of: string; amount: string;
  snapshot: ResultCalculation; note: string; approved_by: string; approved_at: string;
}
export type ApprovalInput = { request_id: string; project_id: string; as_of: string; fingerprint: string; note: string }
export type CashEntry = Omit<CashInput, 'request_id'> & {
  id: string; reference_number: string; direction: 'in' | 'out'; project_name: string | null;
  recorded_by: string; recorded_at: string; voided_at: string | null; voided_by: string | null; void_reason: string | null;
}
export type ProjectResult = Omit<ResultInput, 'request_id'> & {
  id: string; project_name: string; recorded_by: string; recorded_at: string; voided_at: string | null; void_reason: string | null;
}
export type CashSummary = {
  opening_balance: string; opening_entries: string; money_in: string; money_out: string; closing_balance: string;
  net_movement: string; company_spending: string; count: number; kind_totals: Record<string, string>;
  expense_categories: { category: string; amount: string }[]; accounts: { account: string; balance: string }[];
  owners: { owner: string; capital: string; withdrawals: string; net: string }[];
  borrowings: { lender: string; borrowed: string; repaid: string; interest: string; outstanding: string }[];
  borrowings_outstanding: string; borrowings_borrowed: string; borrowings_repaid: string; borrowings_interest: string;
}
export type CashbookData = {
  options?: CashOption[];
  currency: string; start: string | null; end: string; summary: CashSummary; lifetime: CashSummary;
  items: CashEntry[]; total: number; page: number; page_size: number; filtered_in: string; filtered_out: string;
  projects: { id: string; name: string; status: string; archived?: boolean; calculated: ResultCalculation; approval: ResultApproval | null; pending_approval: boolean; cash_received: string; cash_sent: string }[];
  approvals: ResultApproval[];
  calculation_as_of: string;
  results: ProjectResult[]; project_totals: { profits: string; losses: string; net: string; reported: number; unreported: number };
}
export type CashHistory = { items: { id: string; actor: string; occurred_at: string; action: string; record_id: string | null; details: Record<string, unknown> | null }[]; total: number; page: number; page_size: number }
export type CashActivityRecord =
  | { type: 'entry'; record: CashEntry }
  | { type: 'result'; record: ProjectResult }
  | { type: 'approval'; record: ResultApproval }
  | { type: 'option'; record: CashOption }
export type CashbookPage = 'cash' | 'borrowings' | 'results' | 'capital' | 'history' | 'audit-log'
export function cashActivityLabel(action: string) {
  const visits: Record<string, string> = {
    cashbook_record_voided: 'Marked transaction as invalid',
    visit_cash_transactions: 'Visited Cash Transactions',
    visit_borrowings: 'Visited Borrowings',
    visit_project_profit_loss: 'Visited Project Profit & Loss',
    visit_owner_capital: 'Visited Owner Capital',
    visit_cashbook_history: 'Visited Company Cashbook history',
    visit_company_audit_log: 'Visited Company Audit Log',
    backup_created: 'Created backup',
    backup_saved: 'Saved backup file',
    backup_failed: 'Backup failed',
    backup_schedule_updated: 'Updated daily backup settings',
    backup_restored: 'Restored data from backup',
    backup_restore_failed: 'Restore failed',
    backup_restore_rejected: 'Backup file rejected',
  }
  return visits[action] || action.replace('cashbook_', '').replaceAll('_', ' ')
}
export function cashHistoryQuery(search: string, startTime: string, endTime: string) {
  return new URLSearchParams({ search, ...(startTime ? { start_time: startTime } : {}), ...(endTime ? { end_time: endTime } : {}) })
}
export function cashQuery(filters: CashFilters) {
  return new URLSearchParams(Object.entries(filters).filter(([, value]) => value !== ''))
}
