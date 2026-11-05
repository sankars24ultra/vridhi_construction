import { useEffect, useRef, useState } from 'react'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDownLeft, ArrowUpRight, ArrowUpDown, Ban, BanknoteArrowDown, Calculator, CalendarArrowDown, CalendarArrowUp, CalendarRange, ChevronDown, ChevronLeft, ChevronRight, ChevronUp, CircleCheck, FolderPlus, CircleHelp, ClipboardCheck, Download, Eye, FilterX, History, HandCoins, Info, ListFilter, ListPlus, Plus, RefreshCw, Search, Sunrise, Tags, UserCheck, Wallet } from 'lucide-react'
import { api, ApiError } from '../../lib/api'
import { cashKinds, cashCategories, cashActivityLabel, cashAmount as amount, type CashKind, type CashFilters, type CashInput, type CashbookData, type ApprovalInput, type CashOption, type CashOptionInput, type BorrowingInput, type CashHistory, type CashbookPage, type CashActivityRecord } from '../../lib/cashbook'
import { EmptyState, FormActions, Kpi, MutationError, PageTitle, PanelHeading, QueryError } from '../../components/ui'
import { ModalFrame } from '../../components/ModalFrame'
import { ExportHeader } from '../../components/ExportHeader'
import { AuditDateRange } from '../../components/AuditDateRange'
import './CompanyCashbook.css'

const today = () => {
  const date = new Date()
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}
const localDate = (value: string) => new Date(`${value}T12:00:00`).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
const incoming = (kind: CashKind) => ['owner_capital', 'project_received', 'other_receipt', 'opening_in'].includes(kind)
type Tab = 'cash' | 'borrowings' | 'results' | 'capital'
type VoidTarget = { type: 'entries'; id: string; label: string; entry: CashbookData['items'][number] }
const loanPaymentStatus = (lender: CashbookData['lifetime']['borrowings'][number]) =>
  Number(lender.outstanding) <= 0 ? 'Paid' : Number(lender.repaid) > 0 ? 'Partially paid' : 'Unpaid'

function useCashbookVisit(page: CashbookPage, csrf: string) {
  const client = useQueryClient()
  const lastVisit = useRef('')
  const visit = useMutation({
    mutationFn: (target: CashbookPage) => api.recordCashbookVisit(target, csrf),
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: ['company-cashbook', 'history'] }),
        client.invalidateQueries({ queryKey: ['company-cashbook', 'audit-log'] }),
      ])
    },
  })
  const { mutate } = visit
  useEffect(() => {
    const key = `${csrf}:${page}`
    if (lastVisit.current === key) return
    lastVisit.current = key
    mutate(page)
  }, [page, csrf, mutate])
  return visit
}

export function CompanyCashbook({ csrf, canWrite, canApprove, canExport }: { csrf: string; canWrite: boolean; canApprove: boolean; canExport: boolean }) {
  const client = useQueryClient()
  const [filters, setFilters] = useState<CashFilters>({ start: '', end: today(), search: '', kind: '', custom_category: '', category: '', direction: '', status: 'posted' })
  const [tab, setTab] = useState<Tab>(() => {
    const saved = sessionStorage.getItem('vridhi-cashbook-tab')
    return saved === 'borrowings' || saved === 'results' || saved === 'capital' ? saved : 'cash'
  })
  const visit = useCashbookVisit(tab, csrf)
  useEffect(() => {
    sessionStorage.setItem('vridhi-cashbook-tab', tab)
  }, [tab])
  const [lenderSearch, setLenderSearch] = useState('')
  const [loanStatus, setLoanStatus] = useState('')
  const [lenderPage, setLenderPage] = useState(1)
  const [lenderPageSize, setLenderPageSize] = useState(5)
  const [projectSearch, setProjectSearch] = useState('')
  const [approvalStatus, setApprovalStatus] = useState<'' | 'pending' | 'approved'>('')
  const [approvedUser, setApprovedUser] = useState('')
  const [projectPage, setProjectPage] = useState(1)
  const [projectPageSize, setProjectPageSize] = useState(10)
  const [resultDetails, setResultDetails] = useState<{ project: CashbookData['projects'][number]; view: 'calculation' | 'history' } | null>(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [spendingPage, setSpendingPage] = useState(1)
  const [spendingPageSize, setSpendingPageSize] = useState(10)
  const [accountPage, setAccountPage] = useState(1)
  const [accountPageSize, setAccountPageSize] = useState(10)
  const [entryOpen, setEntryOpen] = useState(false)
  const [helpOpen, setHelpOpen] = useState(false)
  const [summaryOpen, setSummaryOpen] = useState(() => localStorage.getItem('vridhi-cashbook-summary-open') !== 'false')
  const toggleSummary = () => setSummaryOpen(open => { localStorage.setItem('vridhi-cashbook-summary-open', String(!open)); return !open })
  const [borrowing, setBorrowing] = useState<{ action: BorrowingInput['action']; lender: string } | null>(null)
  const [lenderDetails, setLenderDetails] = useState<string | null>(null)
  const [entryDetails, setEntryDetails] = useState<CashbookData['items'][number] | null>(null)
  const [approvalTarget, setApprovalTarget] = useState<{ project: CashbookData['projects'][number]; asOf: string } | null>(null)
  const [voidTarget, setVoidTarget] = useState<VoidTarget | null>(null)
  const [reason, setReason] = useState('')
  const [message, setMessage] = useState('')
  const [printData, setPrintData] = useState<CashbookData | null>(null)
  const invalidDate = Boolean(filters.start && filters.start > filters.end || filters.end > today() || !filters.end)
  // Summary sections depend only on the date range, so register-only filters and paging refetch just the table.
  const overview = useQuery({ queryKey: ['company-cashbook', 'overview', filters.start, filters.end], queryFn: () => api.cashbook({ start: filters.start, end: filters.end, search: '', kind: '', custom_category: '', category: '', direction: '', status: 'posted' }, 1, 1), enabled: !invalidDate, placeholderData: keepPreviousData, refetchInterval: tab === 'results' ? 15000 : false })
  const query = useQuery({ queryKey: ['company-cashbook', 'register', filters, page, pageSize], queryFn: () => api.cashbook(filters, page, pageSize), enabled: !invalidDate, placeholderData: keepPreviousData })
  useEffect(() => {
    if (!message) return
    const timer = window.setTimeout(() => setMessage(''), 5000)
    return () => window.clearTimeout(timer)
  }, [message])
  const data = printData || overview.data
  const rows = printData || query.data
  const visibleLenders = data?.lifetime.borrowings.filter(lender =>
    lender.lender.toLocaleLowerCase().includes(lenderSearch.trim().toLocaleLowerCase()) &&
    (!loanStatus || loanPaymentStatus(lender) === loanStatus),
  ) || []
  const currentLenderPage = Math.min(lenderPage, Math.max(1, Math.ceil(visibleLenders.length / lenderPageSize)))
  const lenderRows = printData ? visibleLenders : visibleLenders.slice((currentLenderPage - 1) * lenderPageSize, currentLenderPage * lenderPageSize)
  useEffect(() => {
    setLenderPage(1)
  }, [lenderSearch, loanStatus])
  const visibleProjects = data?.projects.filter(project =>
    project.name.toLocaleLowerCase().includes(projectSearch.trim().toLocaleLowerCase()) &&
    (!approvalStatus || (approvalStatus === 'pending') === project.pending_approval) &&
    (!approvedUser || (approvedUser === '__none' ? !project.approval : project.approval?.approved_by === approvedUser)),
  ) || []
  const currentProjectPage = Math.min(projectPage, Math.max(1, Math.ceil(visibleProjects.length / projectPageSize)))
  const projectRows = printData ? visibleProjects : visibleProjects.slice((currentProjectPage - 1) * projectPageSize, currentProjectPage * projectPageSize)
  const currentSpendingPage = Math.min(spendingPage, Math.max(1, Math.ceil((data?.summary.expense_categories.length || 0) / spendingPageSize)))
  const currentAccountPage = Math.min(accountPage, Math.max(1, Math.ceil((data?.summary.accounts.length || 0) / accountPageSize)))
  const spendingRows = printData ? printData.summary.expense_categories : data?.summary.expense_categories.slice((currentSpendingPage - 1) * spendingPageSize, currentSpendingPage * spendingPageSize) || []
  const accountRows = printData ? printData.summary.accounts : data?.summary.accounts.slice((currentAccountPage - 1) * accountPageSize, currentAccountPage * accountPageSize) || []
  useEffect(() => {
    setSpendingPage(1)
    setAccountPage(1)
  }, [filters.start, filters.end])
  useEffect(() => {
    setProjectPage(1)
  }, [projectSearch, approvalStatus, approvedUser])
  const refresh = async (text: string) => {
    setMessage(text)
    await client.invalidateQueries({ queryKey: ['company-cashbook'] })
  }
  const voidRecord = useMutation({
    mutationFn: async () => {
      if (!voidTarget) throw new Error('Select a record to mark as invalid.')
      return api.voidCashbookRecord(voidTarget.type, voidTarget.id, reason, csrf)
    },
    onSuccess: async () => { setVoidTarget(null); setReason(''); await refresh('Record marked as invalid. History is retained and balances have been recalculated.') },
  })
  const exportReport = useMutation({
    mutationFn: async () => {
      const report = await api.exportCashbook(filters, csrf)
      setPrintData(report)
      await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
      await document.fonts.ready
      const title = document.title
      document.title = `Company Cashbook - ${tab} - ${filters.end}`
      const restore = () => { document.title = title; setPrintData(null) }
      window.addEventListener('afterprint', restore, { once: true })
      try { window.print() } catch (error) { window.removeEventListener('afterprint', restore); restore(); throw error }
    },
  })
  const changeFilters = (update: Partial<CashFilters>) => { setFilters(previous => ({ ...previous, ...update })); setPage(1) }
  const openVoid = (target: VoidTarget) => { setVoidTarget(target); setReason(''); voidRecord.reset() }
  const dateLabel = `${filters.start ? localDate(filters.start) : 'Beginning of register'} to ${filters.end ? localDate(filters.end) : '—'}`
  return <div className="company-cashbook">
    <ExportHeader reportTitle={`Company Cashbook · ${tab === 'results' ? 'Project results' : tab === 'capital' ? 'Owner capital' : tab === 'borrowings' ? 'Borrowings' : 'Cash transactions'}`} />
    <PageTitle eyebrow="COMPANY FINANCE" title="Company Cashbook" subtitle="Company-wide capital, receipts, spending and project transfers. Independent of your selected project." action={<div className="overview-actions">
      {canExport && <button className="button-secondary export-report-action" disabled={!data || overview.isFetching || query.isFetching || invalidDate || exportReport.isPending} onClick={() => exportReport.mutate()}><Download size={15} />{exportReport.isPending ? 'Preparing…' : 'Download Report'}</button>}
      {canWrite && <button className="button-primary" onClick={() => { setMessage(''); setEntryOpen(true) }}><Plus size={15} />Record transaction</button>}
      <span className="row-action-tooltip" data-tooltip="Cashbook FAQ"><button type="button" className="icon-button" aria-label="Cashbook FAQ" aria-haspopup="dialog" onClick={() => setHelpOpen(true)}><Info size={17} aria-hidden="true" /></button></span>
    </div>} />
    {message && <div className="cashbook-message" role="status">{message} <button type="button" className="text-action" aria-label="Dismiss notification" onClick={() => setMessage('')}>Dismiss</button></div>}
    <div className="cashbook-toolbar">
    {!invalidDate && data && <p className="cashbook-period">{dateLabel} · All company accounts · Invalid entries excluded from totals</p>}
    <div className="cashbook-filters">
      <label className="row-action-tooltip cashbook-date-field" data-tooltip="From"><CalendarArrowDown size={15} aria-hidden="true" /><input aria-label="From" type="date" value={filters.start} max={filters.end || today()} onChange={event => changeFilters({ start: event.target.value })} /></label>
      <label className="row-action-tooltip cashbook-date-field" data-tooltip="Through"><CalendarArrowUp size={15} aria-hidden="true" /><input aria-label="Through" type="date" value={filters.end} max={today()} onChange={event => changeFilters({ end: event.target.value })} /></label>
      <div className="cashbook-presets">
        <button className="button-secondary" onClick={() => changeFilters({ start: `${today().slice(0, 7)}-01`, end: today() })}>This month</button>
        <button className="button-secondary" onClick={() => changeFilters({ start: '', end: today() })}>All time</button>
        {(filters.start || filters.end !== today()) && <span className="row-action-tooltip" data-tooltip="Clear date filter"><button type="button" className="icon-button" aria-label="Clear date filter" onClick={() => changeFilters({ start: '', end: today() })}><FilterX size={17} /></button></span>}
        <span className="row-action-tooltip cashbook-help-tip" data-tooltip="Date range changes cash totals. Project results use the latest declaration through the end date."><button type="button" className="icon-button" aria-label="About the date filter: Date range changes cash totals. Project results use the latest declaration through the end date."><CircleHelp size={17} /></button></span>
      </div>
    </div>
    </div>
    {invalidDate && <div className="form-error" role="alert">Choose a valid date range ending no later than today.</div>}
    <QueryError error={overview.error || exportReport.error} onRetry={() => void overview.refetch()} />
    <QueryError error={visit.error} onRetry={() => visit.mutate(tab)} />
    {overview.isLoading && <div className="loading-line" />}
    {!invalidDate && data && <>
      <div className="cashbook-kpis kpi-grid">
        <Kpi label="Closing recorded balance" value={amount(data.summary.closing_balance)} note="Opening balance + money in − money out" icon={<Wallet size={17} />} />
        <Kpi label="Opening balance" value={amount(data.summary.opening_balance)} note="Cash before the From date + starting balances in this range" icon={<Sunrise size={17} />} />
        <Kpi label="Money in" value={amount(data.summary.money_in)} note="All money-in transaction types, excluding starting balances" icon={<ArrowDownLeft size={17} />} />
        <Kpi label="Money out" value={amount(data.summary.money_out)} note="All money-out transaction types, excluding starting balances" icon={<ArrowUpRight size={17} />} />
        <Kpi label="Outstanding borrowings" value={amount(data.lifetime.borrowings_outstanding)} note={`Principal still owed through ${localDate(data.end)}`} icon={<ArrowUpDown size={17} />} />
      </div>
      {Number(data.summary.closing_balance) < 0 && <div className="form-error" role="status">Recorded cash is negative. Check starting balances, missing receipts and duplicate payments before relying on this figure.</div>}
      <div className={`cashbook-sofar panel${summaryOpen ? '' : ' collapsed'}`}>
        <PanelHeading title={`Cumulative financial summary · through ${localDate(data.end)}`} meta="Net category totals from the beginning through this date · Opposite-direction types offset totals · Unaffected by register filters" action={<span className="row-action-tooltip cashbook-summary-toggle" data-tooltip={summaryOpen ? 'Collapse summary' : 'Expand summary'}><button type="button" className="icon-button" aria-label={summaryOpen ? 'Collapse cumulative financial summary' : 'Expand cumulative financial summary'} aria-expanded={summaryOpen} aria-controls="cashbook-cumulative-metrics" onClick={toggleSummary}>{summaryOpen ? <ChevronUp size={17} aria-hidden="true" /> : <ChevronDown size={17} aria-hidden="true" />}</button></span>} />
        <div className="cashbook-metrics" id="cashbook-cumulative-metrics" hidden={!summaryOpen}>
          <div><span>Money in so far</span><strong className="cash-in">{amount(data.lifetime.money_in)}</strong></div>
          <div><span>Money out so far</span><strong className="cash-out">{amount(data.lifetime.money_out)}</strong></div>
          <div><span>Company spending</span><strong className="cash-out">{amount(data.lifetime.company_spending)}</strong></div>
          <div><span>Other receipts so far</span><strong className="cash-in">{amount(data.lifetime.kind_totals.other_receipt)}</strong></div>
          <div><span>Owner capital received</span><strong className="cash-in">{amount(data.lifetime.kind_totals.owner_capital)}</strong></div>
          <div><span>Owner withdrawals</span><strong className="cash-out">{amount(data.lifetime.kind_totals.owner_withdrawal)}</strong></div>
          <div><span>Project cash received / funded</span><strong><span className="cash-in cashbook-metric-number">{amount(data.lifetime.kind_totals.project_received)}</span> / <span className="cash-out cashbook-metric-number">{amount(data.lifetime.kind_totals.project_funding)}</span></strong></div>
          <div><span>Borrowings outstanding</span><strong>{amount(data.lifetime.borrowings_outstanding)}</strong></div>
          <div><span>Approved projected profit / loss</span><strong className={Number(data.project_totals.net) < 0 ? 'cash-out' : 'cash-in'}>{data.project_totals.reported ? amount(data.project_totals.net) : 'Not approved'}</strong></div>
          <div><span>Project approvals</span><strong><span className="cash-in cashbook-metric-number">{data.project_totals.reported} approved</span> · <span className="cash-pending cashbook-metric-number">{data.project_totals.unreported} not yet approved</span></strong></div>
        </div>
      </div>
      <div className="cashbook-tabs" role="tablist" aria-label="Company finance views">{([['cash', 'Cash Transactions'], ['borrowings', 'Borrowings'], ['results', 'Project Profit & Loss'], ['capital', 'Owner Capital']] as const).map(([id, label]) => <button key={id} role="tab" id={`cash-tab-${id}`} aria-selected={tab === id} aria-controls={`cash-panel-${id}`} className={tab === id ? 'selected' : ''} onClick={() => setTab(id)}>{label}</button>)}</div>
      <section role="tabpanel" id={`cash-panel-${tab}`} aria-labelledby={`cash-tab-${tab}`}>
      {tab === 'cash' && <>
        <section className="panel table-panel cashbook-register-panel">
          <PanelHeading title="Transaction register" meta="Newest transaction dates first · Mark an incorrect posted record as invalid, then record a replacement" action={<div className="cashbook-register-filters">
            <label className="row-action-tooltip" data-tooltip="Search"><Search size={15} aria-hidden="true" /><input aria-label="Search" type="search" maxLength={200} placeholder="Party, purpose, account or reference" value={filters.search} onChange={event => changeFilters({ search: event.target.value })} /></label>
            <label className="row-action-tooltip" data-tooltip="Category"><Tags size={15} aria-hidden="true" /><select aria-label="Category" value={filters.custom_category ? `custom:${filters.custom_category}` : filters.kind} onChange={event => { const custom = event.target.value.startsWith('custom:') ? event.target.value.slice(7) : ''; changeFilters({ kind: custom ? '' : event.target.value as CashFilters['kind'], custom_category: custom, category: '' }) }}><option value="">All categories</option>{Object.entries(cashKinds).map(([key, label]) => <option key={key} value={key}>{label}</option>)}{(data?.options || []).filter(option => option.option_type === 'category').map(option => <option key={option.id} value={`custom:${option.name}`}>{option.name}</option>)}</select></label>
            <label className="row-action-tooltip" data-tooltip="Direction"><ArrowUpDown size={15} aria-hidden="true" /><select aria-label="Direction" value={filters.direction} onChange={event => changeFilters({ direction: event.target.value as CashFilters['direction'] })}><option value="">Both directions</option><option value="in">Money in</option><option value="out">Money out</option></select></label>
            <label className="row-action-tooltip" data-tooltip="Transaction type"><ListFilter size={15} aria-hidden="true" /><select aria-label="Transaction type" value={filters.category} onChange={event => changeFilters({ category: event.target.value })}><option value="">All transaction types</option>{[...new Set(filters.custom_category || filters.kind
              ? [...(filters.custom_category ? [] : cashCategories[filters.kind as CashKind]), ...(data?.options || []).filter(option => option.option_type === 'type' && (filters.custom_category ? option.parent === filters.custom_category : option.kind === filters.kind && !option.parent)).map(option => option.name)]
              : [...Object.values(cashCategories).flat(), ...(data?.options || []).filter(option => option.option_type === 'type').map(option => option.name)])].sort().map(type => <option key={type}>{type}</option>)}</select></label>
            <label className="row-action-tooltip" data-tooltip="Status"><CircleCheck size={15} aria-hidden="true" /><select aria-label="Status" value={filters.status} onChange={event => changeFilters({ status: event.target.value as CashFilters['status'] })}><option value="posted">Posted</option><option value="voided">Marked as invalid</option><option value="all">All records</option></select></label>
            {(filters.search || filters.kind || filters.custom_category || filters.direction || filters.category || filters.status !== 'posted') && <span className="row-action-tooltip" data-tooltip="Clear register filters"><button type="button" className="icon-button" aria-label="Clear register filters" onClick={() => changeFilters({ search: '', kind: '', custom_category: '', direction: '', category: '', status: 'posted' })}><FilterX size={17} /></button></span>}
          </div>} />
          <div role="status" className="cashbook-report-scope cashbook-updating">{query.isFetching ? 'Updating transactions…' : ''}</div>
          <QueryError error={query.error} onRetry={() => void query.refetch()} />
          {query.isLoading && <div className="loading-line" />}
          <div className="table-scroll"><table className="data-table cashbook-table"><thead><tr><th>Date</th><th>Transaction</th><th>Party / purpose</th><th>Mode / account</th><th className="numeric">Money in</th><th className="numeric">Money out</th><th>Recorded by</th><th>Details</th></tr></thead><tbody>
            {rows?.items.map(entry => <tr key={entry.id} className={entry.voided_at ? 'cashbook-voided' : ''}>
              <td>{localDate(entry.transaction_date)}</td>
              <td><strong className="cashbook-cell-line" title={entry.custom_category || cashKinds[entry.kind]}>{entry.custom_category || cashKinds[entry.kind]}</strong><small className="cashbook-cell-line" title={entry.category}>{entry.category}</small>{entry.voided_at && <span className="status-pill">Marked as invalid</span>}</td>
              <td><span className="cashbook-cell-line" title={entry.party}>{entry.party}</span><small className="cashbook-cell-line" title={entry.description}>{entry.description}</small>{entry.project_name && <small className="cashbook-print-project">Project: {entry.project_name}</small>}</td>
              <td><span className="cashbook-cell-line" title={[entry.payment_mode, entry.reference].filter(Boolean).join(' · ')}>{entry.payment_mode}{entry.reference && ` · ${entry.reference}`}</span><small className="cashbook-cell-line" title={entry.account}>{entry.account}</small></td>
              <td className="numeric cash-in">{entry.direction === 'in' ? amount(entry.amount) : '—'}</td>
              <td className="numeric cash-out">{entry.direction === 'out' ? amount(entry.amount) : '—'}</td>
              <td><span className="cashbook-cell-line" title={entry.recorded_by}>{entry.recorded_by}</span></td>
              <td><div className="cashbook-entry-actions"><span className="row-action-tooltip" data-tooltip="View transaction details"><button type="button" className="icon-button" aria-label="View" onClick={() => setEntryDetails(entry)}><Eye size={17} aria-hidden="true" /></button></span>{canWrite && !entry.voided_at && !data.projects.some(project => project.id === entry.project_id && project.archived) && <span className="row-action-tooltip" data-tooltip="Mark transaction as invalid"><button type="button" className="icon-button cashbook-void-action" aria-label="Mark as invalid" onClick={() => openVoid({ type: 'entries', id: entry.id, label: entry.reference_number, entry })}><Ban size={17} aria-hidden="true" /></button></span>}</div></td>
            </tr>)}
            {rows && !rows.items.length && <tr><td colSpan={8}><EmptyState title="No matching transactions" note="Record your starting balance and actual company cash movements, or change the filters." /></td></tr>}
          </tbody></table></div>
          {rows && <div className="cashbook-report-scope">All matching posted rows: money in {amount(rows.filtered_in)} · money out {amount(rows.filtered_out)} (includes starting entries; invalid entries excluded).</div>}
          {!printData && rows && <Pager page={page} total={rows.total} size={pageSize} busy={query.isFetching} setPage={setPage} setSize={size => { setPageSize(size); setPage(1) }} />}
        </section>
        <div className="cashbook-bottom">
          <section className="panel"><PanelHeading title="Company spending breakdown" meta="Selected dates · Company spending and Paid/Salary, net of money-in entries · Not an accounting expense statement" /><div className="cashbook-breakdown">{spendingRows.map(item => <div key={item.category}><span>{item.category}</span><meter min={Math.min(0, Number(item.amount))} max={Math.max(1, Number(item.amount), Number(data.summary.company_spending))} value={Number(item.amount)} /><strong className={Number(item.amount) < 0 ? 'cash-in' : 'cash-out'}>{amount(item.amount)}</strong></div>)}{!data.summary.expense_categories.length && <p>No company spending recorded in this period.</p>}</div>{!printData && <Pager page={currentSpendingPage} size={spendingPageSize} total={data.summary.expense_categories.length} busy={overview.isFetching} setPage={setSpendingPage} setSize={size => { setSpendingPageSize(size); setSpendingPage(1) }} sizes={[10, 20, 50]} rowsLabel="Spending categories per page" />}</section>
          <section className="panel"><PanelHeading title="Recorded cash by account" meta={`Through ${localDate(data.end)} · Not reconciled against bank statements`} /><div className="cashbook-breakdown">{accountRows.map(account => <div key={account.account}><span>{account.account}</span><strong className={Number(account.balance) < 0 ? 'cash-out' : 'cash-balance'}>{amount(account.balance)}</strong></div>)}{!data.summary.accounts.length && <p>No accounts used yet.</p>}</div>{!printData && <Pager page={currentAccountPage} size={accountPageSize} total={data.summary.accounts.length} busy={overview.isFetching} setPage={setAccountPage} setSize={size => { setAccountPageSize(size); setAccountPage(1) }} sizes={[10, 20, 50]} rowsLabel="Accounts per page" />}</section>
        </div>
      </>}
      {tab === 'borrowings' && <dl className="cashbook-loan-summary" aria-label="Borrowing totals">
        <div><dt>Outstanding principal</dt><dd>{amount(data.lifetime.borrowings_outstanding)}</dd></div>
        <div><dt>Total borrowed</dt><dd className="cash-in">{amount(data.lifetime.borrowings_borrowed)}</dd></div>
        <div><dt>Principal repaid</dt><dd className="cash-out">{amount(data.lifetime.borrowings_repaid)}</dd></div>
        <div><dt>Interest paid</dt><dd className="cash-out">{amount(data.lifetime.borrowings_interest)}</dd></div>
      </dl>}
      {tab === 'borrowings' && <section className="panel table-panel">
        <PanelHeading title="Borrowings & interest" meta={`Loans from banks and other lenders · From the beginning through ${localDate(data.end)} · Interest counts as company spending; principal does not`} action={<div className="cashbook-borrowing-tools">
        <div className="cashbook-register-filters">
          <label className="row-action-tooltip" data-tooltip="Search lenders"><Search size={15} aria-hidden="true" /><input type="search" aria-label="Search lenders" placeholder="Search lenders" value={lenderSearch} onChange={event => setLenderSearch(event.target.value)} /></label>
          <label className="row-action-tooltip" data-tooltip="Loan payment status"><ListFilter size={15} aria-hidden="true" /><select aria-label="Loan payment status" value={loanStatus} onChange={event => setLoanStatus(event.target.value)}><option value="">All Payments</option><option>Unpaid</option><option>Partially paid</option><option>Paid</option></select></label>
          <span className="row-action-tooltip" data-tooltip="Clear filters"><button type="button" className="icon-button" aria-label="Clear borrowing filters" disabled={!lenderSearch && !loanStatus} onClick={() => { setLenderSearch(''); setLoanStatus('') }}><FilterX size={17} aria-hidden="true" /></button></span>
        </div>
        {canWrite && <>
          <span className="row-action-tooltip" data-tooltip="New Loan"><button type="button" className="icon-button cashbook-record-loan" aria-label="New Loan" onClick={() => setBorrowing({ action: 'loan', lender: '' })}><BanknoteArrowDown size={17} aria-hidden="true" /></button></span>
          <span className="row-action-tooltip" data-tooltip="Loan Repayment"><button type="button" className="icon-button cashbook-record-repayment" aria-label="Loan Repayment" disabled={!data.lifetime.borrowings.some(lender => Number(lender.outstanding) > 0)} onClick={() => setBorrowing({ action: 'repayment', lender: '' })}><HandCoins size={17} aria-hidden="true" /></button></span>
        </>}
        </div>} />

        {(lenderSearch || loanStatus) && <p className="cashbook-report-scope">Showing {visibleLenders.length} of {data.lifetime.borrowings.length} lenders{lenderSearch.trim() && ` · Search: ${lenderSearch.trim()}`}{loanStatus && ` · ${loanStatus}`} · Totals above include all lenders</p>}
        <div className="table-scroll"><table className="data-table cashbook-table"><thead><tr><th>Lender</th><th className="numeric">Borrowed</th><th className="numeric">Principal repaid</th><th className="numeric">Interest paid</th><th className="numeric">Outstanding principal</th><th>Payment status</th><th className="cashbook-result-actions-column">Actions</th></tr></thead><tbody>{lenderRows.map(lender => <tr key={lender.lender}>
          <td>{lender.lender}</td><td className="numeric cash-in">{amount(lender.borrowed)}</td><td className="numeric cash-out">{amount(lender.repaid)}</td><td className="numeric cash-out">{amount(lender.interest)}</td><td className="numeric"><strong>{amount(lender.outstanding)}</strong></td><td><span className="cashbook-payment-status" data-status={loanPaymentStatus(lender)}>{loanPaymentStatus(lender)}</span></td>
          <td className="cashbook-result-actions-column"><div className="cashbook-result-actions">
            {canWrite && <span className="row-action-tooltip" data-tooltip={Number(lender.outstanding) > 0 ? 'Loan Repayment' : 'Loan settled — no outstanding principal'}><button type="button" className="icon-button" aria-label={`Loan repayment to ${lender.lender}`} disabled={Number(lender.outstanding) <= 0} onClick={() => setBorrowing({ action: 'repayment', lender: lender.lender })}><HandCoins size={17} aria-hidden="true" /></button></span>}
            <span className="row-action-tooltip" data-tooltip="View loan & repayment history"><button type="button" className="icon-button" aria-label={`View transactions for ${lender.lender}`} onClick={() => setLenderDetails(lender.lender)}><Eye size={17} aria-hidden="true" /></button></span>
          </div></td>
        </tr>)}</tbody></table></div>
        {!printData && data.lifetime.borrowings.length > 0 && <Pager page={currentLenderPage} size={lenderPageSize} total={visibleLenders.length} busy={overview.isFetching} setPage={setLenderPage} setSize={size => { setLenderPageSize(size); setLenderPage(1) }} sizes={[5, 10, 20]} rowsLabel="Lenders per page" />}
        {!data.lifetime.borrowings.length && <EmptyState title="No borrowings recorded" note="Record a loan received to start tracking principal and interest by lender." />}
        {data.lifetime.borrowings.length > 0 && !visibleLenders.length && <EmptyState title="No matching borrowings" note="Try another lender name or payment status, or clear the borrowing filters." />}
      </section>}
      {tab === 'results' && <>
        {data.end !== data.calculation_as_of && <div className="cashbook-help">Approved totals and cash transfers below are through {localDate(data.end)}. Set Through to today to approve a current projection.</div>}
        <div className="cashbook-metrics panel"><div><span>Approved projected profits</span><strong className="cash-in">{amount(data.project_totals.profits)}</strong></div><div><span>Approved projected losses</span><strong className="cash-out">{amount(data.project_totals.losses)}</strong></div><div><span>Net approved projection</span><strong>{data.project_totals.reported ? amount(data.project_totals.net) : 'Not approved'}</strong></div></div>
        <section className="panel table-panel"><PanelHeading title="Project projected profit / loss" meta={`${data.projects.filter(project => project.pending_approval).length} projects need approval. The totals above show approved amounts for all projects.`} action={<div className="cashbook-project-tools"><label className="search-wrap"><Search size={15} aria-hidden="true" /><input type="search" aria-label="Search project name" placeholder="Search project name" value={projectSearch} onChange={event => setProjectSearch(event.target.value)} /></label><label className="row-action-tooltip cashbook-project-filter" data-tooltip="Approval status"><CircleCheck size={15} aria-hidden="true" /><select aria-label="Approval status" value={approvalStatus} onChange={event => setApprovalStatus(event.target.value as typeof approvalStatus)}><option value="">All statuses</option><option value="pending">Pending approval</option><option value="approved">Approved</option></select></label><label className="row-action-tooltip cashbook-project-filter" data-tooltip="Approved user"><UserCheck size={15} aria-hidden="true" /><select aria-label="Approved user" value={approvedUser} onChange={event => setApprovedUser(event.target.value)}><option value="">All approvers</option><option value="__none">Not approved</option>{[...new Set(data.projects.flatMap(project => project.approval ? [project.approval.approved_by] : []))].sort().map(name => <option key={name} value={name}>{name}</option>)}</select></label>{(projectSearch || approvalStatus || approvedUser) && <span className="row-action-tooltip" data-tooltip="Clear project filters"><button type="button" className="icon-button" aria-label="Clear project filters" onClick={() => { setProjectSearch(''); setApprovalStatus(''); setApprovedUser('') }}><FilterX size={17} /></button></span>}<span className="row-action-tooltip" data-tooltip="Refresh calculations"><button type="button" className="button-secondary" disabled={overview.isFetching} onClick={() => void overview.refetch()}><RefreshCw size={17} aria-hidden="true" />Refresh calculations</button></span></div>} />
          <div className="table-scroll"><table className="data-table cashbook-table"><thead><tr><th>Project</th><th className="numeric">Total project amount</th><th className="numeric">Live projected profit / loss</th><th className="numeric">Approved projection</th><th>Last approved date</th><th>Approved user</th><th>Approval status</th><th className="numeric">Cash received</th><th className="numeric">Cash funded</th><th className="cashbook-result-actions-column">Actions</th></tr></thead><tbody>{projectRows.map(project => <tr key={project.id}>
            <td><strong>{project.name}</strong><small>{project.status}</small></td>
            <td className="numeric">{amount(project.calculated.contract_value)}</td>
            <td className="numeric"><strong className={Number(project.calculated.amount) < 0 ? 'cash-out' : 'cash-in'}>{amount(project.calculated.amount)}</strong></td>
            <td className="numeric">{project.approval ? <strong className={Number(project.approval.amount) < 0 ? 'cash-out' : 'cash-in'}>{amount(project.approval.amount)}</strong> : 'Not approved'}</td>
            <td className="cashbook-approval-date">{project.approval ? new Date(project.approval.approved_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'}</td>
            <td>{project.approval?.approved_by || '—'}</td>
            <td><span className="status-pill">{project.pending_approval ? 'Pending approval' : 'Approved'}</span></td>
            <td className="numeric">{amount(project.cash_received)}</td><td className="numeric">{amount(project.cash_sent)}</td>
            <td className="cashbook-result-actions-column"><div className="cashbook-result-actions">
              {canApprove && !project.archived && project.pending_approval && <span className="row-action-tooltip" data-tooltip="Review and approve"><button type="button" className="icon-button" aria-label="Review and approve" disabled={overview.isFetching || data.end !== data.calculation_as_of} onClick={() => setApprovalTarget({ project, asOf: data.calculation_as_of })}><ClipboardCheck size={17} aria-hidden="true" /></button></span>}
              <span className="row-action-tooltip" data-tooltip="Calculation breakdown"><button type="button" className="icon-button" aria-label="Calculation breakdown" onClick={() => setResultDetails({ project, view: 'calculation' })}><Calculator size={17} aria-hidden="true" /></button></span>
              <span className="row-action-tooltip" data-tooltip="Approval history"><button type="button" className="icon-button" aria-label="Approval history" onClick={() => setResultDetails({ project, view: 'history' })}><History size={17} aria-hidden="true" /></button></span>
            </div></td>
          </tr>)}</tbody></table></div>
          {!visibleProjects.length && <EmptyState title={data.projects.length ? 'No matching projects' : 'No projects'} note={data.projects.length ? 'Try other filters or clear them.' : 'Create a project before reviewing projected profit or loss.'} />}
          {!printData && <Pager page={currentProjectPage} total={visibleProjects.length} size={projectPageSize} busy={overview.isFetching} setPage={setProjectPage} setSize={size => { setProjectPageSize(size); setProjectPage(1) }} sizes={[10, 20, 50]} rowsLabel="Project rows per page" />}
        </section>
        <section className="panel table-panel"><ApprovalHistoryTable records={data.approvals} currentIds={new Set(data.projects.map(project => project.approval?.id).filter((id): id is string => Boolean(id)))} showProject printMode={Boolean(printData)} />{!data.approvals.length && <EmptyState title="No approvals yet" note="Review each project calculation and approve it to include it in actual totals." />}</section>
        {data.results.length > 0 && <section className="panel table-panel"><PanelHeading title="Legacy manual declaration history" meta="Preserved for reference only; not included in actual totals" /><div className="table-scroll"><table className="data-table cashbook-table"><thead><tr><th>Project / as of</th><th className="numeric">Result</th><th>Basis</th><th>Recorded by</th><th>Status</th></tr></thead><tbody>{data.results.map(result => <tr key={result.id}><td>{result.project_name}<small>{localDate(result.as_of)}</small></td><td className="numeric">{amount(result.amount)}</td><td>{result.basis}</td><td>{result.recorded_by}</td><td>{result.voided_at ? 'Marked as invalid' : 'Legacy manual result'}</td></tr>)}</tbody></table></div></section>}
      </>}
      {tab === 'capital' && <section className="panel"><PanelHeading title="Owner capital & withdrawals" meta={`Summary through ${localDate(data.end)} · Table movements use selected dates · Funding, not revenue or operating expenses`} /><div className="cashbook-metrics"><div><span>Capital received so far</span><strong className="cash-in">{amount(data.lifetime.kind_totals.owner_capital)}</strong></div><div><span>Withdrawals so far</span><strong className="cash-out">{amount(data.lifetime.kind_totals.owner_withdrawal)}</strong></div></div>
        <div className="table-scroll"><table className="data-table cashbook-table"><thead><tr><th>Owner / partner</th><th className="numeric">Capital in period</th><th className="numeric">Withdrawn in period</th><th className="numeric">Net capital movements so far</th></tr></thead><tbody>{data.lifetime.owners.map(owner => { const period = data.summary.owners.find(item => item.owner === owner.owner); return <tr key={owner.owner}><td>{owner.owner}</td><td className="numeric cash-in">{amount(period?.capital || '0')}</td><td className="numeric cash-out">{amount(period?.withdrawals || '0')}</td><td className="numeric">{amount(owner.net)}</td></tr> })}</tbody></table></div>
        {!data.lifetime.owners.length && <EmptyState title="No owner movements yet" note="Record actual capital contributions or withdrawals to populate this summary." />}
      </section>}
      </section>
    </>}
    {helpOpen && <ModalFrame title="Cashbook FAQ" onClose={() => setHelpOpen(false)}>
      <div className="cashbook-help"><dl>
        <div><dt>What should I record here?</dt><dd>Actual cash received or paid by the company. Record loans and repayments from the Borrowings tab. Don’t duplicate project payments already recorded in project modules.</dd></div>
        <div><dt>How do I record an opening balance?</dt><dd>Enter the existing balance once per company account. Don’t enter the same starting money again as owner capital.</dd></div>
        <div><dt>How are categories and transaction types used?</dt><dd>Select a category, then its transaction type. The type determines whether the amount increases or reduces company cash.</dd></div>
        <div><dt>Are transfers between company accounts income or spending?</dt><dd>No. They are internal movements, not receipts or expenses.</dd></div>
        <div><dt>How are loans and interest tracked?</dt><dd>Use the Borrowings tab: New Loan for money borrowed, and Loan Repayment for principal and/or interest paid to a lender. Outstanding principal is borrowed less principal repaid. Interest counts as company spending; principal does not.</dd></div>
        <div><dt>Is this an accounting profit-and-loss statement?</dt><dd>No. Purchases, taxes, depreciation and liabilities may be treated differently. Project results are shown separately.</dd></div>
        <div><dt>Who can see this page?</dt><dd>Users with Company Cashbook access can see company-wide finance and project information, independent of project membership.</dd></div>
      </dl></div>
    </ModalFrame>}
    {entryOpen && <CashEntryForm csrf={csrf} canManage={canApprove} options={data?.options || []} projects={data?.projects || []} onCancel={() => setEntryOpen(false)} onSaved={async () => { setEntryOpen(false); setPage(1); await client.invalidateQueries({ queryKey: ['company-cashbook'] }) }} />}
    {borrowing && data && <BorrowingForm csrf={csrf} action={borrowing.action} initialLender={borrowing.lender} lenders={data.lifetime.borrowings} onCancel={() => setBorrowing(null)} onSaved={async text => { setBorrowing(null); setPage(1); await refresh(text) }} />}
    {lenderDetails !== null && data && <LenderDetails key={`${lenderDetails}:${data.end}`} csrf={csrf} canExport={canExport} onView={setEntryDetails} lender={lenderDetails} end={data.end} totals={data.lifetime.borrowings.find(lender => lender.lender === lenderDetails)} onClose={() => setLenderDetails(null)} />}
    {approvalTarget && <ModalFrame title={`Approve projected profit / loss · ${approvalTarget.project.name}`} onClose={() => setApprovalTarget(null)}><ApprovalForm csrf={csrf} project={approvalTarget.project} asOf={approvalTarget.asOf} onCancel={() => setApprovalTarget(null)} onSaved={async () => { setApprovalTarget(null); await refresh('Projected profit / loss approved. Company totals use the approved projection.') }} /></ModalFrame>}
    {entryDetails && <ModalFrame title={`Transaction details · ${entryDetails.reference_number}`} onClose={() => setEntryDetails(null)}>
      <TransactionDetails entryDetails={entryDetails} />
    </ModalFrame>}
    {resultDetails && data && <ModalFrame className={resultDetails.view === 'history' ? 'cashbook-history-modal' : ''} title={`${resultDetails.view === 'calculation' ? 'Calculation breakdown' : 'Approval history'} · ${resultDetails.project.name}`} onClose={() => setResultDetails(null)}>
      {resultDetails.view === 'calculation' ? <div className="cashbook-help"><p>Current projected profit / loss: <strong>{amount(resultDetails.project.calculated.amount)}</strong></p><CalculationDetails calculation={resultDetails.project.calculated} /></div> : <ProjectApprovalHistory records={data.approvals.filter(record => record.project_id === resultDetails.project.id)} />}
    </ModalFrame>}
    {voidTarget && <ModalFrame className="cashbook-void-modal" title={`Mark as invalid · ${voidTarget.label}`} onClose={() => { if (!voidRecord.isPending) setVoidTarget(null) }}>
      <TransactionDetails entryDetails={voidTarget.entry} />
      <form className="form-grid" onSubmit={event => { event.preventDefault(); voidRecord.mutate() }}>
        <label className="field full">Reason<textarea rows={2} required minLength={5} maxLength={500} value={reason} onChange={event => setReason(event.target.value)} /></label>
        <MutationError error={voidRecord.error} /><FormActions busy={voidRecord.isPending} disabled={reason.trim().length < 5} onCancel={() => setVoidTarget(null)} submit="Mark as invalid" />
      </form>
    </ModalFrame>}
  </div>
}

function LenderDetails({ csrf, lender, end, totals, canExport, onView, onClose }: { csrf: string; lender: string; end: string; totals: CashbookData['lifetime']['borrowings'][number] | undefined; canExport: boolean; onView: (entry: CashbookData['items'][number]) => void; onClose: () => void }) {
  const [page, setPage] = useState(1)
  const [size, setSize] = useState(10)
  const [printRows, setPrintRows] = useState<CashbookData['items'] | null>(null)
  const filters: CashFilters = { start: '', end, search: '', kind: 'borrowings', custom_category: '', category: '', direction: '', status: 'all', lender }
  const history = useQuery({
    queryKey: ['company-cashbook', 'lender', lender, end, page, size],
    queryFn: () => api.cashbook(filters, page, size),
  })
  const exportReport = useMutation({
    mutationFn: async () => {
      const report = await api.exportCashbook(filters, csrf)
      setPrintRows(report.items)
      document.body.classList.add('cashbook-lender-printing')
      await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
      await document.fonts.ready
      const title = document.title
      document.title = `Borrowing details - ${lender} - ${end}`
      const restore = () => { document.title = title; document.body.classList.remove('cashbook-lender-printing'); setPrintRows(null) }
      window.addEventListener('afterprint', restore, { once: true })
      try { window.print() } catch (error) { window.removeEventListener('afterprint', restore); restore(); throw error }
    },
  })
  useEffect(() => () => document.body.classList.remove('cashbook-lender-printing'), [])
  const rows = printRows || history.data?.items || []
  return <ModalFrame className="cashbook-lender-modal" title={`Borrowing details · ${lender}`} onClose={onClose}>
    <ExportHeader reportTitle={`Company Cashbook · Borrowing details · ${lender}`} />
    {canExport && <div className="cashbook-lender-toolbar">
      <button type="button" className="button-secondary" disabled={exportReport.isPending || !history.data?.total} onClick={() => exportReport.mutate()}><Download size={15} />{exportReport.isPending ? 'Preparing…' : 'Download Report'}</button>
    </div>}
    <MutationError error={exportReport.error} />
    {totals && <div className="cashbook-metrics cashbook-loan-metrics">
      <div><span>Outstanding principal</span><strong>{amount(totals.outstanding)}</strong></div>
      <div><span>Total borrowed</span><strong className="cash-in">{amount(totals.borrowed)}</strong></div>
      <div><span>Principal repaid</span><strong className="cash-out">{amount(totals.repaid)}</strong></div>
      <div><span>Interest paid</span><strong className="cash-out">{amount(totals.interest)}</strong></div>
    </div>}
    <PanelHeading title="Loan & repayment history" meta="Newest transaction dates first · Principal and interest payments are listed separately" />
    <QueryError error={history.error} onRetry={() => void history.refetch()} />
    {history.isFetching && <div className="loading-line" role="status" aria-label="Loading lender history" />}
    {history.data && !history.isError && <>
      <div className="table-scroll"><table className="data-table cashbook-table"><thead><tr><th>Date</th><th>Transaction</th><th className="numeric">Amount</th><th>Mode / account</th><th>Purpose / reference</th><th>Status</th><th className="cashbook-result-actions-column">Details</th></tr></thead><tbody>
        {rows.map(entry => <tr key={entry.id} className={entry.voided_at ? 'cashbook-voided' : ''}>
          <td>{localDate(entry.transaction_date)}</td><td>{entry.category}</td>
          <td className={`numeric ${entry.direction === 'in' ? 'cash-in' : 'cash-out'}`}>{amount(entry.amount)}<small>{entry.direction === 'in' ? 'Money in' : 'Money out'}</small></td>
          <td>{entry.payment_mode}<small>{entry.account}</small></td>
          <td>{entry.description}<small>{entry.reference || 'No reference'}</small></td>
          <td>{entry.voided_at ? 'Marked as invalid' : 'Posted'}</td>
          <td className="cashbook-result-actions-column"><span className="row-action-tooltip" data-tooltip="View transaction details"><button type="button" className="icon-button" aria-label={`View ${entry.reference_number}`} aria-haspopup="dialog" onClick={() => onView(entry)}><Eye size={17} aria-hidden="true" /></button></span></td>
        </tr>)}
      </tbody></table></div>
      {!history.data.total && <EmptyState title="No loan or repayment history" note="No borrowing transactions were recorded for this lender through the selected end date." />}
      {!printRows && <Pager page={page} size={size} total={history.data.total} busy={history.isFetching} setPage={setPage} setSize={value => { setSize(value); setPage(1) }} rowsLabel="Lender history rows per page" />}
    </>}
  </ModalFrame>
}

function TransactionDetails({ entryDetails }: { entryDetails: CashbookData['items'][number] }) {
  return <dl className="cashbook-entry-details">{([
        ['Transaction date', localDate(entryDetails.transaction_date)], ['Category', entryDetails.custom_category || cashKinds[entryDetails.kind]],
        ['Transaction type', entryDetails.category],
        ['Amount', amount(entryDetails.amount)], ['Direction', entryDetails.direction === 'in' ? 'Money in' : 'Money out'],
        ['Status', entryDetails.voided_at ? 'Marked as invalid' : 'Posted'],
        ['Party', entryDetails.party], ['Purpose', entryDetails.description],
        ['Linked project', entryDetails.project_name || 'Not linked'], ['Account', entryDetails.account],
        ['Payment mode', entryDetails.payment_mode], ['Payment reference', entryDetails.reference || 'Not provided'],
        ['Recorded by', entryDetails.recorded_by], ['Recorded on', new Date(entryDetails.recorded_at).toLocaleString('en-IN')],
        ['Record ID', entryDetails.id],
        ...(entryDetails.voided_at ? [
          ['Marked invalid by', entryDetails.voided_by], ['Marked invalid on', new Date(entryDetails.voided_at).toLocaleString('en-IN')],
          ['Reason', entryDetails.void_reason],
        ] : []),
      ]).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
}

export function CompanyAuditLog({ csrf, canExport }: { csrf: string; canExport: boolean }) {
  const visit = useCashbookVisit('audit-log', csrf)
  return <div className="company-cashbook">
    <PageTitle eyebrow="COMPANY ACTIVITY" title="Company Audit Log" subtitle="Recorded Company Cashbook activity across all dates. Independent of the selected project." />
    <QueryError error={visit.error} onRetry={() => visit.mutate('audit-log')} />
    <CashbookHistory source="audit-log" csrf={csrf} canExport={canExport} />
  </div>
}

function CashbookHistory({ source = 'history', csrf, canExport }: { source?: 'history' | 'audit-log'; csrf: string; canExport: boolean }) {
  const reportTitle = source === 'audit-log' ? 'Company Audit Log' : 'Company Cashbook history'
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [search, setSearch] = useState('')
  const [fromTime, setFromTime] = useState('')
  const [toTime, setToTime] = useState('')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const filterContainer = useRef<HTMLDivElement>(null)
  const filterButton = useRef<HTMLButtonElement>(null)
  const [details, setDetails] = useState<CashHistory['items'][number] | null>(null)
  const [printRows, setPrintRows] = useState<CashHistory['items'] | null>(null)
  const startTime = fromTime ? new Date(fromTime).toISOString() : ''
  const endTime = toTime ? new Date(toTime).toISOString() : ''
  const invalidRange = Boolean(startTime && endTime && startTime > endTime)
  useEffect(() => {
    if (!filtersOpen) return
    const outside = (event: PointerEvent) => {
      if (event.target instanceof Node && !filterContainer.current?.contains(event.target)) setFiltersOpen(false)
    }
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setFiltersOpen(false); filterButton.current?.focus() }
    }
    document.addEventListener('pointerdown', outside)
    document.addEventListener('keydown', escape)
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', escape) }
  }, [filtersOpen])
  const history = useQuery({
    queryKey: ['company-cashbook', source, page, pageSize, search, startTime, endTime],
    queryFn: () => source === 'audit-log' ? api.companyAuditLog(page, pageSize, search, startTime, endTime) : api.cashbookHistory(page, pageSize, search, startTime, endTime),
    enabled: !invalidRange,
  })
  const exportReport = useMutation({ mutationFn: async () => {
    const report = await api.exportCashbookHistory(source, search, startTime, endTime, csrf)
    setPrintRows(report.items)
    document.body.classList.add('cashbook-history-printing')
    const originalTitle = document.title
    const restore = () => { document.title = originalTitle; document.body.classList.remove('cashbook-history-printing'); setPrintRows(null) }
    try {
      await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
      await document.fonts.ready
      document.title = reportTitle
      window.addEventListener('afterprint', restore, { once: true })
      window.print()
    } catch (error) {
      window.removeEventListener('afterprint', restore)
      restore()
      throw error
    }
  }, onSuccess: () => { void history.refetch() } })
  useEffect(() => () => document.body.classList.remove('cashbook-history-printing'), [])
  const rows = printRows || history.data?.items || []
  return <div className="cashbook-history-report">
    <ExportHeader reportTitle={reportTitle} />
    <section className="panel table-panel cashbook-activity-history">
    <PanelHeading title="Company Cashbook history" meta={`${printRows?.length ?? history.data?.total ?? 0} records · Newest first`} action={<div className="audit-time-filters">
      <div ref={filterContainer} className="audit-filter-control">
        <span className={`row-action-tooltip user-badge-tooltip${filtersOpen ? ' audit-filter-tooltip-hidden' : ''}`} data-tooltip={fromTime || toTime ? 'Time range filter active' : 'Filter by time range'}><button ref={filterButton} type="button" className={`icon-button audit-filter-trigger${fromTime || toTime ? ' active' : ''}`} aria-label="Filter by time range" aria-expanded={filtersOpen} aria-controls={`cashbook-${source}-time-range`} onClick={() => setFiltersOpen(previous => !previous)}><CalendarRange size={17} />{(fromTime || toTime) && <span className="audit-filter-indicator" />}</button></span>
        {filtersOpen && <div id={`cashbook-${source}-time-range`} className="audit-filter-popover" role="group" aria-label="Audit time range">
          <AuditDateRange from={fromTime} to={toTime} onApply={(from, to) => { setFromTime(from); setToTime(to); setPage(1) }} onClose={() => { setFiltersOpen(false); filterButton.current?.focus() }} />
        </div>}
      </div>
      <span className="row-action-tooltip user-badge-tooltip" data-tooltip="Clear audit filters"><button type="button" className="icon-button" aria-label="Clear audit filters" disabled={!fromTime && !toTime && !search} onClick={() => { setFromTime(''); setToTime(''); setSearch(''); setPage(1) }}><FilterX size={17} /></button></span>
      <div className="search-wrap"><Search size={15} /><input type="search" aria-label="Search audit log" placeholder="Search username or activity" maxLength={200} value={search} onChange={event => { setSearch(event.target.value); setPage(1) }} /></div>
      {canExport && <button className="button-secondary export-report-action" disabled={exportReport.isPending || invalidRange} onClick={() => exportReport.mutate()}><Download size={15} />{exportReport.isPending ? 'Preparing report...' : 'Download Report'}</button>}
    </div>} />
    {invalidRange && <div className="form-error" role="alert">From date and time must be before To date and time.</div>}
    <QueryError error={history.error} onRetry={() => void history.refetch()} />
    <MutationError error={exportReport.error} />
    {printRows && <p className="audit-report-filters">Period: {fromTime ? new Date(fromTime).toLocaleString('en-IN') : 'Beginning'} to {toTime ? new Date(toTime).toLocaleString('en-IN') : 'Present'}{search && ` · Search: ${search}`}</p>}
    <div className="table-scroll"><table className="data-table cashbook-table"><thead><tr><th>Date & time</th><th>Username</th><th>Activity</th>{!printRows && <th>Details</th>}</tr></thead><tbody>{rows.map(event => <tr key={event.id}><td>{new Date(event.occurred_at).toLocaleString('en-IN')}</td><td>{event.actor}</td><td>{cashActivityLabel(event.action)}</td>{!printRows && <td>
      <span className="row-action-tooltip" data-tooltip="View activity details"><button type="button" className="icon-button" aria-label="View activity details" aria-haspopup="dialog" onClick={() => setDetails(event)}><Eye size={17} aria-hidden="true" /></button></span>
    </td>}</tr>)}</tbody></table></div>
    {history.isLoading && <div className="loading-line" />}
    {!history.isLoading && !history.isError && !rows.length && <EmptyState title="No matching activities" note="Try another search or clear the audit filters." />}
    {!printRows && <Pager page={page} size={pageSize} total={history.data?.total || 0} busy={history.isFetching} setPage={setPage} setSize={size => { setPageSize(size); setPage(1) }} sizes={[10, 20, 50, 100]} rowsLabel="Company audit rows per page" />}
    {details && <ActivityRecordModal activity={details} source={source} csrf={csrf} canExport={canExport} onClose={() => setDetails(null)} />}
  </section></div>
}

const recordActions = new Set(['cashbook_entry_recorded', 'cashbook_borrowing_recorded', 'cashbook_record_voided', 'project_result_approved', 'cashbook_option_created'])

function ActivityRecordModal({ activity, source, csrf, canExport, onClose }: { activity: CashHistory['items'][number]; source: 'history' | 'audit-log'; csrf: string; canExport: boolean; onClose: () => void }) {
  const client = useQueryClient()
  const hasRecord = Boolean(activity.record_id && recordActions.has(activity.action))
  const record = useQuery({ queryKey: ['company-cashbook', 'record', activity.record_id], queryFn: () => api.cashbookRecord(activity.record_id as string), enabled: hasRecord, retry: false, gcTime: 0 })
  const denied = record.error instanceof ApiError && record.error.status === 403
  const missing = record.error instanceof ApiError && record.error.status === 404
  const exportReport = useMutation({ mutationFn: async () => {
    await api.exportCashbookActivity(activity.id, source, csrf)
    const originalTitle = document.title
    const restore = () => { document.title = originalTitle; document.body.classList.remove('cashbook-activity-printing') }
    try {
      document.body.classList.add('cashbook-activity-printing')
      await document.fonts.ready
      document.title = `Activity - ${cashActivityLabel(activity.action)}`
      window.addEventListener('afterprint', restore, { once: true })
      window.print()
    } catch (error) {
      window.removeEventListener('afterprint', restore)
      restore()
      throw error
    }
  }, onSuccess: () => { void client.invalidateQueries({ queryKey: ['company-cashbook', source] }) } })
  useEffect(() => () => document.body.classList.remove('cashbook-activity-printing'), [])
  return <ModalFrame className="cashbook-activity-modal" title={hasRecord ? 'Activity entry' : 'Activity details'} onClose={onClose}>
    <ExportHeader reportTitle="Activity details" />
    {canExport && <div className="cashbook-activity-toolbar"><button type="button" className="button-secondary export-report-action" disabled={exportReport.isPending || hasRecord && (!record.data || record.isError)} onClick={() => exportReport.mutate()}><Download size={15} />{exportReport.isPending ? 'Preparing report...' : 'Download Report'}</button></div>}
    <MutationError error={exportReport.error} />
    <dl className="cashbook-activity-summary">
      <div><dt>Activity</dt><dd>{cashActivityLabel(activity.action)}</dd></div>
      <div><dt>Performed by</dt><dd>{activity.actor}</dd></div>
      <div><dt>Date &amp; time</dt><dd>{new Date(activity.occurred_at).toLocaleString('en-IN')}</dd></div>
    </dl>
    {hasRecord && record.isLoading && <div className="loading-line" role="status" aria-label="Loading activity entry" />}
    {denied && <div className="form-error" role="alert">You don't have permission to view this activity's entry. Ask an administrator for Company Cashbook access.</div>}
    {missing && <div className="form-error" role="alert">This activity's entry is no longer available.</div>}
    {hasRecord && !denied && !missing && <QueryError error={record.error} onRetry={() => void record.refetch()} />}
    {record.data ? <section className="cashbook-activity-content"><ActivityRecord data={record.data} /></section> : !hasRecord && <section className="cashbook-activity-content"><h3>Recorded details</h3><HistoryDetails details={activity.details} /></section>}
  </ModalFrame>
}

function ActivityRecord({ data }: { data: CashActivityRecord }) {
  if (data.type === 'entry') return <><h3>Cash transaction {data.record.reference_number}</h3><TransactionDetails entryDetails={data.record} /></>
  const rows: [string, string][] = data.type === 'approval'
    ? [['Project', data.record.project_name], ['As of', localDate(data.record.as_of)], ['Approved projected profit / loss', amount(data.record.amount)], ['Note', data.record.note], ['Approved by', data.record.approved_by], ['Approved on', new Date(data.record.approved_at).toLocaleString('en-IN')], ['Record ID', data.record.id]]
    : data.type === 'result'
      ? [['Project', data.record.project_name], ['As of', localDate(data.record.as_of)], ['Result', amount(data.record.amount)], ['Basis', data.record.basis], ['Status', data.record.voided_at ? 'Marked as invalid' : 'Posted'], ['Recorded by', data.record.recorded_by], ['Recorded on', new Date(data.record.recorded_at).toLocaleString('en-IN')], ...(data.record.void_reason ? [['Reason', data.record.void_reason] as [string, string]] : []), ['Record ID', data.record.id]]
      : [[data.record.option_type === 'category' ? 'Category' : 'Transaction type', data.record.name], ['Financial behavior', cashKinds[data.record.kind]], ...(data.record.parent ? [['Under category', data.record.parent] as [string, string]] : []), ...(data.record.direction ? [['Direction', data.record.direction === 'in' ? 'Money in' : 'Money out'] as [string, string]] : []), ['Record ID', data.record.id]]
  const title = data.type === 'approval' ? 'Project profit / loss approval' : data.type === 'result' ? 'Project result' : data.record.option_type === 'category' ? 'Cashbook category' : 'Cashbook transaction type'
  return <><h3>{title}</h3><dl className="cashbook-entry-details">{rows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl></>
}

function Pager({ page, size, total, busy, setPage, setSize, sizes = [10, 20, 50, 100], rowsLabel = 'Cashbook rows per page' }: { page: number; size: number; total: number; busy: boolean; setPage: (page: number) => void; setSize?: (size: number) => void; sizes?: number[]; rowsLabel?: string }) {
  const pages = Math.max(1, Math.ceil(total / size))
  return <div className="register-pagination">{setSize && <label>Rows <select aria-label={rowsLabel} value={size} onChange={event => setSize(Number(event.target.value))}>{sizes.map(value => <option key={value}>{value}</option>)}</select></label>}<span>{total} records · Page {page} of {pages}</span><div className="row-actions"><button className="icon-button" aria-label="Previous page" disabled={busy || page <= 1} onClick={() => setPage(page - 1)}><ChevronLeft size={16} /></button><button className="icon-button" aria-label="Next page" disabled={busy || page >= pages} onClick={() => setPage(page + 1)}><ChevronRight size={16} /></button></div></div>
}

const historyLabels: Record<string, string> = { kind: 'financial behavior', custom_category: 'category', category: 'transaction type', option_type: 'added', parent: 'under category', first_type: 'first transaction type', backup_created_at: 'backup made', backup_created_by: 'backup made by', safety_backup: 'safety copy', passphrase_changed: 'passphrase changed', documents: 'documents', rows: 'rows' }

function HistoryDetails({ details }: { details: Record<string, unknown> | null }) {
  if (!details || !Object.keys(details).length) return <p className="cashbook-activity-empty">No additional details recorded.</p>
  const source = details.after && typeof details.after === 'object' ? details.after : details
  return <dl className="cashbook-history-details">{Object.entries(source).filter(([key]) => key !== 'request_id').map(([key, value]) => <div key={key}><dt>{historyLabels[key] || key.replaceAll('_', ' ')}</dt><dd><HistoryValue value={value} /></dd></div>)}</dl>
}

function HistoryValue({ value }: { value: unknown }) {
  if (value == null || value === '') return <>Not provided</>
  if (typeof value === 'boolean') return <>{value ? 'Yes' : 'No'}</>
  if (Array.isArray(value)) return <ul>{value.map((item, index) => <li key={index}><HistoryValue value={item} /></li>)}</ul>
  if (typeof value === 'object') return <HistoryDetails details={Object.fromEntries(Object.entries(value))} />
  return <>{String(value)}</>
}

function CashEntryForm({ csrf, canManage, options: initialOptions, projects, onSaved, onCancel }: { csrf: string; canManage: boolean; options: CashOption[]; projects: CashbookData['projects']; onSaved: () => Promise<void>; onCancel: () => void }) {
  const [input, setInput] = useState<CashInput>({ request_id: crypto.randomUUID(), transaction_date: today(), kind: 'company_expense', category: 'Company purchases', amount: '', party: '', description: '', account: '', payment_mode: 'Bank transfer', reference: '', project_id: null })
  const client = useQueryClient()
  const [options, setOptions] = useState(initialOptions)
  const [newOption, setNewOption] = useState<CashOptionInput | null>(null)
  const addOption = useMutation({
    mutationFn: (option: CashOptionInput) => api.addCashbookOption(option, csrf),
    onSuccess: async ({ items }) => {
      setOptions(previous => [...previous, ...items])
      const type = items.find(option => option.option_type === 'type')
      if (type) setInput(previous => ({ ...previous, kind: type.kind, custom_category: type.parent || null, category: type.name, project_id: type.kind === previous.kind ? previous.project_id : null }))
      setNewOption(null)
      await client.invalidateQueries({ queryKey: ['company-cashbook'] })
    },
  })
  const customCategories = options.filter(option => option.option_type === 'category')
  const typesFor = (kind: CashKind, parent: string) => [...(parent ? [] : cashCategories[kind]), ...options.filter(option => option.option_type === 'type' && option.kind === kind && option.parent === parent).map(option => option.name)]
  const types = typesFor(input.kind, input.custom_category || '')
  const selectedOption = options.find(option => option.option_type === 'type' && option.kind === input.kind && option.parent === (input.custom_category || '') && option.name === input.category)
  const moneyIn = selectedOption ? selectedOption.direction === 'in' : incoming(input.kind)
  const categoryLabel = input.custom_category || cashKinds[input.kind]
  const selectCategory = (value: string) => {
    const custom = customCategories.find(option => `custom:${option.name}` === value)
    const kind = custom?.kind || value as CashKind
    setInput({ ...input, kind, custom_category: custom?.name || null, category: typesFor(kind, custom?.name || '')[0] || '', project_id: null })
  }
  const beginOption = (option_type: CashOptionInput['option_type']) => {
    addOption.reset()
    setNewOption(option_type === 'category' ? { option_type, kind: 'company_expense', parent: '', name: '', first_type: '', direction: 'out' } : { option_type, kind: input.kind, parent: input.custom_category || '', name: '', direction: moneyIn ? 'in' : 'out' })
  }
  const optionReady = Boolean(newOption?.name.trim() && (newOption.option_type === 'type' || newOption.first_type?.trim()))
  const projectTransfer = ['project_received', 'project_funding'].includes(input.kind)
  const defaultAccount = input.payment_mode === 'Cash' ? 'Cash' : input.payment_mode === 'Other' ? 'Others' : ''
  const opening = input.kind.startsWith('opening_')
  const canSubmit = Boolean(
    input.transaction_date && input.transaction_date <= today() &&
    /^\d+(\.\d{1,2})?$/.test(input.amount) && Number(input.amount) > 0 &&
    Number(input.amount) <= 9999999999999999.99 &&
    input.kind && input.category && input.payment_mode &&
    input.party.trim() && input.description.trim() &&
    (defaultAccount || input.account.trim()) &&
    (!projectTransfer || input.project_id),
  )
  const save = useMutation({ mutationFn: () => api.recordCompanyCash(input, csrf), onSuccess: onSaved })
  const closeOption = () => { if (!addOption.isPending) setNewOption(null) }
  if (newOption) return <ModalFrame title={newOption.option_type === 'type' ? 'New transaction type' : 'New category'} onClose={closeOption}>
    <form className="form-grid" onSubmit={event => { event.preventDefault(); if (optionReady && !addOption.isPending) addOption.mutate(newOption) }}>
      {newOption.option_type === 'type' && <p className="cashbook-help full">Under category: <strong>{categoryLabel}</strong></p>}
      <label className="field full">{newOption.option_type === 'type' ? 'Transaction type name *' : 'Category name *'}<input autoFocus required maxLength={80} value={newOption.name} disabled={addOption.isPending} onChange={event => setNewOption({ ...newOption, name: event.target.value })} /></label>
      {newOption.option_type === 'category' && <>
        <label className="field full">First transaction type *<input required maxLength={80} value={newOption.first_type || ''} disabled={addOption.isPending} onChange={event => setNewOption({ ...newOption, first_type: event.target.value })} /></label>
      </>}
      <label className="field full">{newOption.option_type === 'category' ? 'First transaction type direction *' : 'Money direction *'}<select required value={newOption.direction} disabled={addOption.isPending} onChange={event => setNewOption({ ...newOption, direction: event.target.value === 'in' ? 'in' : 'out' })}><option value="out">Money out — reduces company cash</option><option value="in">Money in — increases company cash</option></select></label>
      <MutationError error={addOption.error} />
      <FormActions busy={addOption.isPending} disabled={!optionReady} onCancel={closeOption} submit="Add" />
    </form>
  </ModalFrame>
  return <ModalFrame title="New cash transaction" onClose={onCancel}><form className="form-grid" onSubmit={event => { event.preventDefault(); if (canSubmit && !save.isPending) save.mutate() }}>
    <label className="field">Date *<input type="date" required max={today()} value={input.transaction_date} onChange={event => setInput({ ...input, transaction_date: event.target.value })} /></label>
    <div className="cashbook-option-field"><label className="field">Category *<select required value={input.custom_category ? `custom:${input.custom_category}` : input.kind} onChange={event => selectCategory(event.target.value)}>{Object.entries(cashKinds).filter(([kind]) => kind !== 'borrowings').map(([kind, label]) => <option key={kind} value={kind}>{label}</option>)}{customCategories.map(option => <option key={option.id} value={`custom:${option.name}`}>{option.name}</option>)}</select></label>{canManage && <span className="row-action-tooltip" data-tooltip="New category"><button type="button" className="icon-button" aria-label="New category" disabled={newOption !== null || save.isPending} onClick={() => beginOption('category')}><FolderPlus size={17} aria-hidden="true" /></button></span>}</div>
    <label className="field">Paid to / received from *<input required maxLength={160} value={input.party} onChange={event => setInput({ ...input, party: event.target.value })} /></label>
    <div className="cashbook-option-field"><label className="field">Transaction type *<select required value={input.category} onChange={event => setInput({ ...input, category: event.target.value })}>{types.map(type => <option key={type}>{type}</option>)}</select></label>{canManage && <span className="row-action-tooltip" data-tooltip="New transaction type"><button type="button" className="icon-button" aria-label="New transaction type" disabled={newOption !== null || save.isPending} onClick={() => beginOption('type')}><ListPlus size={17} aria-hidden="true" /></button></span>}</div>
    <label className="field">Amount *<input type="number" required min="0.01" max="9999999999999999.99" step="0.01" value={input.amount} onChange={event => setInput({ ...input, amount: event.target.value })} /></label>
    <label className="field">Payment mode *<select required value={input.payment_mode} onChange={event => setInput({ ...input, payment_mode: event.target.value as CashInput['payment_mode'] })}>{['Bank transfer', 'Cash', 'UPI', 'Cheque', 'Other'].map(mode => <option key={mode}>{mode}</option>)}</select></label>
    <div className="full cashbook-account-reference">
      <label className="field cashbook-account-field cashbook-optional-field">Company account{defaultAccount ? ' (optional)' : ' *'}<input aria-describedby="cashbook-account-hint" required={!defaultAccount} maxLength={100} placeholder={defaultAccount ? `Leave blank to use "${defaultAccount}"` : 'e.g. HDFC current account'} value={input.account} onChange={event => setInput({ ...input, account: event.target.value })} /></label>
      <label className="field cashbook-optional-field">Reference (optional)<input maxLength={100} value={input.reference || ''} onChange={event => setInput({ ...input, reference: event.target.value })} /></label>
      <small id="cashbook-account-hint" className="cashbook-account-hint">{defaultAccount ? `Blank entries are grouped under "${defaultAccount}". ` : ''}Use the exact same account name for its future entries.</small>
    </div>
    {projectTransfer && <label className="field full">Linked Project *<select required value={input.project_id || ''} onChange={event => setInput({ ...input, project_id: event.target.value || null })}><option value="">Select project</option>{projects.filter(project => !project.archived).map(project => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label>}
    <label className="field full cashbook-description-field">Purpose / description *<textarea required maxLength={500} value={input.description} onChange={event => setInput({ ...input, description: event.target.value })} /></label>
    <div className="cashbook-help full">{moneyIn ? 'Money in increases' : 'Money out reduces'} recorded company cash. {opening ? 'Starting balance: record the balance already held when this register begins. Enter it once per account. It is not owner capital or operating income.' : projectTransfer ? 'This does not declare project profit/loss or duplicate project vendor/client transactions.' : 'Company spending is not automatically an accounting expense; purchases may be assets.'}</div>
    <MutationError error={save.error} /><FormActions busy={save.isPending} disabled={!canSubmit || newOption !== null} onCancel={onCancel} submit="Record transaction" />
  </form></ModalFrame>
}

const modes: CashInput['payment_mode'][] = ['Bank transfer', 'Cash', 'UPI', 'Cheque', 'Other']
const money = /^\d+(\.\d{1,2})?$/

function BorrowingForm({ csrf, action, initialLender, lenders, onSaved, onCancel }: { csrf: string; action: BorrowingInput['action']; initialLender: string; lenders: CashbookData['lifetime']['borrowings']; onSaved: (message: string) => Promise<void>; onCancel: () => void }) {
  const repayment = action === 'repayment'
  const owing = lenders.filter(lender => Number(lender.outstanding) > 0)
  const [input, setInput] = useState<BorrowingInput>({ request_id: crypto.randomUUID(), action, transaction_date: today(), lender: initialLender || (repayment ? owing[0]?.lender || '' : ''), principal: '', interest: '', description: '', account: '', payment_mode: 'Bank transfer', reference: '' })
  const selected = lenders.find(lender => lender.lender.toLocaleLowerCase() === input.lender.trim().toLocaleLowerCase())
  const principal = input.principal ? Number(input.principal) : 0
  const interest = input.interest ? Number(input.interest) : 0
  const defaultAccount = input.payment_mode === 'Cash' ? 'Cash' : input.payment_mode === 'Other' ? 'Others' : ''
  const amountsValid = (!input.principal || money.test(input.principal)) && (!input.interest || money.test(input.interest))
  const overRepaid = repayment && selected !== undefined && principal > Number(selected.outstanding)
  const canSubmit = Boolean(
    input.transaction_date && input.transaction_date <= today() && input.lender.trim() && input.description.trim() &&
    (defaultAccount || input.account.trim()) && amountsValid &&
    (repayment ? selected && Number(selected.outstanding) > 0 && principal + interest > 0 && !overRepaid : principal > 0),
  )
  const save = useMutation({
    mutationFn: () => api.recordBorrowing({ ...input, lender: input.lender.trim(), principal: input.principal || '0', interest: repayment ? input.interest || '0' : '0', reference: input.reference || null }, csrf),
    onSuccess: () => onSaved(repayment ? 'Repayment recorded. Outstanding principal and interest paid have been updated.' : 'Loan recorded. It now appears under outstanding borrowings.'),
  })
  return <ModalFrame title={repayment ? 'Record loan repayment' : 'Record loan received'} onClose={() => { if (!save.isPending) onCancel() }}><form className="form-grid" onSubmit={event => { event.preventDefault(); if (canSubmit && !save.isPending) save.mutate() }}>
    <label className="field">Date *<input type="date" required max={today()} value={input.transaction_date} onChange={event => setInput({ ...input, transaction_date: event.target.value })} /></label>
    {repayment
      ? <label className="field">Lender *<select required value={selected?.lender || ''} onChange={event => setInput({ ...input, lender: event.target.value })}>{owing.map(lender => <option key={lender.lender} value={lender.lender}>{lender.lender} · {amount(lender.outstanding)} outstanding</option>)}</select></label>
      : <label className="field">Lender *<input required maxLength={160} list="cashbook-lenders" placeholder="Bank, NBFC or person" value={input.lender} onChange={event => setInput({ ...input, lender: event.target.value })} /><datalist id="cashbook-lenders">{lenders.map(lender => <option key={lender.lender} value={lender.lender} />)}</datalist></label>}
    {repayment ? <>
      <label className="field">Principal repaid<input type="number" min="0" max={selected?.outstanding} step="0.01" placeholder="0.00" value={input.principal} onChange={event => setInput({ ...input, principal: event.target.value })} /></label>
      <label className="field">Interest paid<input type="number" min="0" step="0.01" placeholder="0.00" value={input.interest} onChange={event => setInput({ ...input, interest: event.target.value })} /></label>
    </> : <label className="field">Amount received *<input type="number" required min="0.01" step="0.01" value={input.principal} onChange={event => setInput({ ...input, principal: event.target.value })} /></label>}
    <label className="field">Payment mode *<select required value={input.payment_mode} onChange={event => setInput({ ...input, payment_mode: event.target.value as CashInput['payment_mode'] })}>{modes.map(mode => <option key={mode}>{mode}</option>)}</select></label>
    <div className="full cashbook-account-reference">
      <label className="field cashbook-account-field cashbook-optional-field">Company account{defaultAccount ? ' (optional)' : ' *'}<input required={!defaultAccount} maxLength={100} placeholder={defaultAccount ? `Leave blank to use "${defaultAccount}"` : 'e.g. HDFC current account'} value={input.account} onChange={event => setInput({ ...input, account: event.target.value })} /></label>
      <label className="field cashbook-optional-field">Reference (optional)<input maxLength={100} placeholder={repayment ? 'EMI / UTR number' : 'Loan account / sanction number'} value={input.reference || ''} onChange={event => setInput({ ...input, reference: event.target.value })} /></label>
    </div>
    <label className="field full cashbook-description-field">Purpose / description *<textarea required maxLength={500} value={input.description} onChange={event => setInput({ ...input, description: event.target.value })} /></label>
    <div className="cashbook-help full">{repayment
      ? <>{selected && <>Outstanding with {selected.lender}: <strong>{amount(selected.outstanding)}</strong>. </>}Total paid: <strong>{amount(String(principal + interest))}</strong>. Principal reduces the loan balance; interest is company spending. {overRepaid && <strong className="cash-out">Principal cannot exceed the outstanding amount.</strong>}</>
      : 'Money borrowed increases company cash and outstanding borrowings. It is not income or owner capital.'}</div>
    <MutationError error={save.error} /><FormActions busy={save.isPending} disabled={!canSubmit} onCancel={onCancel} submit="Save" />
  </form></ModalFrame>
}

function ProjectApprovalHistory({ records }: { records: CashbookData['approvals'] }) {
  if (!records.length) return <EmptyState title="No approvals yet" note="This project has not been approved in the selected date range." />
  return <ApprovalHistoryTable records={records} />
}

function ApprovalHistoryTable({ records, currentIds, showProject = false, printMode = false }: { records: CashbookData['approvals']; currentIds?: Set<string>; showProject?: boolean; printMode?: boolean }) {
  const [search, setSearch] = useState('')
  const [approvedBy, setApprovedBy] = useState('')
  const [page, setPage] = useState(1)
  const [size, setSize] = useState(5)
  const [breakdown, setBreakdown] = useState<CashbookData['approvals'][number] | null>(null)
  const term = search.trim().toLowerCase()
  const filtered = records.filter(record => (!approvedBy || record.approved_by === approvedBy) &&
    (!term || [record.project_name, record.note, record.approved_by, record.as_of, record.amount].some(value => value.toLowerCase().includes(term))))
  const currentPage = Math.min(page, Math.max(1, Math.ceil(filtered.length / size)))
  const rows = printMode ? filtered : filtered.slice((currentPage - 1) * size, currentPage * size)
  const tools = <div className="cashbook-project-tools cashbook-approval-tools">
      <label className="search-wrap"><Search size={15} aria-hidden="true" /><input type="search" aria-label="Search approval history" placeholder="Search approval history" value={search} onChange={event => { setSearch(event.target.value); setPage(1) }} /></label>
      <label className="row-action-tooltip cashbook-project-filter" data-tooltip="Approved by"><UserCheck size={15} aria-hidden="true" /><select aria-label="Approved by" value={approvedBy} onChange={event => { setApprovedBy(event.target.value); setPage(1) }}><option value="">All approvers</option>{[...new Set(records.map(record => record.approved_by))].sort().map(name => <option key={name}>{name}</option>)}</select></label>
      <span className="row-action-tooltip" data-tooltip="Clear approval filters"><button type="button" className="icon-button" aria-label="Clear approval filters" disabled={!search && !approvedBy} onClick={() => { setSearch(''); setApprovedBy(''); setPage(1) }}><FilterX size={17} aria-hidden="true" /></button></span>
    </div>
  return <>
    {showProject ? <PanelHeading title="Approval history" meta="Saved calculation snapshots · Only the latest approval per project counts" action={tools} /> : tools}
    <div className="table-scroll"><table className="data-table cashbook-table cashbook-approval-table"><thead><tr>{showProject && <th>Project</th>}<th>As of</th><th className="numeric">Approved projection</th><th>Approval note</th><th>Approved by</th><th>Approved on</th>{currentIds && <th>Status</th>}<th className="cashbook-result-actions-column">Breakdown</th></tr></thead><tbody>{rows.map(record => <tr key={record.id}>
      {showProject && <td><strong>{record.project_name}</strong></td>}
      <td className="cashbook-approval-date">{localDate(record.as_of)}</td>
      <td className="numeric"><strong className={Number(record.amount) < 0 ? 'cash-out' : 'cash-in'}>{amount(record.amount)}</strong></td>
      <td>{record.note}</td>
      <td>{record.approved_by}</td>
      <td className="cashbook-approval-date">{new Date(record.approved_at).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</td>
      {currentIds && <td><span className="status-pill">{currentIds.has(record.id) ? 'Actual' : 'Superseded'}</span></td>}
      <td className="cashbook-result-actions-column"><span className="row-action-tooltip" data-tooltip="Show calculation breakdown"><button type="button" className="icon-button" aria-haspopup="dialog" aria-label="Show calculation breakdown" onClick={() => setBreakdown(record)}><Calculator size={17} aria-hidden="true" /></button></span></td>
    </tr>)}</tbody></table></div>
    {records.length > 0 && !filtered.length && <EmptyState title="No matching approvals" note="Try another search or clear the approval filters." />}
    {!printMode && records.length > 0 && <Pager page={currentPage} size={size} total={filtered.length} busy={false} setPage={setPage} setSize={value => { setSize(value); setPage(1) }} sizes={[5, 10, 20, 50]} rowsLabel="Approval history rows per page" />}
    {breakdown && <ModalFrame title={`Calculation breakdown · ${breakdown.project_name}`} onClose={() => setBreakdown(null)}><div className="cashbook-help"><p>As of {localDate(breakdown.as_of)} · Approved by {breakdown.approved_by}</p><p>Approved projection: <strong>{amount(breakdown.amount)}</strong></p><CalculationDetails calculation={breakdown.snapshot} /></div></ModalFrame>}
  </>
}

function CalculationDetails({ calculation }: { calculation: CashbookData['projects'][number]['calculated'] }) {
  const fields = <dl>{([
    ['Contract value', calculation.contract_value], ['Purchase-order costs', calculation.materials],
    ['Wage work', calculation.wages], ['Certified contractor claims', calculation.contractors],
  ] as const).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{amount(value)}</dd></div>)}</dl>
  return <section className="cashbook-calculation" aria-label="Calculation breakdown"><strong className="cashbook-calculation-title">Calculation breakdown</strong>{fields}</section>
}

function ApprovalForm({ csrf, project, asOf, onSaved, onCancel }: { csrf: string; project: CashbookData['projects'][number]; asOf: string; onSaved: () => Promise<void>; onCancel: () => void }) {
  const [input, setInput] = useState<ApprovalInput>({ request_id: crypto.randomUUID(), project_id: project.id, as_of: asOf, fingerprint: project.calculated.fingerprint, note: '' })
  const save = useMutation({ mutationFn: () => api.approveProjectResult(input, csrf), onSuccess: onSaved })
  return <form className="form-grid cashbook-approval-form" onSubmit={event => { event.preventDefault(); save.mutate() }}>
    <div className="cashbook-help full"><strong>{project.name} · As of {localDate(asOf)}</strong><p>Total project amount: <strong>{amount(project.calculated.contract_value)}</strong></p><p>Overview projected profit / loss: <strong>{amount(project.calculated.amount)}</strong></p><p>Previously approved: {project.approval ? amount(project.approval.amount) : 'Not approved'}</p><CalculationDetails calculation={project.calculated} /></div>
    <label className="field full">Approval note *<textarea required minLength={5} maxLength={500} value={input.note} onChange={event => setInput({ ...input, note: event.target.value })} placeholder="Explain what you checked before approving" /></label>
    <MutationError error={save.error} /><FormActions busy={save.isPending} disabled={input.note.trim().length < 5} onCancel={onCancel} submit="Approve" />
  </form>
}
