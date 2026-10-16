import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowDownLeft, ChevronLeft, ChevronRight, CircleDollarSign, Download, FileText, Plus, Search, WalletCards } from 'lucide-react'
import { api, type Project } from '../../lib/api'
import { currency, dateLabel, todayISO } from '../../lib/format'
import { EmptyState, FormActions, Kpi, MutationError, PageTitle, PanelHeading, QueryError } from '../../components/ui'
import { ExportHeader } from '../../components/ExportHeader'

export function CashFlow({ project, projectId, canWrite = true, canRecordReceipt = canWrite, canCreateApplication = canWrite, canExport = true, onRecordReceipt, onNewApplication }: { project?: Project; projectId: string; canWrite?: boolean; canRecordReceipt?: boolean; canCreateApplication?: boolean; canExport?: boolean; onRecordReceipt: () => void; onNewApplication?: () => void }) {
  const [appSearch, setAppSearch] = useState('')
  const [receiptSearch, setReceiptSearch] = useState('')
  const [appPage, setAppPage] = useState<number>(1)
  const [appPageSize, setAppPageSize] = useState<number>(10)
  const [receiptPage, setReceiptPage] = useState<number>(1)
  const [receiptPageSize, setReceiptPageSize] = useState<number>(10)

  const cashFlow = useQuery({ queryKey: ['project', projectId, 'cash-flow'], queryFn: () => api.cashFlow(projectId) })
  const data = cashFlow.data

  const filteredApplications = [...(data?.applications || [])].sort((a, b) => new Date(b.submitted_date).getTime() - new Date(a.submitted_date).getTime()).filter(app => {
    const query = appSearch.trim().toLowerCase()
    return !query || `${app.application_number} ${app.description} ${app.status}`.toLowerCase().includes(query)
  })

  const appTotal = filteredApplications.length
  const appTotalPages = Math.max(1, Math.ceil(appTotal / appPageSize))
  const currentAppPage = Math.min(appPage, appTotalPages)
  const paginatedApplications = filteredApplications.slice((currentAppPage - 1) * appPageSize, currentAppPage * appPageSize)

  const filteredReceipts = [...(data?.receipts || [])].sort((a, b) => new Date(b.received_date).getTime() - new Date(a.received_date).getTime()).filter(r => {
    const query = receiptSearch.trim().toLowerCase()
    return !query || `${r.application_number || ''} ${r.application_description || ''} ${r.payment_method} ${r.reference || ''} ${r.comment || ''} ${r.recorded_by}`.toLowerCase().includes(query)
  })

  const receiptTotal = filteredReceipts.length
  const receiptTotalPages = Math.max(1, Math.ceil(receiptTotal / receiptPageSize))
  const currentReceiptPage = Math.min(receiptPage, receiptTotalPages)
  const paginatedReceipts = filteredReceipts.slice((currentReceiptPage - 1) * receiptPageSize, currentReceiptPage * receiptPageSize)

  const exportReport = async () => {
    await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
    await document.fonts.ready
    const originalTitle = document.title
    document.title = `${project?.name || 'Project'} - Cash Flow Statement`
    window.addEventListener('afterprint', () => { document.title = originalTitle }, { once: true })
    await api.recordActivity(projectId, 'cashflow', 'export')
    window.print()
  }
  return <div className="cash-flow-sections"><PageTitle eyebrow="CLIENT REVENUE" title="Cash flow" subtitle="Client billings and receipts for this project" action={<div className="overview-actions">{canExport && <button className="button-secondary export-report-action" onClick={exportReport} disabled={cashFlow.isFetching || cashFlow.isError}><Download size={14} />Export report</button>}{canCreateApplication && onNewApplication && <button className="button-primary cash-flow-application-action" onClick={onNewApplication}><Plus size={16} />New application</button>}{canRecordReceipt && <button className="button-primary cash-flow-receipt-action" onClick={onRecordReceipt}><Plus size={16} />Record receipt</button>}</div>} />
    <ExportHeader reportTitle="Client Cash Flow &amp; Receipt Statement" projectName={project?.name} projectLocation={project?.location} />
    <div className="kpi-grid four"><Kpi label="Contract value" value={currency(data?.approved_contract_value, data?.currency)} note="Approved project amount" icon={<FileText size={17} />} loading={cashFlow.isLoading} /><Kpi label="Billed to client" value={currency(data?.billed_work, data?.currency)} note="Submitted billing applications" icon={<ArrowDownLeft size={17} />} loading={cashFlow.isLoading} /><Kpi label="Cash received" value={currency(data?.cash_received, data?.currency)} note="Recorded client receipts" icon={<CircleDollarSign size={17} />} loading={cashFlow.isLoading} /><Kpi label="Billed outstanding" value={currency(data?.outstanding_invoices, data?.currency)} note="Billed less allocated receipts" icon={<WalletCards size={17} />} loading={cashFlow.isLoading} /></div>
    <QueryError error={cashFlow.error} onRetry={() => void cashFlow.refetch()} />
    <section className="panel table-panel">
      <PanelHeading
        title="Billing applications"
        meta="Application amounts and allocated client receipts"
        action={
          <div className="register-tools">
            <div className="search-wrap">
              <Search size={15} />
              <input
                placeholder="Search applications..."
                value={appSearch}
                onChange={event => {
                  setAppSearch(event.target.value)
                  setAppPage(1)
                }}
              />
            </div>
              {canCreateApplication && onNewApplication && (
              <button className="button-secondary" onClick={onNewApplication}>
                <Plus size={14} />New application
              </button>
            )}
          </div>
        }
      />
      <div className="table-scroll"><table className="data-table"><thead><tr><th>Application</th><th>Description</th><th>Submitted</th><th className="numeric">Billed</th><th className="numeric">Received</th><th className="numeric">Outstanding</th></tr></thead><tbody>{cashFlow.isLoading ? <tr><td colSpan={6}><div className="loading-line" /></td></tr> : paginatedApplications.length ? paginatedApplications.map(application => <tr key={application.id}><td className="strong-cell">{application.application_number}</td><td>{application.description}</td><td>{dateLabel(application.submitted_date)}</td><td className="numeric">{currency(application.billed_amount, data?.currency)}</td><td className="numeric">{currency(application.received_amount, data?.currency)}</td><td className="numeric">{currency(application.outstanding_amount, data?.currency)}</td></tr>) : <tr><td colSpan={6}><EmptyState title={appSearch ? "No matching billing applications" : "No billing applications"} note={appSearch ? "Try adjusting your search query." : "Submit a billing application before allocating a receipt to it."} /></td></tr>}</tbody></table></div>
      <div className="register-pagination">
        <label>
          Rows per page
          <select
            aria-label="Applications per page"
            value={appPageSize}
            onChange={event => {
              setAppPageSize(Number(event.target.value))
              setAppPage(1)
            }}
          >
            {[10, 20, 50, 100].map(size => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </label>
        <span>
          {appTotal ? `${(currentAppPage - 1) * appPageSize + 1}–${Math.min(currentAppPage * appPageSize, appTotal)} of ${appTotal}` : '0 of 0'}
        </span>
        <div className="register-page-controls">
          <button
            className="icon-button"
            title="Previous page"
            aria-label="Previous page"
            disabled={currentAppPage <= 1}
            onClick={() => setAppPage(prev => Math.max(1, prev - 1))}
          >
            <ChevronLeft size={16} />
          </button>
          <span>
            Page {currentAppPage} of {appTotalPages}
          </span>
          <button
            className="icon-button"
            title="Next page"
            aria-label="Next page"
            disabled={currentAppPage >= appTotalPages}
            onClick={() => setAppPage(prev => Math.min(appTotalPages, prev + 1))}
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </section>
    <section className="panel table-panel">
      <PanelHeading
        title="Client receipt ledger"
        meta="All recorded client payments · newest first"
        action={
          <div className="search-wrap">
            <Search size={15} />
            <input
              placeholder="Search receipts, method, reference..."
              value={receiptSearch}
              onChange={event => {
                setReceiptSearch(event.target.value)
                setReceiptPage(1)
              }}
            />
          </div>
        }
      />
      <div className="table-scroll"><table className="data-table"><thead><tr><th>Application</th><th>Description</th><th>Received</th><th className="numeric">Amount</th><th>Method</th><th>Reference</th><th>Recorded by</th></tr></thead><tbody>{cashFlow.isLoading ? <tr><td colSpan={7}><div className="loading-line" /></td></tr> : paginatedReceipts.length ? paginatedReceipts.map(receipt => <tr key={receipt.id}><td className="strong-cell">{receipt.application_number || 'Unallocated'}</td><td>{receipt.application_description || '—'}</td><td>{dateLabel(receipt.received_date)}</td><td className="numeric strong-cell">{currency(receipt.amount, data?.currency)}</td><td>{receipt.payment_method}</td><td>{receipt.reference || receipt.comment || '—'}</td><td>{receipt.recorded_by}</td></tr>) : <tr><td colSpan={7}><EmptyState title={receiptSearch ? "No matching client receipts" : "No client receipts recorded"} note={receiptSearch ? "Try adjusting your search query." : "Record each client payment to build the project cash-flow history."} /></td></tr>}</tbody></table></div>
      <div className="register-pagination">
        <label>
          Rows per page
          <select
            aria-label="Receipts per page"
            value={receiptPageSize}
            onChange={event => {
              setReceiptPageSize(Number(event.target.value))
              setReceiptPage(1)
            }}
          >
            {[10, 20, 50, 100].map(size => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </label>
        <span>
          {receiptTotal ? `${(currentReceiptPage - 1) * receiptPageSize + 1}–${Math.min(currentReceiptPage * receiptPageSize, receiptTotal)} of ${receiptTotal}` : '0 of 0'}
        </span>
        <div className="register-page-controls">
          <button
            className="icon-button"
            title="Previous page"
            aria-label="Previous page"
            disabled={currentReceiptPage <= 1}
            onClick={() => setReceiptPage(prev => Math.max(1, prev - 1))}
          >
            <ChevronLeft size={16} />
          </button>
          <span>
            Page {currentReceiptPage} of {receiptTotalPages}
          </span>
          <button
            className="icon-button"
            title="Next page"
            aria-label="Next page"
            disabled={currentReceiptPage >= receiptTotalPages}
            onClick={() => setReceiptPage(prev => Math.min(receiptTotalPages, prev + 1))}
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </section>
  </div>
}

export function CashReceiptForm({ projectId, csrf, onCancel, onSaved }: { projectId: string; csrf: string; onCancel: () => void; onSaved: () => void }) {
  const cashFlow = useQuery({ queryKey: ['project', projectId, 'cash-flow'], queryFn: () => api.cashFlow(projectId) })
  const applications = cashFlow.data?.applications || []
  const [form, setForm] = useState({ billing_entry_id: '', received_date: todayISO, amount: '', payment_method: 'Bank transfer' as 'Bank transfer' | 'Cheque' | 'Cash' | 'Gpay' | 'Other', reference: '', comment: '' })
  const mutation = useMutation({ mutationFn: () => api.recordCashReceipt(projectId, { ...form, billing_entry_id: form.billing_entry_id || undefined }, csrf), onSuccess: onSaved })
  return <form className="form-grid" onSubmit={event => { event.preventDefault(); mutation.mutate() }}>
    <label className="field full">Billing application (optional)<select value={form.billing_entry_id} onChange={event => setForm({ ...form, billing_entry_id: event.target.value })}><option value="">Unallocated client receipt</option>{applications.filter(application => Number(application.outstanding_amount) > 0).map(application => <option key={application.id} value={application.id}>{application.application_number} · {application.description} · remaining {currency(application.outstanding_amount)}</option>)}</select></label>
    <label className="field">Received date<input required type="date" value={form.received_date} onChange={event => setForm({ ...form, received_date: event.target.value })} /></label>
    <label className="field">Amount received<input required type="number" min="0.01" step="0.01" value={form.amount} onChange={event => setForm({ ...form, amount: event.target.value })} /></label>
    <label className="field">Payment method<select value={form.payment_method} onChange={event => setForm({ ...form, payment_method: event.target.value as typeof form.payment_method })}><option>Bank transfer</option><option>Cheque</option><option>Cash</option><option>Gpay</option><option>Other</option></select></label>
    <label className="field">Reference<input maxLength={100} value={form.reference} onChange={event => setForm({ ...form, reference: event.target.value })} placeholder="Transaction or cheque number" /></label>
    <label className="field full">Comment<textarea maxLength={500} value={form.comment} onChange={event => setForm({ ...form, comment: event.target.value })} /></label>
    {cashFlow.error && <QueryError error={cashFlow.error} onRetry={() => void cashFlow.refetch()} />}
    <MutationError error={mutation.error} />
    <FormActions onCancel={onCancel} busy={mutation.isPending || cashFlow.isLoading} submit="Save receipt" />
  </form>
}

